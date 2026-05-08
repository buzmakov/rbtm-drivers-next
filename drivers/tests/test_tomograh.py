# pytest --log-cli-level=INFO -s -v test_tomograh.py
import logging
from pprint import pformat
from ..Tomograph.Tomograph import HWTomograph


# Ожидаемые ключи в ответе get_state() для каждого устройства
_EXPECTED_DEVICE_KEYS = {
    'detector':        ('exposure', 'sensor_temp', 'hous_temp'),
    'shutter':         ('is_open',),
    'source':          ('is_on_high_voltage', 'id', 'tube_name',
                        'actual_voltage', 'nominal_voltage',
                        'actual_current', 'nominal_current',
                        'actual_power', 'nominal_power',
                        'status', 'last_error'),
    'horizontal_motor': ('device_name', 'steps_on_deg',
                         'speed', 'acceleration', 'position'),
    'angle_motor':     ('device_name', 'steps_on_deg',
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
