# pytest --log-cli-level=INFO -s -v test_motors.py
import logging
import numpy as np
from ..Motors.Motor import HWMotor, print_test_info
from ..utils import get_angle_motor_config, get_horizontal_motor_config

# Допустимая погрешность возврата в исходную позицию
ANGLE_TOLERANCE_DEG = 0.1   # градусы
LINEAR_TOLERANCE_STEPS = 5  # шаги


def test_angle_motor():
    """Тест углового (вращательного) мотора.

    Проверяет:
    - Устройство открывается и читает служебную информацию.
    - Текущая позиция читается в градусах.
    - Небольшое движение +2° выполняется точно.
    - Возврат в исходную позицию выполняется точно.
    """
    config = get_angle_motor_config()
    logging.info("Angle motor config: %s", config)

    motor = HWMotor(config['port'], config['speed'], config['acceleration'], config['step_360'])

    info = motor.get_info()
    logging.info("Motor info: %s", info)
    assert info.get('error') is None, "get_info() вернул ошибку: {}".format(info)

    status = motor.get_status()
    logging.info("Motor status: %s", status)

    power_info = motor.get_power_info()
    logging.info("Motor power info: %s", power_info)

    pos_0 = motor.get_position_deg()
    logging.info("Initial position: %.4f °", pos_0)

    target = (pos_0 + 2.0) % 360.0
    motor.move_to_position_deg(target)
    pos_1 = motor.get_position_deg()
    logging.info("After +2°: %.4f ° (expected %.4f °)", pos_1, target)
    assert abs(pos_1 - target) < ANGLE_TOLERANCE_DEG, \
        "Угол после движения {:.4f}° не совпадает с ожидаемым {:.4f}° (допуск {})".format(
            pos_1, target, ANGLE_TOLERANCE_DEG)

    motor.move_to_position_deg(pos_0)
    pos_2 = motor.get_position_deg()
    logging.info("After return: %.4f ° (expected %.4f °)", pos_2, pos_0)
    assert abs(pos_2 - pos_0) < ANGLE_TOLERANCE_DEG, \
        "Угол после возврата {:.4f}° не совпадает с исходным {:.4f}° (допуск {})".format(
            pos_2, pos_0, ANGLE_TOLERANCE_DEG)


def test_horizontal_motor():
    """Тест горизонтального (линейного) мотора.

    Линейный мотор: deg-методы не используются, позиция в шагах.

    Проверяет:
    - Устройство открывается и читает служебную информацию.
    - Текущая позиция читается в шагах.
    - Смещение +100 шагов выполняется точно.
    - Возврат на -100 шагов выполняется точно.
    """
    config = get_horizontal_motor_config()
    logging.info("Horizontal motor config: %s", config)

    # steps_on_deg=None — линейный мотор, deg-методы не применяются
    motor = HWMotor(config['port'], config['speed'], config['acceleration'], steps_on_deg=None)

    info = motor.get_info()
    logging.info("Motor info: %s", info)
    assert info.get('error') is None, "get_info() вернул ошибку: {}".format(info)

    status = motor.get_status()
    logging.info("Motor status: %s", status)

    power_info = motor.get_power_info()
    logging.info("Motor power info: %s", power_info)

    pos_0 = motor.get_position()
    logging.info("Initial position: %.2f steps", pos_0)

    motor.move_by_delta(100)
    pos_1 = motor.get_position()
    logging.info("After +100 steps: %.2f (expected %.2f)", pos_1, pos_0 + 100)
    assert abs(pos_1 - (pos_0 + 100)) < LINEAR_TOLERANCE_STEPS, \
        "Позиция после движения {:.2f} не совпадает с ожидаемой {:.2f} (допуск {})".format(
            pos_1, pos_0 + 100, LINEAR_TOLERANCE_STEPS)

    motor.move_by_delta(-100)
    pos_2 = motor.get_position()
    logging.info("After return: %.2f (expected %.2f)", pos_2, pos_0)
    assert abs(pos_2 - pos_0) < LINEAR_TOLERANCE_STEPS, \
        "Позиция после возврата {:.2f} не совпадает с исходной {:.2f} (допуск {})".format(
            pos_2, pos_0, LINEAR_TOLERANCE_STEPS)
