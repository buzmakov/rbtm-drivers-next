# import logging
import concurrent.futures
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
        self._trigger_mode = False          # True = XI_TRG_SOFTWARE mode
        self._current_exposure_us = None

    # ------------------------------------------------------------------
    # Persistent acquisition API
    # ------------------------------------------------------------------

    def start_acquisition(self, exposure, use_trigger=True):
        """Start persistent acquisition for a series of frames.

        Call this once before a batch of get_frames() calls for best
        performance. While active, get_frames() skips start/stop overhead.

        :param exposure: exposition in seconds (fixed for the whole batch)
        :param use_trigger: True  — software-trigger mode: each get_frames()
                                    fires XI_TRG_SOFTWARE (~μs overhead).
                            False — free-run mode: frames arrive continuously,
                                    get_frames() just reads them.
        :raises RuntimeError: if camera rejects the configuration.
                              The camera is left in a clean state (trigger OFF,
                              acquisition stopped) so legacy get_frames() will
                              still work.
        """
        if self._acquisition_active:
            tomo_logger.logger.warning(
                "Detector.start_acquisition() called while already active — ignored"
            )
            return

        exposure_us = int(round(exposure * 1e6))

        try:
            self.cam.set_exposure(exposure_us)
            self._current_exposure_us = exposure_us

            if use_trigger:
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
            self._trigger_mode = use_trigger

            tomo_logger.logger.info(
                "Detector: persistent acquisition started "
                "(exposure=%.3f s, trigger=%s)",
                exposure, "SOFTWARE" if use_trigger else "FREE_RUN"
            )

        except xiapi.Xi_error as err:
            tomo_logger.logger.error(
                "Detector.start_acquisition() failed %s — falling back to legacy mode",
                str(err)
            )
            # Clean up: restore free-run so legacy mode is not broken
            try:
                self.cam.set_trigger_source("XI_TRG_OFF")
            except Exception:
                pass
            self._acquisition_active = False
            self._trigger_mode = False
            raise RuntimeError("Detector.start_acquisition() failed " + str(err))

    def stop_acquisition(self):
        """Stop persistent acquisition.

        Safe to call even if acquisition is not active.
        After this, get_frames() falls back to legacy (start/stop per call).
        """
        if not self._acquisition_active:
            return
        try:
            self.cam.stop_acquisition()
        except xiapi.Xi_error as err:
            tomo_logger.logger.error(
                "Detector.stop_acquisition() failed %s", str(err)
            )
        finally:
            self._acquisition_active = False
            self._trigger_mode = False
            # Restore free-run so legacy get_frames() works without trigger
            try:
                self.cam.set_trigger_source("XI_TRG_OFF")
            except Exception:
                pass
            tomo_logger.logger.info("Detector: persistent acquisition stopped")

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
    # Покрывает время передачи данных, USB-задержки, jitter.
    _HARD_TIMEOUT_MARGIN_S = 15.0

    def _capture_one_frame(self, timeout_us):
        """Захватить один кадр.
        Вызывается из get_frames() в отдельном потоке через concurrent.futures,
        чтобы применить внешний (hard) таймаут независимо от XIMEA SDK.
        """
        if self._trigger_mode:
            self.cam.set_trigger_software(1)
        self.cam.get_image(self._img, timeout=timeout_us)
        return self._img.get_image_data_numpy().astype(np.uint32)

    def get_frames(self, exposure, number_frames=1):
        """Capture and return frames as a uint16 numpy array.

        :param exposure: exposition in seconds
        :param number_frames: number of frames to sum (accumulate in uint32)

        Каждый вызов `get_image()` выполняется в отдельном потоке через
        `concurrent.futures.ThreadPoolExecutor` с жёстким (hard) таймаутом.
        Это защищает от зависания XIMEA SDK при USB-обрыве: SDK входит
        в бесконечный цикл сброса эндпоинтов и никогда не выбрасывает исключение,
        даже если SDK-таймаут `timeout_us` установлен.

        Hard timeout = exposure × 2 + _HARD_TIMEOUT_MARGIN_S (15 сек по умолчанию).

        Behaviour depends on acquisition state:

        * **Persistent + trigger mode** (after start_acquisition(use_trigger=True)):
          Fires XI_TRG_SOFTWARE per frame — minimal overhead (~μs).
          If exposure changed, applies set_exposure_direct() without stop/start.

        * **Persistent + free-run mode** (after start_acquisition(use_trigger=False)):
          Reads frames directly — no per-frame start/stop overhead.
          If exposure changed, applies set_exposure_direct() without stop/start.

        * **Legacy mode** (no start_acquisition() call or after stop_acquisition()):
          Classic start_acquisition → get_image × N → stop_acquisition per call.
          Always correct, slower by ~100–250 ms per call.
        """
        exposure_us = int(round(exposure * 1e6))
        # Hard timeout: экспозиция × 2 + запас на USB/transfer jitter
        hard_timeout_s = exposure * 2 + self._HARD_TIMEOUT_MARGIN_S
        data = None

        # get_image() принимает timeout в МИЛЛИСЕКУНДАХ (см. xiapi.py).
        # exposure_us — в микросекундах, поэтому делим на 1000, добавляем 500 мс запаса.
        timeout_ms = int(exposure_us * 1.5 / 1000 + 500)

        try:
            if self._acquisition_active:
                # ── Optimised path ──────────────────────────────────────
                if exposure_us != self._current_exposure_us:
                    self.cam.set_exposure_direct(exposure_us)
                    self._current_exposure_us = exposure_us

                for frame_numb in range(number_frames):
                    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
                        future = ex.submit(self._capture_one_frame, timeout_ms)
                        try:
                            frame_data = future.result(timeout=hard_timeout_s)
                        except concurrent.futures.TimeoutError:
                            tomo_logger.logger.critical(
                                "Detector: get_image HARD TIMEOUT (%.1fs) — "
                                "USB hang detected. Завершаем tomograph_server "
                                "для автоматического перезапуска Docker.",
                                hard_timeout_s,
                            )
                            # sys.exit(1): Docker (restart: unless-stopped) перезапустит
                            # контейнер и переинициализирует XIMEA SDK.
                            sys.exit(1)
                    if frame_numb == 0:
                        data = frame_data
                    else:
                        data += frame_data

            else:
                # ── Legacy path (fallback) ───────────────────────────────
                self.cam.set_exposure(exposure_us)
                self._current_exposure_us = exposure_us

                self.cam.start_acquisition()
                try:
                    for frame_numb in range(number_frames):
                        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
                            future = ex.submit(self._capture_one_frame, timeout_ms)
                            try:
                                frame_data = future.result(timeout=hard_timeout_s)
                            except concurrent.futures.TimeoutError:
                                tomo_logger.logger.critical(
                                    "Detector: get_image HARD TIMEOUT (%.1fs) — "
                                    "USB hang detected. Завершаем tomograph_server "
                                    "для автоматического перезапуска Docker.",
                                    hard_timeout_s,
                                )
                                sys.exit(1)
                        if frame_numb == 0:
                            data = frame_data
                        else:
                            data += frame_data
                finally:
                    self.cam.stop_acquisition()

        except xiapi.Xi_error as err:
            # If persistent acquisition broke mid-series — mark it stopped so
            # subsequent calls fall back to legacy mode automatically.
            if self._acquisition_active:
                tomo_logger.logger.warning(
                    "Detector: error during persistent acquisition — "
                    "resetting to legacy mode"
                )
                self._acquisition_active = False
                self._trigger_mode = False
                try:
                    self.cam.stop_acquisition()
                except Exception:
                    pass
                try:
                    self.cam.set_trigger_source("XI_TRG_OFF")
                except Exception:
                    pass
            tomo_logger.logger.error("Detector.get_frame() failed " + str(err))
            raise RuntimeError("Detector.get_frame() failed " + str(err))

        if data is None:
            raise RuntimeError("Detector.get_frame() failed: no frames captured")
        # Clip and convert back to uint16
        return np.clip(data, 0, 65535).astype(np.uint16)

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
