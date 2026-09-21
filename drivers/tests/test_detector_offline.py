# pytest -v drivers/tests/test_detector_offline.py
"""Офлайн-тесты драйвера детектора: камера подменяется заглушкой.

Железо не нужно — проверяется логика драйвера:
ленивый старт захвата, программный триггер на кадр, сброс состояния при
ошибке посреди серии, зависание -> DetectorHangError + колбэк on_hang,
идемпотентный close().
"""
import sys
import types
import threading

import numpy as np
import pytest


def _install_ximea_stub():
    """Подсунуть пустую заглушку пакета ``ximea``.

    Нужна только чтобы модуль драйвера импортировался там, где XIMEA SDK
    не установлен (Windows, CI). Сами тесты подменяют ``Detector.xiapi``
    на полноценную заглушку камеры (см. FakeXiapi).
    """
    ximea = types.ModuleType('ximea')
    xiapi = types.ModuleType('ximea.xiapi')

    class Xi_error(Exception):
        pass

    class Camera(object):
        pass

    class Image(object):
        pass

    xiapi.Xi_error = Xi_error
    xiapi.Camera = Camera
    xiapi.Image = Image
    ximea.xiapi = xiapi
    sys.modules.setdefault('ximea', ximea)
    sys.modules.setdefault('ximea.xiapi', xiapi)


try:
    from ..Detector import Detector as detector_module
except ImportError:
    _install_ximea_stub()
    from ..Detector import Detector as detector_module


# ----------------------------------------------------------------------
# Заглушка камеры XIMEA
# ----------------------------------------------------------------------

class FakeXiError(Exception):
    """Аналог xiapi.Xi_error."""

    def __init__(self, message='fake xi error'):
        super(FakeXiError, self).__init__(message)


class FakeImage(object):
    def __init__(self):
        self.value = 0

    def get_image_data_numpy(self):
        return np.full((4, 4), self.value, dtype=np.uint16)


class FakeCamera(object):
    """Минимальная заглушка ``xiapi.Camera`` с журналом вызовов."""

    def __init__(self):
        self.CAM_OPEN = False
        self.calls = []                 # журнал вызовов, по именам методов
        self.acquisition_running = False
        self.trigger_source = None
        self.exposure_us = None
        self.device_name = b'MH110XC-KK-FA'
        self.fail_get_image_with = None  # исключение для следующего get_image
        self.fail_configure_with = None  # исключение при set_imgdataformat
        self.hang_get_image = threading.Event()   # set -> get_image зависает
        self.release_hang = threading.Event()     # для корректного завершения теста
        self.frames_taken = 0

    # --- lifecycle ---
    def open_device(self):
        self.calls.append('open_device')
        self.CAM_OPEN = True

    def close_device(self):
        self.calls.append('close_device')
        self.CAM_OPEN = False

    def set_debug_level(self, level):
        pass

    # --- configuration ---
    def disable_aeag(self):
        self.calls.append('disable_aeag')

    def set_gain(self, gain):
        pass

    def set_cooling(self, mode):
        pass

    def set_target_temp(self, temp):
        pass

    def set_imgdataformat(self, fmt):
        if self.fail_configure_with is not None:
            raise self.fail_configure_with

    def get_device_name(self, buffer_size=256):
        if isinstance(self.device_name, Exception):
            raise self.device_name
        return self.device_name

    # --- acquisition ---
    def set_exposure(self, exposure_us):
        self.calls.append('set_exposure')
        self.exposure_us = exposure_us

    def set_exposure_direct(self, exposure_us):
        self.calls.append('set_exposure_direct')
        self.exposure_us = exposure_us

    def get_exposure(self):
        return self.exposure_us or 0

    def set_trigger_source(self, source):
        self.calls.append('set_trigger_source:' + source)
        self.trigger_source = source

    def set_trigger_selector(self, selector):
        self.calls.append('set_trigger_selector')

    def set_trigger_overlap(self, overlap):
        self.calls.append('set_trigger_overlap')

    def start_acquisition(self):
        self.calls.append('start_acquisition')
        if self.acquisition_running:
            raise FakeXiError('already running')
        self.acquisition_running = True

    def stop_acquisition(self):
        self.calls.append('stop_acquisition')
        if not self.acquisition_running:
            raise FakeXiError('not running')
        self.acquisition_running = False

    def set_trigger_software(self, value):
        self.calls.append('set_trigger_software')
        if not self.acquisition_running:
            raise FakeXiError('acquisition is not running')

    def get_image(self, image, timeout=5000):
        self.calls.append('get_image')
        if self.hang_get_image.is_set():
            # имитируем зависший xiGetImage: возврата нет, пока тест не отпустит
            self.release_hang.wait(30)
            return
        if self.fail_get_image_with is not None:
            error, self.fail_get_image_with = self.fail_get_image_with, None
            raise error
        self.frames_taken += 1
        image.value = self.frames_taken

    # --- telemetry ---
    def get_temp(self):
        return 15.0

    def get_hous_temp(self):
        return 25.0


