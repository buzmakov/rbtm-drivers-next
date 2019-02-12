from ..Motors.Motor import HWMotor, print_test_info
from ..utils import get_angle_motor_config, get_horizontal_motor_config
import logging
import numpy as np


def test_angle_motor():
    config = get_angle_motor_config()
    logging.info(config)
    motor = HWMotor(config['port'], config['speed'], config['acceleration'], config['step_360'])
    logging.info(motor.get_info())
    logging.info(motor.get_status())
    logging.info(motor.get_position())
    logging.info(motor.get_position_deg())
    pos_0 = motor.get_position_deg()
    motor.move_to_position_deg((pos_0 + 2) % 360)
    pos_1 = motor.get_position_deg()
    assert np.isclose(pos_1, (pos_0 + 2) % 360)
    motor.set_zero()
    assert np.isclose(motor.get_position_deg() % 360, 0)


def test_horizontal_motor():
    config = get_horizontal_motor_config()
    logging.info(config)
    motor = HWMotor(config['port'], config['speed'], config['acceleration'], config['step_360'])
    logging.info(motor.get_info())
    logging.info(motor.get_status())
    logging.info(motor.get_position())
