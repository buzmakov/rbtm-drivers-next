# pytest --log-cli-level=INFO -s -v -m hardware drivers/tests/test_detector.py
#
# Тесты требуют реальной камеры XIMEA и остановленного tomograph_server
# (иначе устройство занято сервером). Офлайн-логика драйвера проверяется
# в test_detector_offline.py.
import logging

import numpy as np
import pytest

try:
    from ..Detector import Detector as _detector_module
except ImportError as err:  # XIMEA SDK не установлен — железных тестов нет
    pytest.skip("XIMEA SDK is not available: {}".format(err),
                allow_module_level=True)

# Офлайн-тесты (test_detector_offline.py) подсовывают заглушку пакета ximea,
# чтобы модуль драйвера импортировался без SDK. Отличаем её от настоящего
# биндинга по наличию методов у Camera — иначе железные тесты «успешно»
# запустились бы на заглушке.
if not hasattr(_detector_module.xiapi.Camera, 'open_device'):
    pytest.skip("XIMEA SDK is not available (ximea stub is installed)",
                allow_module_level=True)

HWDetector = _detector_module.HWDetector

pytestmark = pytest.mark.hardware


@pytest.fixture
def detector():
    """Open HWDetector once per test and guarantee close() on teardown."""
    d = HWDetector()
    yield d
    d.close()


def test_detector_connection(detector):
    """Быстрая проверка подключения детектора и чтение метаданных.

    Проверяет:
    - Детектор открывается без ошибок.
    - get_model() возвращает непустую строку (кэш из __init__).
    - get_pixel_size() возвращает положительное число.
    - get_state() возвращает словарь с ключами exposure, sensor_temp, hous_temp.
    - Температуры в допустимом диапазоне (-50 … 50 °C).
    """
    model = detector.get_model()
    logging.info("Detector model: %s", model)
    assert isinstance(model, str) and len(model) > 0, \
        "get_model() должен вернуть непустую строку"

    pixel_size = detector.get_pixel_size()
    logging.info("Pixel size: %s mm", pixel_size)
    assert isinstance(pixel_size, float) and pixel_size > 0, \
        "get_pixel_size() должен вернуть положительное число"

    state = detector.get_state()
    logging.info("Detector state: %s", state)
    for key in ('exposure', 'sensor_temp', 'hous_temp'):
        assert key in state, "get_state() должен содержать ключ '{}'".format(key)

    sensor_temp = detector.get_sensor_temp()
    hous_temp = detector.get_hous_temp()
    logging.info("Sensor temp: %.2f °C, Housing temp: %.2f °C", sensor_temp, hous_temp)
    assert -50 < sensor_temp < 50, \
        "Температура сенсора вне допустимого диапазона: {}".format(sensor_temp)
    assert -50 < hous_temp < 50, \
        "Температура корпуса вне допустимого диапазона: {}".format(hous_temp)


def test_detector_capture(detector):
    """Захват кадров с экспозицией 0.1 с (ленивый старт постоянного захвата).

    Проверяет:
    - Первый get_frame() сам поднимает постоянный захват.
    - Возвращается numpy.ndarray с dtype uint16, 2D, ненулевого размера.
    - Второй кадр снимается без повторного старта захвата.
    """
    assert detector._acquisition_active is False, \
        "захват не должен стартовать в __init__"

    frame = detector.get_frame(0.1)
    logging.info("Frame shape: %s, dtype: %s", frame.shape, frame.dtype)
    logging.info("Frame mean: %.1f, max: %d", frame.mean(), frame.max())

    assert isinstance(frame, np.ndarray), \
        "get_frame() должен вернуть numpy.ndarray"
    assert frame.dtype == np.uint16, \
        "dtype должен быть uint16, получен: {}".format(frame.dtype)
    assert frame.ndim == 2, \
        "Кадр должен быть двумерным (H, W)"
    assert frame.shape[0] > 0 and frame.shape[1] > 0, \
        "Размер кадра не должен быть нулевым: {}".format(frame.shape)
    assert detector._acquisition_active is True, \
        "после первого кадра постоянный захват должен быть активен"

    second = detector.get_frame(0.1)
    assert second.shape == frame.shape
    assert detector._acquisition_active is True


def test_detector_explicit_acquisition_cycle(detector):
    """Явный цикл start_acquisition() → кадры → stop_acquisition().

    Так детектором пользуется Flask-слой в эксперименте.
    Проверяет идемпотентность start/stop и смену экспозиции на лету.
    """
    detector.start_acquisition(0.1)
    detector.start_acquisition(0.1)  # повторный вызов игнорируется
    assert detector._acquisition_active is True

    first = detector.get_frame(0.1)
    second = detector.get_frame(0.2)  # экспозиция меняется без stop/start
    assert first.shape == second.shape
    assert detector._acquisition_active is True

    detector.stop_acquisition()
    detector.stop_acquisition()  # идемпотентно
    assert detector._acquisition_active is False

    # после остановки захват поднимается заново лениво
    third = detector.get_frame(0.1)
    assert third.shape == first.shape
