"""tools/verify_robotom.py: проверка K стартует эксперимент с полями верхнего уровня как у rbtm-web.

Без timestamp/datetime/specimen документ в rbtm-storage ломал список объектов
rbtm-recon (KeyError 'timestamp'). Железо и сеть не нужны: api и remote — заглушки,
старт отвечает success=False, и проверка K завершается исключением Check сразу после POST.
"""
import importlib.util
import pathlib

import pytest

_PATH = pathlib.Path(__file__).resolve().parent.parent / 'tools' / 'verify_robotom.py'
_spec = importlib.util.spec_from_file_location('verify_robotom', _PATH)
verify_robotom = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(verify_robotom)


class _Resp:
    def json(self):
        return {'success': False, 'error': 'stub'}


class _Api:
    def __init__(self):
        self.posted = []

    def post(self, path, body, timeout=30):
        self.posted.append((path, body))
        return _Resp()


class _Remote:
    def segfaults(self):
        return 0

    def restart_count(self):
        return 0

    def server_log_grep(self, pattern):
        return 0


def test_check_k_start_body_matches_web_format():
    api = _Api()
    with pytest.raises(verify_robotom.Check):
        verify_robotom.check_k_short_experiment(api, _Remote())

    (path, body), = api.posted
    assert path == '/experiment/start'
    assert body['exp_id'].startswith('smoke-')
    assert isinstance(body['timestamp'], float)
    assert body['datetime'] and body['specimen'] and 'tags' in body
    assert body['experiment parameters'] == verify_robotom.EXPERIMENT
    assert 'exp_id' not in body['experiment parameters']
