import atexit
import concurrent.futures

import numpy as np

try:
    # Вендорённые биндинги: drivers/Detector/ximea -> vendor/ximea/api/Python/v3/ximea
    from .ximea import xiapi
except ImportError:
    # Пакет ximea установлен в систему (XIMEA Software Package).
    from ximea import xiapi

from .. import tomo_logger

DEFAULT_MODEL = 'Ximea xiRAY'  # если имя устройства не читается
PIXEL_SIZES = {
    'MH110XC-KK-FA': 9.0e-3,  # pixel size in mm
    'MJ150XR-GP-FA-GO': 4.25e-3,  # pixel size in mm
}
DEFAULT_PIXEL_SIZE = 4.25e-3  # pixel size in mm

# ----------------------------------------------------------------------
# Таймауты. Одна формула на весь драйвер:
#     sdk_timeout_ms  = exposure_ms * SDK_TIMEOUT_FACTOR + SDK_TIMEOUT_MARGIN_MS
#     hard_timeout_s  = sdk_timeout_s + HARD_TIMEOUT_MARGIN_S
# SDK-таймаут отдаётся в xiGetImage, hard-таймаут — внешнему watchdog'у
# (xiGetImage при обрыве шины не возвращается даже со своим таймаутом).
# RPC-слой должен брать свой таймаут из expected_frame_timeout_s().
# ----------------------------------------------------------------------
SDK_TIMEOUT_FACTOR = 1.5        # запас на чтение матрицы и передачу кадра
SDK_TIMEOUT_MARGIN_MS = 500.0   # фиксированный запас SDK-таймаута, мс
HARD_TIMEOUT_MARGIN_S = 15.0    # запас watchdog'а поверх SDK-таймаута, с


def sdk_timeout_ms(exposure_s):
    """Таймаут для ``xiGetImage`` в миллисекундах."""
    return int(round(exposure_s * 1e3 * SDK_TIMEOUT_FACTOR + SDK_TIMEOUT_MARGIN_MS))


def expected_frame_timeout_s(exposure_s):
    """Сколько максимум может длиться один кадр, секунды.

    Значение, после которого кадр считается зависшим. RPC-слой обязан
    ставить свой таймаут больше этого, иначе прокси отвалится раньше,
    чем драйвер успеет сообщить о зависании.
    """
    return sdk_timeout_ms(exposure_s) / 1e3 + HARD_TIMEOUT_MARGIN_S


class DetectorHangError(RuntimeError):
    """``xiGetImage`` не вернулся за отведённое время (зависание SDK/шины).

    Камера после этого непригодна: поток захвата навсегда остался внутри
    вызова SDK. Драйвер НЕ завершает процесс сам — решение принимает
    владелец процесса (``tomograph_server``) через колбэк ``on_hang``.
    """


# Колбэк по умолчанию для всех детекторов процесса: вызывается при
# зависании захвата до выброса DetectorHangError. Устанавливается
# владельцем процесса через set_on_hang() (см. tomograph_server.py).
_on_hang_hook = None


