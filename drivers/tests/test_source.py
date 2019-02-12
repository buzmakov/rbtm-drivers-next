from ..XRaySource.XRaySource import HWSource
from ..utils import get_source_config
from pprint import pprint


def test_xraysource():
    config = get_source_config()

    s = HWSource(config['port'])
    pprint(s.get_state())
    print(s.get_id())

    print('Is hight voltage on:', s.is_on_high_volatge())
    s.on_high_voltage()
    print('Is hight voltage on:', s.get_state(['is_on_high_voltage', 'qqq']))
    pprint(s.get_state())

    print('Set voltage to:', 20)
    s.set_voltage(20)
    assert s.get_actual_voltage() == 20

    pprint(s.get_state())
    s.set_current(10)
    assert s.get_actual_current() == 10
    pprint(s.get_state())

    s.off_high_voltage()
    assert not s.is_on_high_volatge()
    print('Is hight voltage on:', s.is_on_high_volatge())


# def test_on_hv():
#     config = get_source_config()
#     s = HWSource(config['port'])
#     s.off_high_voltage()
#     assert not s.get_state('is_on_high_voltage')['is_on_high_voltage']

#     s.on_high_voltage()
#     pprint(s.get_state())
#     assert s.get_state('is_on_high_voltage')['is_on_high_voltage']
