# pytest --log-cli-level=INFO -s -v test_detector.py
import logging
import pytest
import numpy as np
from ..Detector.Detector import HWDetector


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
    - get_model() возвращает непустую строку.
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
    """Захват одного кадра с экспозицией 0.1 с.

    Проверяет:
    - Возвращается numpy.ndarray с dtype uint16.
    - Размер кадра ненулевой по обоим измерениям.
    - Логируются mean и max пикселей для визуальной оценки.
    """
    frame = detector.get_frames(exposure=0.1, number_frames=1)
    logging.info("Frame shape: %s, dtype: %s", frame.shape, frame.dtype)
    logging.info("Frame mean: %.1f, max: %d", frame.mean(), frame.max())

    assert isinstance(frame, np.ndarray), \
        "get_frames() должен вернуть numpy.ndarray"
    assert frame.dtype == np.uint16, \
        "dtype должен быть uint16, получен: {}".format(frame.dtype)
    assert frame.ndim == 2, \
        "Кадр должен быть двумерным (H, W)"
    assert frame.shape[0] > 0 and frame.shape[1] > 0, \
        "Размер кадра не должен быть нулевым: {}".format(frame.shape)
