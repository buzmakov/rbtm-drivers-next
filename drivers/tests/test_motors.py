from ..Motors.Motor import HWMotor, print_test_info
from ..utils import get_angle_motor_config

def test_angle_motor():
#     print(print_test_info())
    config = get_angle_motor_config()
    print(config)
    motor = HWMotor(config['port'], config['step_360'],
            config['speed'], config['acceleration'])
    motor.test_info()