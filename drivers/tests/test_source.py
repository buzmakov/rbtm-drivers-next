from ..XRaySource.XRaySource import HWSource
from ..utils import get_source_config
import time
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

    pprint(s.get_state())
    s.set_current(10)
    pprint(s.get_state())

    time.sleep(2)
    s.off_high_voltage()
    print('Is hight voltage on:', s.is_on_high_volatge())

# print(s.get_error())
#
