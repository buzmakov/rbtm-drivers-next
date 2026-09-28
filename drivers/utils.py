from configparser import RawConfigParser
import os

CONFIG_PATH = os.path.join(os.path.dirname(__file__), 'config', 'devices.cfg')


def get_info_from_config(device, param):
    config = RawConfigParser()
    config.read(CONFIG_PATH)
    value = config[device][param]
    return value


def get_shutter_config():
    port = get_info_from_config("shutter", "port")
    relay_number = int(get_info_from_config("shutter", "relay"))
    return {'port': port, 'relay_number': relay_number}


def get_source_config():
    """Прочитать конфигурацию рентгеновского источника из devices.cfg.

    Returns:
        dict: ``{'port': str, 'mock': bool}``
    """
    port = get_info_from_config("x-ray source", "port")
    mock = get_info_from_config("x-ray source", "mock").strip().lower() == 'true'
    return {'port': port, 'mock': mock}


def get_angle_motor_config():
    """Прочитать конфигурацию углового (вращательного) мотора из devices.cfg.

    Угловой мотор — вращательный (:class:`HWRotaryMotor`).

    Returns:
        dict с ключами:
            - 'port': str — имя устройства (порт).
            - 'speed': int — скорость в шагах/с.
            - 'acceleration': int — ускорение в шагах/с².
            - 'steps_per_deg': float — число шагов на градус, посчитанное из
              ключа конфига ``step_in_360`` (32400 шагов / 360° = 90 шагов/°).
    """
    port = get_info_from_config("angle motor", "port")
    steps_in_360 = float(get_info_from_config("angle motor", "step_in_360"))
    speed = int(get_info_from_config("angle motor", "speed"))
    acceleration = int(get_info_from_config("angle motor", "acceleration"))
    return {'port': port, 'steps_per_deg': steps_in_360 / 360.,
            'speed': speed, 'acceleration': acceleration}


def get_horizontal_motor_config():
    """
    Прочитать конфигурацию горизонтального (линейного) мотора из devices.cfg.

    Горизонтальный мотор — линейный (:class:`HWLinearMotor`).

    Returns:
        dict с ключами:
            - 'port': str — имя устройства (порт).
            - 'speed': int — скорость в шагах/с.
            - 'acceleration': int — ускорение в шагах/с².
            - 'steps_per_mm': float — число шагов на миллиметр (1 шаг = 5.0136 мкм → 199.46 шагов/мм).
            - 'move_outside_mm': float — позиция парковки объекта в мм (обычно отрицательная),
              читается из ключа конфига ``move_object_outside_mm``.
    """
    port = get_info_from_config("horizontal motor", "port")
    speed = int(get_info_from_config("horizontal motor", "speed"))
    acceleration = int(get_info_from_config("horizontal motor", "acceleration"))
    steps_per_mm = float(get_info_from_config("horizontal motor", "steps_per_mm"))
    move_outside_mm = float(get_info_from_config("horizontal motor", "move_object_outside_mm"))
    return {
        'port': port,
        'speed': speed,
        'acceleration': acceleration,
        'steps_per_mm': steps_per_mm,
        'move_outside_mm': move_outside_mm,
    }


if __name__ == '__main__':
    print('Shutter settings:', get_shutter_config())
    print('Source settings:', get_source_config())
    print('Angle motor settings:', get_angle_motor_config())
    print('Horizontal motor settings:', get_horizontal_motor_config())
