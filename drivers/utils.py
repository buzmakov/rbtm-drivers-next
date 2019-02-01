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
    return {'port': port, "step_360":step_360, 
        "speed": speed, "acceleration":acceleration}


def get_horizontal_motor_config():
    port = get_info_from_config("horizontal motor", "port")
    speed = get_info_from_config("angle motor", "speed")
    acceleration = get_info_from_config("angle motor", "acceleration")
    return {'port': port, "speed": speed, "acceleration":acceleration}


if __name__ == '__main__':
    print('Shutter settings:', get_shutter_config())
    print('Source settings:', get_source_config())
    print('Angle motor settings:', get_angle_motor_config())
    print('Horizontal motor settings:', get_horizontal_motor_config())
