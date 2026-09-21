"""Юнит-тест /experiment/start: exp_id не должен просачиваться в
data['experiment parameters'], которая целиком уходит в storage/Mongo.

До исправления exp_param = data['experiment parameters'] был тем же
объектом, что и вложенный словарь в data; добавление exp_param['exp_id']
мутировало его и лишний exp_id оказывался внутри 'experiment parameters'
в JSON, отправляемом в storage.

Юниты роута изолируются подменой experiment.routes.tomograph (стаб без
реального железа/Redis) и experiment.routes.send_to_storage — не требует
запущенного tomograph_server/Redis/Mongo.
"""
import json
import time

import pytest
from flask import Flask

from experiment import routes


class _StubTomograph:
    def __init__(self):
        self.current_experiment = None
        self.started_exp_params = []

    def tomo_state(self):
        return 'ready', ''

    def get_detector_model(self):
        return 'mock-model'

    def get_detector_pixel_size(self):
        return 0.1

    def mark_experiment_starting(self, *a, **kw):
        pass

    def carry_out_experiment(self, exp_param):
        # Синхронно, вместо реального потока — нам нужен только сам exp_param.
        self.started_exp_params.append(exp_param)


@pytest.fixture
def client(monkeypatch):
    stub = _StubTomograph()
    monkeypatch.setattr(routes, 'tomograph', stub)

    captured_storage_calls = []

    def fake_send_to_storage(storage_uri, data, files=None):
        captured_storage_calls.append(data)

    monkeypatch.setattr(routes, 'send_to_storage', fake_send_to_storage)

    # Поток эксперимента реальный, но carry_out_experiment у стаба не блокирует
    # и не трогает железо — можно оставить threading.Thread как есть, он
    # завершится мгновенно.
    app = Flask(__name__)
    app.register_blueprint(routes.bp_tomograph)
    app.testing = True
    with app.test_client() as c:
        c._stub = stub
        c._storage_calls = captured_storage_calls
        yield c


def _valid_body():
    return {
        'exp_id': 'exp-123',
        'experiment parameters': {
            'exp_id': 'this-should-not-matter',  # клиент теоретически мог прислать
            'advanced': False,
            'DARK': {'count': 1, 'exposure': 1.0},
            'EMPTY': {'count': 1, 'exposure': 1.0},
            'DATA': {'step count': 1, 'exposure': 1.0, 'angle step': 1.0, 'count per step': 1},
        },
    }


def test_exp_id_not_leaked_into_stored_experiment_parameters(client):
    body = _valid_body()
    resp = client.post('/tomograph/0/experiment/start', data=json.dumps(body),
                       content_type='application/json')
    assert resp.status_code == 200
    result = json.loads(resp.get_data(as_text=True))
    assert result['success'] is True

    assert len(client._storage_calls) == 1
    sent = client._storage_calls[0]
    # sent — это enriched_data, JSON-байты (см. experiment_start: json.dumps(data).encode())
    sent_dict = json.loads(sent) if isinstance(sent, (bytes, str)) else sent
    assert sent_dict['exp_id'] == 'exp-123'
    # Главное: вложенный 'experiment parameters' не должен обзавестись
    # верхнеуровневым exp_id из-за мутации того же объекта, что ушёл в поток.
    assert sent_dict['experiment parameters']['exp_id'] == 'this-should-not-matter'

    # carry_out_experiment запускается в отдельном потоке (threading.Thread);
    # дожидаемся, пока стаб зафиксирует exp_param (без сна/железа — быстро).
    deadline = time.monotonic() + 2.0
    while not client._stub.started_exp_params and time.monotonic() < deadline:
        time.sleep(0.01)

    assert len(client._stub.started_exp_params) == 1
    assert client._stub.started_exp_params[0]['exp_id'] == 'exp-123'
