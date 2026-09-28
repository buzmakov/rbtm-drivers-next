# pytest -v drivers/tests/test_motor_math.py
"""Тесты чистой арифметики драйвера моторов.

Оборудование и libximc не нужны: модуль ``drivers.Motors.motor_math``
не импортирует ``pyximc``.
"""
from ..Motors.motor_math import (MICROSTEPS_PER_STEP, move_timeout_s,
                                 to_steps, from_steps,
                                 normalize_deg, shortest_delta_deg)


# ─── to_steps / from_steps ───────────────────────────────────────────────────

def test_to_steps_positive():
    assert to_steps(0) == (0, 0)
    assert to_steps(10) == (10, 0)
    assert to_steps(1.5) == (1, 128)
    assert to_steps(0.25) == (0, 64)


def test_to_steps_negative_has_consistent_sign():
    """Position и uPosition должны быть одного знака (libximc: uPosition ∈ -255..255)."""
    assert to_steps(-1.5) == (-1, -128)
    assert to_steps(-0.25) == (0, -64)
    assert to_steps(-10) == (-10, 0)

    for total in (-0.1, -1.5, -21.06 * 199.46, -4200.75):
        steps, usteps = to_steps(total)
        assert abs(usteps) <= 255
        assert steps <= 0 and usteps <= 0, \
            'знаки частей разошлись для {}: {}'.format(total, (steps, usteps))


def test_to_steps_round_trip():
    for total in (0.0, 1.5, -1.5, 199.46, -199.46, -4200.0, 32400.75, -0.00390625):
        steps, usteps = to_steps(total)
        assert abs(from_steps(steps, usteps) - total) <= 1.0 / MICROSTEPS_PER_STEP


def test_to_steps_carries_to_whole_step():
    """Округление 255.6/256 микрошага не должно давать uPosition = 256."""
    assert to_steps(1 - 0.4 / MICROSTEPS_PER_STEP) == (1, 0)
    assert to_steps(-(1 - 0.4 / MICROSTEPS_PER_STEP)) == (-1, 0)


def test_from_steps():
    assert from_steps(0, 0) == 0.0
    assert from_steps(1, 128) == 1.5
    assert from_steps(-1, -128) == -1.5
    assert from_steps(5) == 5.0


# ─── move_timeout_s ──────────────────────────────────────────────────────────

def test_move_timeout_scales_with_distance():
    # полный оборот углового мотора: 32400 шагов при 500 шагах/с ≈ 64.8 с
    assert move_timeout_s(32400, 500) == 32400 / 500 * 1.5 + 5.0
    assert move_timeout_s(0, 500) == 5.0
    # знак расстояния не важен
    assert move_timeout_s(-1000, 200) == move_timeout_s(1000, 200)


def test_move_timeout_is_monotonic():
    assert move_timeout_s(100, 500) < move_timeout_s(1000, 500)
    assert move_timeout_s(1000, 500) > move_timeout_s(1000, 1000)


def test_move_timeout_with_zero_speed():
    """Нулевая/некорректная скорость не должна давать деление на ноль."""
    assert move_timeout_s(1000, 0) == 5.0


# ─── normalize_deg ───────────────────────────────────────────────────────────

def test_normalize_deg():
    assert normalize_deg(0.0) == 0.0
    assert normalize_deg(359.5) == 359.5
    assert normalize_deg(360.0) == 0.0
    assert normalize_deg(720.5) == 0.5
    assert normalize_deg(-0.5) == 359.5
    assert normalize_deg(-360.0) == 0.0
    assert normalize_deg(-721.0) == 359.0


def test_normalize_deg_always_in_range():
    for angle in (-1e-15, -1e-9, 1e-9, -360.0 - 1e-13, 32400.0, -32400.5):
        res = normalize_deg(angle)
        assert 0.0 <= res < 360.0, '{} -> {}'.format(angle, res)


# ─── shortest_delta_deg ──────────────────────────────────────────────────────

def test_shortest_delta_takes_short_way_over_zero():
    """Главный случай: возврат 359.5° -> 0° должен быть +0.5°, а не -359.5°."""
    assert shortest_delta_deg(359.5, 0.0) == 0.5
    assert shortest_delta_deg(0.0, 359.5) == -0.5
    assert shortest_delta_deg(350.0, 10.0) == 20.0
    assert shortest_delta_deg(10.0, 350.0) == -20.0


def test_shortest_delta_simple_cases():
    assert shortest_delta_deg(0.0, 0.0) == 0.0
    assert shortest_delta_deg(0.0, 90.0) == 90.0
    assert shortest_delta_deg(90.0, 0.0) == -90.0
    assert shortest_delta_deg(45.0, 45.0) == 0.0


def test_shortest_delta_half_turn_is_positive():
    """Ровно 180° неоднозначны — договариваемся крутить вперёд."""
    assert shortest_delta_deg(0.0, 180.0) == 180.0
    assert shortest_delta_deg(180.0, 0.0) == 180.0


def test_shortest_delta_range_and_target():
    for current in (0.0, 0.5, 90.0, 179.9, 180.0, 270.0, 359.9):
        for target in (0.0, 1.0, 45.5, 180.0, 359.5, -10.0, 720.25):
            delta = shortest_delta_deg(current, target)
            assert -180.0 < delta <= 180.0
            # смещение приводит именно в запрошенный угол
            assert abs(normalize_deg(current + delta) - normalize_deg(target)) < 1e-9 \
                or abs(normalize_deg(current + delta) - normalize_deg(target) - 360.0) < 1e-9


def test_shortest_delta_accepts_unnormalized_input():
    assert shortest_delta_deg(719.5, 360.0) == 0.5
    assert shortest_delta_deg(-0.5, 0.0) == 0.5
