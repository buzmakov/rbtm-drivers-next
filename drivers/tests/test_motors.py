from ..Motors.Motor import HWMotor, print_test_info
from ..utils import get_angle_motor_config, get_horizontal_motor_config

def test_angle_motor():
    config = get_angle_motor_config()
    print(config)
    motor = HWMotor(config['port'], config['speed'], config['acceleration'], config['step_360'], )
    motor.open()
    print(motor.get_info())
    print(motor.get_status())
    print(motor.get_position())
    motor.close()


def test_horizontal_motor():
    config = get_horizontal_motor_config()
    print(config)
    motor = HWMotor(config['port'], config['speed'], config['acceleration'])
    motor.open()
    print(motor.get_info())
    print(motor.get_status())
    print(motor.get_position())
    motor.close()