def set_on_hang(callback):
    """Задать процессный колбэк на зависание захвата.

    :param callback: ``callable(exc: DetectorHangError)`` или ``None``.
        Типичная реализация в ``tomograph_server``: сбросить логи и
        завершить процесс (``os._exit(1)``), чтобы Docker перезапустил
        контейнер.
    """
    global _on_hang_hook
    _on_hang_hook = callback


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

    def __init__(self, on_hang=None):
        """
        :param on_hang: колбэк ``callable(exc)``, вызываемый при зависании
            захвата. Если не задан — используется процессный колбэк из
            :func:`set_on_hang`. Сам драйвер процесс не завершает.
        """
        self._on_hang = on_hang
        self._closed = False
        # create instance for first connected camera
        try:
            self.cam = xiapi.Camera()
            self.cam.set_debug_level("XI_DL_WARNING")
            self.cam.open_device()
        except Exception as err:
            tomo_logger.logger.error("Detector.init() failed " + str(err))
            raise RuntimeError("Detector.init() failed " + str(err))

        self.target_temperature = 15.0
        try:
            self.cam.disable_aeag()
            self.cam.set_gain(0.0)
            self.cam.set_cooling("XI_TEMP_CTRL_MODE_AUTO")
            self.cam.set_target_temp(self.target_temperature)
            self.cam.set_imgdataformat("XI_MONO16")
            # TODO: add waiting for cooling
        except Exception as err:
            # Устройство уже открыто: без close_device() камера осталась бы
            # занятой, и ленивая переинициализация детектора в HWTomograph
            # получала бы «устройство занято» на каждой попытке.
            tomo_logger.logger.error("Detector.init() failed " + str(err))
            try:
                self.cam.close_device()
            except Exception as close_err:
                tomo_logger.logger.error(
                    "Detector.init(): close_device() after failed configuration "
                    "also failed: %s", str(close_err))
            raise RuntimeError("Detector.init() failed " + str(err))

        # Имя модели читается один раз: от него зависит размер пикселя,
        # а молчаливый откат на модель по умолчанию давал 4.25 мкм вместо
        # 9 мкм для MH110XC (ошибка в метаданных всех кадров).
        self.model = self._read_device_name()
        self._pixel_size_warned = False

        # --- Persistent acquisition state ---
        # Pre-allocate Image once to avoid per-frame memory allocation
        self._img = xiapi.Image()
        self._acquisition_active = False
        self._current_exposure_us = None
        # True после hard timeout: поток захвата навсегда внутри xiGetImage,
        # трогать камеру больше нельзя (иначе та самая гонка в libm3api).
        self._hung = False
        # Один долгоживущий поток захвата на весь процесс: xiGetImage всегда
        # вызывается из одного и того же OS-потока.
        self._capture_executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=1, thread_name_prefix='ximea-capture')

        atexit.register(self.close)

    def _read_device_name(self):
        """Прочитать имя модели камеры; при ошибке — ERROR в лог и значение
        по умолчанию."""
        try:
            name = self.cam.get_device_name()
        except Exception as err:
            tomo_logger.logger.error(
                "Detector: не удалось прочитать имя устройства (%s) — "
                "используется '%s', размер пикселя будет по умолчанию",
                str(err), DEFAULT_MODEL)
            return DEFAULT_MODEL
        if isinstance(name, bytes):
            name = name.decode('utf-8', errors='replace')
        return str(name).rstrip('\x00')

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
        if self._closed:
            raise RuntimeError("Detector.start_acquisition(): детектор закрыт")
        if self._hung:
            raise DetectorHangError(
                "Detector: захват завис ранее, требуется перезапуск процесса")

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
        """Остановить захват, закрыть устройство, погасить поток захвата.

        Идемпотентен: atexit вызывает close() после явного close() из
        фикстуры pytest или из ``HWTomograph._release_devices()``.
        """
        if self._closed:
            return
        self._closed = True
        try:
            atexit.unregister(self.close)
        except Exception:
            pass

        try:
            if self._hung:
                # Поток захвата сидит внутри xiGetImage: stop/close из
                # главного потока — это гонка, которая роняет процесс.
                tomo_logger.logger.critical(
                    "Detector.close(): захват завис, камера не закрывается — "
                    "требуется перезапуск процесса")
                return
            self.stop_acquisition()
            if self.cam.CAM_OPEN:
                self.cam.close_device()
        except Exception as err:
            tomo_logger.logger.error("Detector.close() failed " + str(err))
            raise RuntimeError("Detector.close() failed " + str(err))
        finally:
            # wait=False: если поток захвата завис в SDK, ждать его нельзя.
            self._capture_executor.shutdown(wait=False)

    # ------------------------------------------------------------------
    # Camera parameters
    # ------------------------------------------------------------------

    def get_model(self):
        """Имя модели, прочитанное один раз при инициализации."""
        return self.model

    def get_pixel_size(self):
        """Физический размер пикселя в мм по модели детектора."""
        pixel_size = PIXEL_SIZES.get(self.model)
        if pixel_size is None:
            if not self._pixel_size_warned:
                self._pixel_size_warned = True
                tomo_logger.logger.warning(
                    "Detector: размер пикселя для модели '%s' неизвестен — "
                    "используется значение по умолчанию %.3e мм",
                    self.model, DEFAULT_PIXEL_SIZE)
            return DEFAULT_PIXEL_SIZE
        return pixel_size

    def get_sensor_temp(self):
        return self.cam.get_temp()

    def get_hous_temp(self):
        return self.cam.get_hous_temp()

    def get_exposure(self):
        return self.cam.get_exposure() / 1e6

    # ------------------------------------------------------------------
    # Frame capture
    # ------------------------------------------------------------------

    @staticmethod
    def expected_frame_timeout_s(exposure):
        """Верхняя граница длительности одного кадра, секунды.

        Обёртка над модульной :func:`expected_frame_timeout_s`, чтобы
        RPC-слой мог получить значение прямо у объекта детектора.
        """
        return expected_frame_timeout_s(exposure)

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

        Захват идёт в единственном долгоживущем потоке — это гарантирует,
        что ``xiGetImage`` всегда вызывается из одного и того же OS-потока.

        При зависании SDK (обрыв шины: xiGetImage не возвращается даже
        с собственным таймаутом) драйвер НЕ завершает процесс: он помечает
        детектор как зависший, дёргает колбэк ``on_hang`` (политика владельца
        процесса — например, ``os._exit(1)`` в ``tomograph_server``, чтобы
        Docker перезапустил контейнер) и бросает :class:`DetectorHangError`.

        Трогать камеру после этого нельзя: ``xiStopAcquisition`` /
        ``xiCloseDevice`` из главного потока, пока поток захвата сидит
        внутри ``xiGetImage``, — это ровно та гонка в libm3api, из-за
        которой процесс падал по segfault.
        """
        future = self._capture_executor.submit(self._capture_one_frame, timeout_ms)
        try:
            return future.result(timeout=hard_timeout_s)
        except concurrent.futures.TimeoutError:
            self._hung = True
            self._acquisition_active = False
            tomo_logger.logger.critical(
                "Detector: get_image HARD TIMEOUT (%.1f s) — зависание SDK/шины. "
                "Камера непригодна до перезапуска процесса.", hard_timeout_s,
            )
            error = DetectorHangError(
                "Detector.get_frame(): xiGetImage hang, hard timeout "
                "{:.1f} s exceeded".format(hard_timeout_s))
            self._notify_hang(error)
            raise error

    def _notify_hang(self, error):
        """Сообщить владельцу процесса о зависании захвата."""
        callback = self._on_hang if self._on_hang is not None else _on_hang_hook
        if callback is None:
            tomo_logger.logger.warning(
                "Detector: колбэк on_hang не задан — решение о перезапуске "
                "процесса принимать некому")
            return
        try:
            callback(error)
        except Exception as err:
            tomo_logger.logger.error(
                "Detector: колбэк on_hang упал: %s", str(err))

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

        :raises DetectorHangError: если ``xiGetImage`` не вернулся за
            :func:`expected_frame_timeout_s`.
        :raises RuntimeError: при любой другой ошибке захвата.
        """
        if self._closed:
            raise RuntimeError("Detector.get_frame(): детектор закрыт")
        if self._hung:
            # Поток захвата навсегда внутри xiGetImage — новые попытки
            # только вешают вызывающего ещё на один hard timeout.
            raise DetectorHangError(
                "Detector: захват завис ранее, требуется перезапуск процесса")

        exposure_us = int(round(exposure * 1e6))
        timeout_ms = sdk_timeout_ms(exposure)
        hard_timeout_s = expected_frame_timeout_s(exposure)

        if not self._acquisition_active:
            self.start_acquisition(exposure)

        try:
            self._apply_exposure(exposure_us)
            data = self._capture_with_hard_timeout(timeout_ms, hard_timeout_s)
        except DetectorHangError:
            raise
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
