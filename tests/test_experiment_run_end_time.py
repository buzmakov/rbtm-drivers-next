"""Юнит-тест BaseExperiment.run(): по завершении должен фиксироваться
status_dict['end_time'].

/experiment/status использует end_time - start_time для elapsed_sec
завершённого эксперимента вместо time.time() - start_time, который рос
бы бесконечно и после конца съёмки.
"""
from experiment.experiment import BaseExperiment, ModExpError


class _StubHW:
    """Минимальный тomograph-стаб для BaseExperiment.run()."""

    def __init__(self, fail_acquire=False):
        self.fail_acquire = fail_acquire
        self.calls = []

    def source_power_on(self):
        self.calls.append('source_power_on')

    def source_wait_for_ready(self):
        self.calls.append('source_wait_for_ready')

    def reset_to_zero_angle(self):
        self.calls.append('reset_to_zero_angle')

    def detector_start_acquisition(self, exposure):
        self.calls.append('detector_start_acquisition')

    def detector_stop_acquisition(self):
        self.calls.append('detector_stop_acquisition')

    def close_shutter(self):
        self.calls.append('close_shutter')

    def source_power_off(self):
        self.calls.append('source_power_off')


class _OkExperiment(BaseExperiment):
    def _acquire(self):
        pass


class _FailingExperiment(BaseExperiment):
    def _acquire(self):
        raise ModExpError(error='boom', exception_message='detail')


def test_end_time_set_after_successful_run():
    exp = _OkExperiment(_tomograph=_StubHW(), exp_param={'exp_id': 'e1'},
                        frames_total=0, first_exposure=1.0)
    status_before = exp.get_status()
    assert status_before['end_time'] is None

    exp.run()

    status_after = exp.get_status()
    assert status_after['end_time'] is not None
    assert status_after['end_time'] >= status_after['start_time']


def test_end_time_set_even_when_acquire_raises():
    exp = _FailingExperiment(_tomograph=_StubHW(), exp_param={'exp_id': 'e1'},
                             frames_total=0, first_exposure=1.0)
    try:
        exp.run()
    except ModExpError:
        pass
    else:
        raise AssertionError('ожидалось исключение из _acquire()')

    status = exp.get_status()
    assert status['end_time'] is not None
