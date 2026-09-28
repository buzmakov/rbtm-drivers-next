"""Юнит-тесты /experiment/status: окно старта, elapsed_sec для завершённого
эксперимента, ключ 'error'.

Роут изолируется подменой experiment.routes.tomograph стабом — без
реального железа/Redis. Стаб копирует форму нужных атрибутов
experiment.tomograph.Tomograph (current_experiment, _experiment_starting,
_starting_exp_id, last_experiment_status).
"""
import json

import pytest
from flask import Flask

from experiment import routes
from experiment.experiment import ModExpError


class _StubExp:
    """Заглушка запущенного BaseExperiment для веток exp is not None."""

    def __init__(self, exp_id='running-id', status=None, stop_exception=None):
        self.exp_id = exp_id
        self._status = status or {
            'exp_id': exp_id, 'frame_num': 3, 'total_frames': 10,
            'current_mode': 'data', 'current_angle': 12.0,
            'start_time': 1000.0, 'end_time': None, 'timeline': [{'mode': 'dark', 'count': 3}],
            'last_frame_at': 1005.0,
        }
        self.stop_exception = stop_exception

    def get_status(self):
        return dict(self._status)


class _StubTomograph:
    def __init__(self):
        self.current_experiment = None
        self._experiment_starting = False
        self._starting_exp_id = None
        self.last_experiment_status = None


@pytest.fixture
def app_client(monkeypatch):
    stub = _StubTomograph()
    monkeypatch.setattr(routes, 'tomograph', stub)
    app = Flask(__name__)
    app.register_blueprint(routes.bp_tomograph)
    app.testing = True
    with app.test_client() as c:
        c._stub = stub
        yield c


def _get_status(client):
    resp = client.get('/tomograph/0/experiment/status')
    assert resp.status_code == 200
    return json.loads(resp.get_data(as_text=True))['result']


def test_starting_window_reports_running_true_pending(app_client):
    """current_experiment ещё None, но поток уже запущен (_experiment_starting)."""
    app_client._stub._experiment_starting = True
    app_client._stub._starting_exp_id = 'new-exp-id'

    result = _get_status(app_client)
    assert result['running'] is True
    assert result['current_mode'] == 'pending'
    assert result['frame_num'] == 0
    assert result['exp_id'] == 'new-exp-id'
    assert result['timeline'] == []
    assert result['error'] is None


def test_running_experiment_elapsed_uses_live_clock(app_client, monkeypatch):
    app_client._stub.current_experiment = _StubExp()
    monkeypatch.setattr(routes.time, 'time', lambda: 1042.5)

    result = _get_status(app_client)
    assert result['running'] is True
    assert result['elapsed_sec'] == pytest.approx(42.5)
    assert result['error'] is None


def test_running_experiment_reports_stop_exception_as_error(app_client):
    se = ModExpError(error='short reason', exception_message='long detail')
    app_client._stub.current_experiment = _StubExp(stop_exception=se)

    result = _get_status(app_client)
    assert result['error'] == 'long detail'


def test_finished_experiment_elapsed_uses_end_time_not_now(app_client, monkeypatch):
    """До исправления elapsed_sec считался от time.time(), а не от end_time,
    и рос бы бесконечно после завершения эксперимента."""
    app_client._stub.last_experiment_status = {
        'exp_id': 'finished-id', 'frame_num': 10, 'total_frames': 10,
        'current_mode': 'data', 'current_angle': 90.0,
        'start_time': 1000.0, 'end_time': 1300.0, 'timeline': [],
        'last_frame_at': 1299.0, 'error': None,
    }
    # "Сейчас" сильно позже конца эксперимента — elapsed не должен от этого расти.
    monkeypatch.setattr(routes.time, 'time', lambda: 999999.0)

    result = _get_status(app_client)
    assert result['running'] is False
    assert result['elapsed_sec'] == pytest.approx(300.0)


def test_finished_experiment_reports_stored_error(app_client):
    app_client._stub.last_experiment_status = {
        'exp_id': 'finished-id', 'frame_num': 4, 'total_frames': 10,
        'current_mode': 'data', 'current_angle': 30.0,
        'start_time': 1000.0, 'end_time': 1050.0, 'timeline': [],
        'last_frame_at': 1049.0, 'error': 'detector timeout',
    }
    result = _get_status(app_client)
    assert result['error'] == 'detector timeout'


def test_finished_experiment_success_has_null_error(app_client):
    app_client._stub.last_experiment_status = {
        'exp_id': 'finished-id', 'frame_num': 10, 'total_frames': 10,
        'current_mode': 'data', 'current_angle': 30.0,
        'start_time': 1000.0, 'end_time': 1050.0, 'timeline': [],
        'last_frame_at': 1049.0, 'error': None,
    }
    result = _get_status(app_client)
    assert result['error'] is None


def test_no_experiment_ever_run(app_client):
    result = _get_status(app_client)
    assert result['running'] is False
    assert result['error'] is None
    assert result['exp_id'] == ''


def test_running_experiment_user_stop_is_not_error(app_client):
    """Кнопка «Закончить» в web (routes.experiment_stop) — не ошибка: web не должен показывать «Ошибка: unknown»."""
    from experiment.constants import SOMEONE_STOP_MSG
    se = ModExpError(error='unknown', stop_msg=SOMEONE_STOP_MSG)
    app_client._stub.current_experiment = _StubExp(stop_exception=se)

    result = _get_status(app_client)
    assert result['running'] is True
    assert result['error'] is None


def test_carry_out_experiment_user_stop_leaves_null_error(monkeypatch):
    """После ручной остановки last_experiment_status['error'] = None, причина всё равно уходит в storage."""
    from experiment import tomograph as tomograph_mod
    from experiment.constants import SOMEONE_STOP_MSG

    class _StoppedExp:
        def __init__(self, _tomograph, exp_param):
            self.exp_id = exp_param['exp_id']

        def run(self):
            raise ModExpError(error='unknown', stop_msg=SOMEONE_STOP_MSG)

        def get_status(self):
            return {'exp_id': self.exp_id, 'frame_num': 2, 'total_frames': 10}

    sent = []
    monkeypatch.setattr(tomograph_mod, 'Experiment', _StoppedExp)
    monkeypatch.setattr(tomograph_mod, 'send_message_to_storage_webpage', sent.append)

    tomo = tomograph_mod.Tomograph.__new__(tomograph_mod.Tomograph)
    tomo.current_experiment = None
    tomo._experiment_starting = True
    tomo._starting_exp_id = 'stopped-id'
    tomo.last_experiment_status = None

    tomo.carry_out_experiment({'exp_id': 'stopped-id', 'advanced': False})

    assert tomo.last_experiment_status['error'] is None
    assert tomo._experiment_starting is False
    assert sent and sent[0]['message'] == SOMEONE_STOP_MSG
