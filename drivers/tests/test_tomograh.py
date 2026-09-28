# pytest --log-cli-level=INFO -s -v -m hardware drivers/tests/test_tomograh.py
#
# Требуется подключённое оборудование и остановленный tomograph_server.
import logging
from pprint import pformat

import numpy as np
import pytest

try:
    from ..Tomograph.Tomograph import HWTomograph
except (ImportError, SystemExit) as err:  # нет pyximc/XIMEA SDK
    pytest.skip("Hardware drivers are not available: {}".format(err),
                allow_module_level=True)

pytestmark = pytest.mark.hardware


# Ожидаемые ключи в ответе get_state() для каждого устройства
_EXPECTED_DEVICE_KEYS = {
    'detector':        ('exposure', 'sensor_temp', 'hous_temp'),
    'shutter':         ('is_open',),
    'source':          ('is_on_high_voltage', 'id', 'tube_name',
                        'actual_voltage', 'nominal_voltage',
                        'actual_current', 'nominal_current',
                        'actual_power', 'nominal_power',
                        'status', 'last_error'),
    'horizontal_motor': ('device_name', 'steps_per_mm', 'move_outside_mm',
                         'speed', 'acceleration', 'position'),
    'angle_motor':      ('device_name', 'steps_on_deg',
                         'speed', 'acceleration', 'position'),
}


def test_tomograph_state():
    """Проверка состояния всего томографа через HWTomograph.get_state().

    Проверяет:
    - get_state() возвращает словарь.
    - В ответе присутствуют все пять устройств: shutter, source,
      horizontal_motor, angle_motor, detector.
    - Состояние каждого устройства — непустой dict без ключа 'error'.
    - Для каждого устройства присутствуют ожидаемые ключи состояния.
    """
    # mock=True явно переопределяет значение из devices.cfg —
    # при smoke-тесте не включаем реальное высокое напряжение
    t = HWTomograph(mock=True)
    state = t.get_state()

    logging.info("Tomograph state:\n%s", pformat(state))

    assert isinstance(state, dict), "get_state() должен вернуть dict"

    expected_devices = ('shutter', 'source', 'horizontal_motor', 'angle_motor', 'detector')
    for device in expected_devices:
        assert device in state, \
            "В ответе get_state() отсутствует устройство '{}'".format(device)
        device_state = state[device]
        assert isinstance(device_state, dict) and len(device_state) > 0, \
            "Состояние устройства '{}' должно быть непустым dict, получено: {}".format(
                device, device_state)

    # Проверяем присутствие ключей состояния для каждого устройства
    for device, expected_keys in _EXPECTED_DEVICE_KEYS.items():
        device_state = state.get(device, {})
        for key in expected_keys:
            assert key in device_state, \
                "В состоянии устройства '{}' отсутствует ключ '{}'".format(device, key)


def test_tomograph_capture_frame():
    """Кадр и метаданные одним вызовом HWTomograph.capture_frame().

    Проверяет структуру метаданных — ровно ту, что Flask-слой раньше
    собирал десятком отдельных RPC (get_detector_frame_metadata):
    - image_data: timestamp, datetime, exposure (мс), detector{model,
      pixel_size}, chip_temp, hous_temp;
    - object: angle position, horizontal position (present и vertical
      position добавляет Flask — их здесь быть не должно);
    - shutter: open;
    - X-ray source: voltage, current.
    """
    t = HWTomograph(mock=True)
    try:
        image, metadata = t.capture_frame(0.1)
    finally:
        t._release_devices()

    assert isinstance(image, np.ndarray) and image.dtype == np.uint16, \
        "capture_frame() должен вернуть кадр uint16"
    assert image.ndim == 2 and image.shape[0] > 0 and image.shape[1] > 0

    logging.info("Frame metadata:\n%s", pformat(metadata))

    for section in ('image_data', 'object', 'shutter', 'X-ray source'):
        assert section in metadata, "нет раздела '{}'".format(section)

    image_data = metadata['image_data']
    for key in ('timestamp', 'datetime', 'exposure', 'detector',
                'chip_temp', 'hous_temp'):
        assert key in image_data, "нет ключа image_data['{}']".format(key)
    assert set(image_data['detector']) == {'model', 'pixel_size'}
    assert image_data['detector']['pixel_size'] > 0

    assert set(metadata['object']) == {'angle position', 'horizontal position'}, \
        "present и vertical position принадлежат Flask-слою"
    assert set(metadata['shutter']) == {'open'}
    assert set(metadata['X-ray source']) == {'voltage', 'current'}
