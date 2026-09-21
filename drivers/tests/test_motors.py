# pytest --log-cli-level=INFO -s -v test_motors.py
import logging
import numpy as np
from ..Motors.Motor import HWRotaryMotor, HWLinearMotor
from ..utils import get_angle_motor_config, get_horizontal_motor_config

# Допустимая погрешность возврата в исходную позицию
ANGLE_TOLERANCE_DEG = 0.1    # градусы
LINEAR_TOLERANCE_MM = 0.05   # миллиметры (~10 шагов при steps_per_mm=199.46)


def test_angle_motor():
    """Тест углового (вращательного) мотора HWRotaryMotor.

    Проверяет:
    - Устройство открывается и читает служебную информацию.
    - Текущая позиция читается в градусах.
    - Небольшое движение +2° выполняется точно.
    - Возврат в исходную позицию выполняется точно.
    """
    config = get_angle_motor_config()
    logging.info("Angle motor config: %s", config)

    motor = HWRotaryMotor(config['port'], config['speed'], config['acceleration'],
                          steps_on_deg=config['step_360'])

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
    """Тест горизонтального (линейного) мотора HWLinearMotor.

    Проверяет:
    - Устройство открывается и читает служебную информацию.
    - Текущая позиция читается в миллиметрах.
    - Смещение +0.5 мм выполняется точно.
    - Возврат на -0.5 мм выполняется точно.
    - move_outside() перемещает в позицию парковки без ошибок.
    - Возврат в нулевую позицию (move_to_position(0)) выполняется без ошибок.
    """
    config = get_horizontal_motor_config()
    logging.info("Horizontal motor config: %s", config)

    motor = HWLinearMotor(config['port'], config['speed'], config['acceleration'],
                          steps_per_mm=config['steps_per_mm'],
                          move_outside_mm=config['move_outside_mm'])

    info = motor.get_info()
    logging.info("Motor info: %s", info)
    assert info.get('error') is None, "get_info() вернул ошибку: {}".format(info)

    status = motor.get_status()
    logging.info("Motor status: %s", status)

    power_info = motor.get_power_info()
    logging.info("Motor power info: %s", power_info)

    pos_0_mm = motor.get_position_mm()
    logging.info("Initial position: %.4f mm", pos_0_mm)

    delta_mm = 0.5
    motor.move_by_delta_mm(delta_mm)
    pos_1_mm = motor.get_position_mm()
    logging.info("After +%.2f mm: %.4f mm (expected %.4f mm)", delta_mm, pos_1_mm, pos_0_mm + delta_mm)
    assert abs(pos_1_mm - (pos_0_mm + delta_mm)) < LINEAR_TOLERANCE_MM, \
        "Позиция после движения {:.4f} мм не совпадает с ожидаемой {:.4f} мм (допуск {})".format(
            pos_1_mm, pos_0_mm + delta_mm, LINEAR_TOLERANCE_MM)

    motor.move_by_delta_mm(-delta_mm)
    pos_2_mm = motor.get_position_mm()
    logging.info("After return: %.4f mm (expected %.4f mm)", pos_2_mm, pos_0_mm)
    assert abs(pos_2_mm - pos_0_mm) < LINEAR_TOLERANCE_MM, \
        "Позиция после возврата {:.4f} мм не совпадает с исходной {:.4f} мм (допуск {})".format(
            pos_2_mm, pos_0_mm, LINEAR_TOLERANCE_MM)

    # Проверяем парковку: move_outside() перемещает в позицию конфига
    logging.info("Testing move_outside() → %.4f mm", motor.move_outside_mm)
    motor.move_outside()
    pos_out_mm = motor.get_position_mm()
    logging.info("After move_outside(): %.4f mm (expected %.4f mm)", pos_out_mm, motor.move_outside_mm)
    assert abs(pos_out_mm - motor.move_outside_mm) < LINEAR_TOLERANCE_MM, \
        "Позиция после move_outside() {:.4f} мм не совпадает с {:.4f} мм (допуск {})".format(
            pos_out_mm, motor.move_outside_mm, LINEAR_TOLERANCE_MM)

    # Возврат в рабочую позицию (нуль)
    motor.move_to_position(0)
    pos_home_mm = motor.get_position_mm()
    logging.info("After return to 0: %.4f mm", pos_home_mm)
    assert abs(pos_home_mm) < LINEAR_TOLERANCE_MM, \
        "Позиция после возврата в 0 {:.4f} мм не совпадает с нулём (допуск {})".format(
            pos_home_mm, LINEAR_TOLERANCE_MM)
