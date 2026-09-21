"""Юнит-тесты check_and_prepare_exp_parameters (простой режим, ключи DARK/EMPTY/DATA).

Модуль ``experiment.experiment`` не требует живого Redis/железа для импорта —
``hwrpc``/``redis`` подключаются лениво, при первом реальном вызове. Пакеты
flask/redis/numpy/requests/scipy/matplotlib/autologging должны быть
установлены в окружении (см. tests/test_hwrpc.py и readme.md).

Запуск: ``python -m pytest tests/``.
"""
import copy

from experiment.experiment import check_and_prepare_exp_parameters


def _base_params():
    return {
        'exp_id': 'e1',
        'advanced': False,
        'DARK': {'count': 1, 'exposure': 1.0},
        'EMPTY': {'count': 1, 'exposure': 1.0},
        'DATA': {'step count': 1, 'exposure': 1.0, 'angle step': 1.0, 'count per step': 1},
    }


def test_valid_simple_params_pass():
    ok, msg = check_and_prepare_exp_parameters(_base_params())
    assert ok is True
    assert msg == ''


def test_dark_missing_both_keys_is_reported_not_keyerror():
    params = _base_params()
    params['DARK'] = {}
    # До исправления приоритета `not (a in d) and (b in d)` это падало с
    # KeyError на exp_param['DARK']['count'], а не возвращало (False, ...).
    ok, msg = check_and_prepare_exp_parameters(params)
    assert ok is False
    assert msg == "Incorrect format in 'DARK' parameters"


def test_dark_missing_exposure_only():
    params = _base_params()
    del params['DARK']['exposure']
    ok, msg = check_and_prepare_exp_parameters(params)
    assert ok is False
    assert msg == "Incorrect format in 'DARK' parameters"


def test_empty_missing_both_keys():
    params = _base_params()
    params['EMPTY'] = {}
    ok, msg = check_and_prepare_exp_parameters(params)
    assert ok is False
    assert msg == "Incorrect format in 'EMPTY' parameters"


def test_data_missing_step_count_and_exposure():
    params = _base_params()
    params['DATA'] = {'angle step': 1.0, 'count per step': 1}
    ok, msg = check_and_prepare_exp_parameters(params)
    assert ok is False
    assert msg == "Incorrect format in 'DATA' parameters"


def test_data_missing_angle_step_and_count_per_step():
    params = _base_params()
    params['DATA'] = {'step count': 1, 'exposure': 1.0}
    ok, msg = check_and_prepare_exp_parameters(params)
    assert ok is False
    assert msg == "Incorrect format in 'DATA' parameters"


def test_does_not_mutate_input():
    params = _base_params()
    snapshot = copy.deepcopy(params)
    check_and_prepare_exp_parameters(params)
    assert params == snapshot
