# import logging
import concurrent.futures
import os
import sys
import numpy as np

#check os
try:
    from .ximea import xiapi
except ImportError:
    # sys.path.insert(0, r"C:\Users\topo-tomo\workspace\rbtm-drivers-next\vendor\ximea_win\API\Python\v3") #TODO: replace to ximea drivers path
    sys.path.insert(0, r"c:\XIMEA\API\Python\v3") #TODO: replace to ximea drivers path
    from ximea import xiapi

import atexit

# from autologging import traced, TRACE

# logging.basicConfig(
#     level=TRACE, stream=sys.stdout,
#     format="%(levelname)s:%(filename)s,%(lineno)d:%(name)s.%(funcName)s:%(message)s")


from autologging import traced
from .. import tomo_logger

# @traced(tomo_logger.logger)
PIXEL_SIZES = {
    'MH110XC-KK-FA': 9.0e-3,  # pixel size in mm
    'MJ150XR-GP-FA-GO': 4.25e-3,  # pixel size in mm
}
DEFAULT_PIXEL_SIZE = 4.25e-3  # pixel size in mm


class HWDetector(object):
    """Драйвер камеры XIMEA xiRAY.

    Режим захвата **один**: постоянный захват (``xiStartAcquisition`` один
    раз) с программным триггером на каждый кадр. Прежний «legacy»-режим
    (start/stop на каждый кадр) удалён: именно он воспроизводил гонку
    ``xiStopAcquisition`` / ``mm_WorkerThread`` внутри libm3api и ронял
    процесс по segfault (см. README.md).

    Захват запускается лениво при первом :meth:`get_frame` либо явно через
    :meth:`start_acquisition` и останавливается только в :meth:`close`
    (или явным :meth:`stop_acquisition` в конце эксперимента). При любой
    ошибке посреди серии состояние сбрасывается через
    :meth:`_reset_trigger`, и следующий вызов поднимает захват заново.
    """

    def __init__(self):
        # create instance for first connected camera
        try:
            self.cam = xiapi.Camera()
            self.cam.set_debug_level("XI_DL_WARNING")
            self.cam.open_device()
        except xiapi.Xi_error as err:
            tomo_logger.logger.error("Detector.init() failed " + str(err))
            raise RuntimeError("Detector.init() failed " + str(err))

        atexit.register(self.close)

        self.target_temperature = 15.0
        try:
            self.cam.disable_aeag()
            # self.cam.disable_auto_wb()
            self.cam.set_gain(0.0)
            self.cam.set_cooling("XI_TEMP_CTRL_MODE_AUTO")
            self.cam.set_target_temp(self.target_temperature)
            self.cam.set_imgdataformat("XI_MONO16")
            # TODO: add waiting for cooling

        except xiapi.Xi_error as err:
            tomo_logger.logger.error("Detector.init() failed " + str(err))
            raise RuntimeError("Detector.init() failed " + str(err))

        # --- Persistent acquisition state ---
        # Pre-allocate Image once to avoid per-frame memory allocation
        self._img = xiapi.Image()
        self._acquisition_active = False
        self._current_exposure_us = None
        # Один долгоживущий поток захвата на весь процесс: xiGetImage всегда
        # вызывается из одного и того же OS-потока.
        self._capture_executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=1, thread_name_prefix='ximea-capture')

    # ------------------------------------------------------------------
    # Persistent acquisition API
    # ------------------------------------------------------------------

    def start_acquisition(self, exposure, use_trigger=True):
        """Запустить постоянный захват с программным триггером.

        Идемпотентен: если захват уже идёт, метод только применяет новую
        экспозицию (без stop/start). Вызывается автоматически из
        :meth:`get_frame`; отдельно нужен Flask-слою в начале эксперимента.

        :param exposure: экспозиция в секундах.
        :param use_trigger: устарел и игнорируется; режим всегда
            ``XI_TRG_SOFTWARE`` (оставлен для совместимости сигнатуры).
        :raises RuntimeError: если камера отвергла конфигурацию. Камера при
            этом возвращается в известное состояние (триггер выключен,
            захват остановлен).
        """
        if not use_trigger:
            tomo_logger.logger.warning(
                "Detector.start_acquisition(use_trigger=False): режим свободного "
                "счёта удалён, используется программный триггер"
            )

        exposure_us = int(round(exposure * 1e6))

        if self._acquisition_active:
            # Идемпотентность: повторный вызов только меняет экспозицию.
            try:
                self._apply_exposure(exposure_us)
            except Exception as err:
                tomo_logger.logger.error(
                    "Detector.start_acquisition() failed %s", str(err))
                self._reset_trigger()
                raise RuntimeError("Detector.start_acquisition() failed " + str(err))
            return

        try:
            self.cam.set_exposure(exposure_us)
            self._current_exposure_us = exposure_us

            # Each frame starts only on explicit set_trigger_software(1)
            self.cam.set_trigger_source("XI_TRG_SOFTWARE")
            self.cam.set_trigger_selector("XI_TRG_SEL_FRAME_START")
            # Accept next trigger while sensor reads out previous frame.
            # Not all models support this — skip silently if not implemented.
            try:
                self.cam.set_trigger_overlap("XI_TRG_OVERLAP_READ_OUT")
            except xiapi.Xi_error as _ov_err:
                tomo_logger.logger.warning(
                    "Detector: trigger_overlap not supported by this model "
                    "(%s) — continuing without overlap", str(_ov_err)
                )

            self.cam.start_acquisition()
            self._acquisition_active = True

            tomo_logger.logger.info(
                "Detector: постоянный захват запущен (exposure=%.3f s, "
                "trigger=SOFTWARE)", exposure
            )

        except Exception as err:
            tomo_logger.logger.error(
                "Detector.start_acquisition() failed %s", str(err))
            self._reset_trigger()
            raise RuntimeError("Detector.start_acquisition() failed " + str(err))

    def stop_acquisition(self):
        """Остановить постоянный захват. Идемпотентен."""
        if not self._acquisition_active:
            return
        self._reset_trigger()
        tomo_logger.logger.info("Detector: постоянный захват остановлен")

    def _reset_trigger(self):
        """Вернуть камеру в известное состояние: захват остановлен, триггер OFF.

        Вызывается из всех путей ошибки вместо разрозненных
        ``except Exception: pass``. Собственные ошибки не пробрасывает —
        её задача только в том, чтобы следующий :meth:`start_acquisition`
        начинал с чистого состояния.
        """
        self._acquisition_active = False
        self._current_exposure_us = None
        for what, action in (
            ('stop_acquisition', self.cam.stop_acquisition),
            ('set_trigger_source(XI_TRG_OFF)',
             lambda: self.cam.set_trigger_source("XI_TRG_OFF")),
        ):
            try:
                action()
            except Exception as err:
                tomo_logger.logger.warning(
                    "Detector._reset_trigger: %s failed: %s", what, str(err))

    def _apply_exposure(self, exposure_us):
        """Сменить экспозицию на лету (без stop/start захвата)."""
        if exposure_us == self._current_exposure_us:
            return
        self.cam.set_exposure_direct(exposure_us)
        self._current_exposure_us = exposure_us

    # ------------------------------------------------------------------
    # Device lifecycle
    # ------------------------------------------------------------------

    def close(self):
        # Guard against double-close: atexit may call this after an explicit
        # close() from a pytest fixture or user code. cam.CAM_OPEN is the
        # authoritative flag set by xiapi.Camera.
        if not self.cam.CAM_OPEN:
            return
        try:
            if self._acquisition_active:
                self.cam.stop_acquisition()
                self._acquisition_active = False
            self.cam.close_device()
        except xiapi.Xi_error as err:
            tomo_logger.logger.error("Detector.close() failed " + str(err))
            raise RuntimeError("Detector.close() failed " + str(err))

    # ------------------------------------------------------------------
    # Camera parameters
    # ------------------------------------------------------------------

    def get_model(self):
        try:
            name = self.cam.get_device_name()
            if isinstance(name, bytes):
                return name.decode('utf-8', errors='replace').rstrip('\x00')
            return str(name)
        except Exception:
            return 'Ximea xiRAY'

    def get_pixel_size(self):
        """Return physical pixel size in mm based on detector model."""
        return PIXEL_SIZES.get(self.get_model(), DEFAULT_PIXEL_SIZE)

    def set_gain(self, gain):
        self.cam.set_gain(gain)

    def get_gain(self):
        return self.cam.get_gain()

    def get_sensor_temp(self):
        return self.cam.get_temp()

    def get_hous_temp(self):
        return self.cam.get_hous_temp()

    def get_exposure(self):
        return self.cam.get_exposure() / 1e6

    # ------------------------------------------------------------------
    # Frame capture
    # ------------------------------------------------------------------

    # Дополнительный запас времени (сек) поверх экспозиции для hard timeout watchdog.
    # Покрывает время передачи данных, задержки шины, jitter.
    _HARD_TIMEOUT_MARGIN_S = 15.0

    def _capture_one_frame(self, timeout_ms):
        """Захватить один кадр.
        Вызывается из get_frame() в выделенном потоке захвата через
        concurrent.futures, чтобы применить внешний (hard) таймаут
        независимо от XIMEA SDK.
        """
        self.cam.set_trigger_software(1)
        self.cam.get_image(self._img, timeout=timeout_ms)
        return np.asarray(self._img.get_image_data_numpy(), dtype=np.uint16)

    def _capture_with_hard_timeout(self, timeout_ms, hard_timeout_s):
        """Захватить кадр с жёстким таймаутом поверх SDK-таймаута.

        При зависании SDK (обрыв шины: xiGetImage не возвращается даже
        с собственным таймаутом) процесс завершается через ``os._exit(1)``,
        и Docker (``restart: unless-stopped``) перезапускает контейнер.

        Почему ``os._exit``, а не ``sys.exit``: SystemExit запускал
        ``atexit``-обработчики, т.е. ``close()`` → ``xiStopAcquisition`` /
        ``xiCloseDevice`` из главного потока, пока поток захвата всё ещё
        сидит внутри ``xiGetImage``.
        """
        future = self._capture_executor.submit(self._capture_one_frame, timeout_ms)
        try:
            return future.result(timeout=hard_timeout_s)
        except concurrent.futures.TimeoutError:
            tomo_logger.logger.critical(
                "Detector: get_image HARD TIMEOUT (%.1fs) — "
                "зависание шины. Завершаем tomograph_server "
                "для автоматического перезапуска Docker.",
                hard_timeout_s,
            )
            for handler in tomo_logger.logger.handlers:
                try:
                    handler.flush()
                except Exception:
                    pass
            sys.stdout.flush()
            sys.stderr.flush()
            os._exit(1)

    def get_frame(self, exposure):
        """Захватить один кадр и вернуть его как ``numpy.ndarray`` uint16.

        :param exposure: экспозиция в секундах.

        Если постоянный захват ещё не запущен — запускается лениво
        (см. :meth:`start_acquisition`). Далее каждый кадр — это
        ``set_trigger_software(1)`` + ``xiGetImage`` без stop/start.
        Смена экспозиции применяется на лету через ``set_exposure_direct``.

        ``xiGetImage`` выполняется в выделенном долгоживущем потоке с
        жёстким (hard) таймаутом поверх SDK-таймаута: при обрыве шины SDK
        уходит в бесконечный цикл сброса эндпоинтов и не возвращается даже
        при выставленном ``timeout``.

        При любой ошибке состояние захвата сбрасывается
        (:meth:`_reset_trigger`), и следующий вызов поднимет захват заново.

        :raises RuntimeError: при любой ошибке захвата.
        """
        exposure_us = int(round(exposure * 1e6))
        # Hard timeout: экспозиция × 2 + запас на transfer jitter
        hard_timeout_s = exposure * 2 + self._HARD_TIMEOUT_MARGIN_S
        # get_image() принимает timeout в МИЛЛИСЕКУНДАХ (см. xiapi.py).
        timeout_ms = int(exposure_us * 1.5 / 1000 + 500)

        if not self._acquisition_active:
            self.start_acquisition(exposure)

        try:
            self._apply_exposure(exposure_us)
            data = self._capture_with_hard_timeout(timeout_ms, hard_timeout_s)
        except Exception as err:
            # Ловим ЛЮБОЙ тип исключения (не только Xi_error): иначе
            # MemoryError/RuntimeError оставляли _acquisition_active=True
            # при фактически сломанном захвате.
            tomo_logger.logger.error(
                "Detector.get_frame() failed %s — сбрасываем захват, "
                "следующий вызов запустит его заново", str(err))
            self._reset_trigger()
            raise RuntimeError("Detector.get_frame() failed " + str(err))

        if data is None:
            self._reset_trigger()
            raise RuntimeError("Detector.get_frame() failed: no frame captured")
        return data

    def get_frames(self, exposure):
        """Совместимость со старым API: синоним :meth:`get_frame`.

        Параметр ``number_frames`` удалён — в проде всегда был 1,
        накопление кадров делается на стороне эксперимента.
        """
        return self.get_frame(exposure)

    # ------------------------------------------------------------------
    # State
    # ------------------------------------------------------------------

    def get_state(self, options=None):
        if options is None:
            options = ['exposure', 'sensor_temp', 'hous_temp']
        res = {}
        if not isinstance(options, (list, tuple)):
            options = [options, ]

        for option in options:
            if option == 'exposure':
                s = self.get_exposure()
            elif option == 'sensor_temp':
                s = self.get_sensor_temp()
            elif option == 'hous_temp':
                s = self.get_hous_temp()
            elif option == 'model':
                s = self.get_model()
            else:
                s = {'error': 'Unsupported option'}
            res[option] = s
        return res