class FakeXiapi(object):
    """Подмена модуля ``xiapi`` внутри Detector.py."""
    Xi_error = FakeXiError
    Image = FakeImage

    def __init__(self):
        self.camera = FakeCamera()

    def Camera(self):
        return self.camera


@pytest.fixture
def fake_xiapi(monkeypatch):
    fake = FakeXiapi()
    monkeypatch.setattr(detector_module, 'xiapi', fake)
    monkeypatch.setattr(detector_module, '_on_hang_hook', None, raising=False)
    return fake


@pytest.fixture
def detector(fake_xiapi):
    d = detector_module.HWDetector()
    yield d
    fake_xiapi.camera.release_hang.set()
    try:
        d.close()
    except Exception:
        pass


def _count(cam, name):
    return cam.calls.count(name)


# ----------------------------------------------------------------------
# Тесты
# ----------------------------------------------------------------------

def test_init_caches_model_and_pixel_size(detector):
    """Модель читается один раз, размер пикселя берётся из таблицы."""
    assert detector.get_model() == 'MH110XC-KK-FA'
    assert detector.get_pixel_size() == detector_module.PIXEL_SIZES['MH110XC-KK-FA']


def test_init_unknown_model_falls_back_with_warning(fake_xiapi, caplog):
    """Неизвестная модель -> размер пикселя по умолчанию + WARNING один раз."""
    fake_xiapi.camera.device_name = b'SOME-UNKNOWN-CAM'
    d = detector_module.HWDetector()
    try:
        with caplog.at_level('WARNING'):
            assert d.get_pixel_size() == detector_module.DEFAULT_PIXEL_SIZE
            assert d.get_pixel_size() == detector_module.DEFAULT_PIXEL_SIZE
        warnings = [r for r in caplog.records if 'размер пикселя' in r.getMessage()]
        assert len(warnings) == 1, 'WARNING должен писаться один раз'
    finally:
        d.close()


def test_init_closes_device_when_configuration_fails(fake_xiapi):
    """Ошибка конфигурации после open_device() -> close_device() до проброса."""
    fake_xiapi.camera.fail_configure_with = FakeXiError('no such format')
    with pytest.raises(RuntimeError):
        detector_module.HWDetector()
    assert fake_xiapi.camera.CAM_OPEN is False
    assert 'close_device' in fake_xiapi.camera.calls


def test_lazy_start_and_software_trigger(detector, fake_xiapi):
    """Первый кадр поднимает захват; дальше — только софт-триггер на кадр."""
    cam = fake_xiapi.camera
    assert cam.acquisition_running is False, 'захват не должен стартовать в __init__'

    frame = detector.get_frame(0.01)
    assert isinstance(frame, np.ndarray) and frame.dtype == np.uint16
    assert cam.acquisition_running is True
    assert _count(cam, 'start_acquisition') == 1
    assert cam.trigger_source == 'XI_TRG_SOFTWARE'

    detector.get_frame(0.01)
    detector.get_frame(0.01)
    assert _count(cam, 'start_acquisition') == 1, 'захват стартует ровно один раз'
    assert _count(cam, 'set_trigger_software') == 3, 'по триггеру на каждый кадр'
    assert _count(cam, 'stop_acquisition') == 0


def test_exposure_change_without_restart(detector, fake_xiapi):
    """Смена экспозиции идёт через set_exposure_direct, без stop/start."""
    cam = fake_xiapi.camera
    detector.get_frame(0.01)
    detector.get_frame(0.02)
    assert _count(cam, 'set_exposure_direct') == 1
    assert _count(cam, 'start_acquisition') == 1
    assert cam.exposure_us == 20000


