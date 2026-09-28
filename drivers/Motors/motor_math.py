"""Чистые вычисления для драйвера моторов XIMC.

Модуль намеренно не импортирует ``pyximc``/``libximc``: его функции можно
тестировать без подключённого оборудования (см. ``drivers/tests/test_motor_math.py``).
"""

#: Число микрошагов в одном полном шаге (режим MICROSTEP_MODE_FRAC_256).
MICROSTEPS_PER_STEP = 256

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


def to_steps(total_steps):
    """Разложить дробное число шагов на (Position, uPosition) для libximc.

    По документации libximc (``ximc.h``, ``command_move``/``get_position_t``)
    поле ``uPosition`` — знаковое, диапазон -255..255, и знак у него тот же,
    что у ``Position``: контроллер отдаёт позицию как ``Position + uPosition/256``
    с одинаковыми знаками обеих частей. Поэтому округление здесь идёт
    "к нулю" (а не floor, как было раньше): floor давал для -1.5 пару
    ``(-2, +128)`` — арифметически то же число, но с разными знаками частей,
    чего прошивка не ожидает.

    :param total_steps: float — позиция или смещение в шагах (дробное).
    :return: tuple (position: int, uposition: int), знаки совпадают,
             |uposition| <= 255.
    """
    total = float(total_steps)
    sign = -1 if total < 0 else 1
    micro = int(round(abs(total) * MICROSTEPS_PER_STEP))
    steps, usteps = divmod(micro, MICROSTEPS_PER_STEP)
    return sign * steps, sign * usteps


def normalize_deg(angle_deg):
    """Привести угол к диапазону [0, 360).

    :param angle_deg: float — угол в градусах (любой знак и величина).
    :return: float — угол в [0, 360).
    """
    res = float(angle_deg) % 360.0
    # для очень малых отрицательных углов x % 360.0 округляется ровно до 360.0
    if res >= 360.0:
        return 0.0
    return res


def shortest_delta_deg(current_deg, target_deg):
    """Кратчайшее угловое смещение от текущего угла к целевому.

    Результат лежит в (-180, 180]: например, из 359.5° в 0° это +0.5°,
    а не -359.5° (полный оборот назад ≈ 65 с на угловом моторе томографа).

    :param current_deg: float — текущий угол, градусы (нормализация не нужна).
    :param target_deg: float — целевой угол, градусы (нормализация не нужна).
    :return: float — смещение в градусах, (-180, 180].
    """
    delta = (float(target_deg) - float(current_deg)) % 360.0
    if delta > 180.0:
        delta -= 360.0
    return delta


def from_steps(position, uposition=0):
    """Собрать дробное число шагов из (Position, uPosition).

    :param position: int — целая часть в шагах.
    :param uposition: int — дробная часть в микрошагах (знак как у position).
    :return: float — позиция в шагах.
    """
    return position + uposition / float(MICROSTEPS_PER_STEP)
