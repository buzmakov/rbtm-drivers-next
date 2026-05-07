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
    port = get_info_from_config("x-ray source", "port")
    return {'port': port}


def get_angle_motor_config():
    port = get_info_from_config("angle motor", "port")
    step_360 = get_info_from_config("angle motor", "step_in_360")
    speed = get_info_from_config("angle motor", "speed")
    acceleration = get_info_from_config("angle motor", "acceleration")
    return {'port': port, "step_360": float(step_360) / 360.,
            "speed": speed, "acceleration": acceleration}


def get_horizontal_motor_config():
    """
    Прочитать конфигурацию горизонтального (линейного) мотора из devices.cfg.

    Горизонтальный мотор — линейный. Параметр 'move_object_outside' задаёт позицию
    в шагах, на которую нужно сместить объект, чтобы вывести его из рентгеновского пучка.
    steps_on_deg для этого мотора не применяется (передаётся None в HWMotor).

    TODO: архитектурная проблема — горизонтальный мотор линейный, но использует тот же
          класс HWMotor, что и вращательный угловой мотор. Требуется рефакторинг на
          отдельные классы HWRotaryMotor / HWLinearMotor.
    """
    port = get_info_from_config("horizontal motor", "port")
    move_object_outside = int(get_info_from_config("horizontal motor", "move_object_outside"))
    speed = get_info_from_config("horizontal motor", "speed")
    acceleration = get_info_from_config("horizontal motor", "acceleration")
    return {
        'port': port,
        'move_object_outside': move_object_outside,
        'speed': speed,
        'acceleration': acceleration,
        # steps_on_deg не применяется для линейного мотора
        'step_360': None,
    }


if __name__ == '__main__':
    print('Shutter settings:', get_shutter_config())
    print('Source settings:', get_source_config())
    print('Angle motor settings:', get_angle_motor_config())
    print('Horizontal motor settings:', get_horizontal_motor_config())