def test_start_stop_acquisition_idempotent(detector, fake_xiapi):
    """start/stop можно звать повторно — Flask-слой делает это на эксперимент."""
    cam = fake_xiapi.camera
    detector.start_acquisition(0.01)
    detector.start_acquisition(0.01, use_trigger=True)
    assert _count(cam, 'start_acquisition') == 1

    detector.stop_acquisition()
    detector.stop_acquisition()
    assert _count(cam, 'stop_acquisition') == 1
    assert cam.trigger_source == 'XI_TRG_OFF'

    detector.get_frame(0.01)
    assert _count(cam, 'start_acquisition') == 2, 'после stop захват поднимается заново'


@pytest.mark.parametrize('error', [FakeXiError('read failed'), MemoryError('oom')],
                         ids=['xi_error', 'memory_error'])
def test_error_mid_capture_resets_state(detector, fake_xiapi, error):
    """Любая ошибка посреди серии сбрасывает состояние захвата."""
    cam = fake_xiapi.camera
    detector.get_frame(0.01)

    cam.fail_get_image_with = error
    with pytest.raises(RuntimeError):
        detector.get_frame(0.01)

    assert detector._acquisition_active is False
    assert cam.acquisition_running is False
    assert cam.trigger_source == 'XI_TRG_OFF'

    # следующий вызов поднимает захват заново и отдаёт кадр
    frame = detector.get_frame(0.01)
    assert isinstance(frame, np.ndarray)
    assert _count(cam, 'start_acquisition') == 2


def test_hang_raises_and_calls_on_hang(fake_xiapi, monkeypatch):
    """Зависание xiGetImage -> DetectorHangError + колбэк, процесс жив."""
    monkeypatch.setattr(detector_module, 'SDK_TIMEOUT_MARGIN_MS', 10.0)
    monkeypatch.setattr(detector_module, 'HARD_TIMEOUT_MARGIN_S', 0.3)

    seen = []
    d = detector_module.HWDetector(on_hang=seen.append)
    cam = fake_xiapi.camera
    try:
        cam.hang_get_image.set()
        with pytest.raises(detector_module.DetectorHangError):
            d.get_frame(0.01)

        assert len(seen) == 1
        assert isinstance(seen[0], detector_module.DetectorHangError)

        # повторный вызов не вешает вызывающего ещё на один таймаут
        calls_before = len(cam.calls)
        with pytest.raises(detector_module.DetectorHangError):
            d.get_frame(0.01)
        assert len(cam.calls) == calls_before, 'зависшую камеру больше не трогаем'

        # close() не закрывает устройство, пока поток сидит в xiGetImage
        d.close()
        assert cam.CAM_OPEN is True
        assert 'close_device' not in cam.calls
    finally:
        cam.release_hang.set()


def test_on_hang_module_hook(fake_xiapi, monkeypatch):
    """Процессный колбэк из set_on_hang() используется, если не задан в ctor."""
    monkeypatch.setattr(detector_module, 'SDK_TIMEOUT_MARGIN_MS', 10.0)
    monkeypatch.setattr(detector_module, 'HARD_TIMEOUT_MARGIN_S', 0.3)

    seen = []
    monkeypatch.setattr(detector_module, '_on_hang_hook', seen.append, raising=False)

    d = detector_module.HWDetector()
    cam = fake_xiapi.camera
    try:
        cam.hang_get_image.set()
        with pytest.raises(detector_module.DetectorHangError):
            d.get_frame(0.01)
        assert len(seen) == 1
    finally:
        cam.release_hang.set()
        d.close()


def test_close_is_idempotent(fake_xiapi):
    """Повторный close() (в т.ч. из atexit) ничего не ломает."""
    d = detector_module.HWDetector()
    cam = fake_xiapi.camera
    d.get_frame(0.01)

    d.close()
    d.close()

    assert _count(cam, 'close_device') == 1
    assert _count(cam, 'stop_acquisition') == 1
    assert cam.CAM_OPEN is False

    with pytest.raises(RuntimeError):
        d.get_frame(0.01)


def test_timeout_formula():
    """Одна формула таймаутов: SDK-таймаут и hard-таймаут связаны."""
    exposure_s = 2.0
    sdk_ms = detector_module.sdk_timeout_ms(exposure_s)
    assert sdk_ms == int(round(2000 * detector_module.SDK_TIMEOUT_FACTOR
                               + detector_module.SDK_TIMEOUT_MARGIN_MS))
    hard_s = detector_module.expected_frame_timeout_s(exposure_s)
    assert hard_s == pytest.approx(sdk_ms / 1e3 + detector_module.HARD_TIMEOUT_MARGIN_S)
    assert hard_s > exposure_s
