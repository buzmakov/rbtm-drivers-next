"""Юнит-тест BaseExperiment.get_status(): должен отдавать глубокую копию.

До исправления get_status() делал dict(self.status_dict) — мелкую копию:
вложенный список 'timeline' оставался общим с оригиналом, и мутация
результата (или его же мутация потоком съёмки во время json.dumps в
/experiment/status) отражалась на внутреннем состоянии эксперимента и
наоборот.
"""
from experiment.experiment import BaseExperiment


def _make_experiment():
    return BaseExperiment(_tomograph=None, exp_param={'exp_id': 'e1'},
                          frames_total=5, first_exposure=1.0)


def test_get_status_returns_independent_timeline():
    exp = _make_experiment()
    exp._update_status(mode='dark', angle=0.0)

    snapshot = exp.get_status()
    snapshot['timeline'].append({'mode': 'injected', 'count': 999})
    snapshot['timeline'][0]['count'] = 999

    fresh = exp.get_status()
    assert fresh['timeline'] == [{'mode': 'dark', 'count': 1}]


def test_mutating_internal_timeline_after_snapshot_does_not_change_it():
    exp = _make_experiment()
    exp._update_status(mode='dark', angle=0.0)

    snapshot = exp.get_status()
    exp._update_status(mode='dark', angle=1.0)  # count += 1 внутри

    assert snapshot['timeline'] == [{'mode': 'dark', 'count': 1}]
