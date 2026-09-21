"""Чистые вычисления для драйвера моторов XIMC.

Модуль намеренно не импортирует ``pyximc``/``libximc``: его функции можно
тестировать без подключённого оборудования (см. ``drivers/tests/test_motor_math.py``).
"""

#: Множитель к расчётному времени движения (расстояние / скорость).
MOVE_TIMEOUT_FACTOR = 1.5
#: Постоянная добавка к таймауту движения, с (разгон/торможение, обмен по USB).
MOVE_TIMEOUT_EXTRA_S = 5.0


def move_timeout_s(distance_steps, speed_steps_per_s,
                   factor=MOVE_TIMEOUT_FACTOR, extra_s=MOVE_TIMEOUT_EXTRA_S):
    """Оценить таймаут ожидания остановки для перемещения.

    :param distance_steps: float — длина перемещения в шагах (знак не важен).
    :param speed_steps_per_s: float — скорость контроллера в шагах/с.
    :param factor: float — запас на разгон/торможение.
    :param extra_s: float — постоянная добавка, с.
    :return: float — таймаут в секундах (всегда >= extra_s).
    """
    distance = abs(float(distance_steps))
    speed = abs(float(speed_steps_per_s))
    if speed <= 0:
        return float(extra_s)
    return distance / speed * float(factor) + float(extra_s)
