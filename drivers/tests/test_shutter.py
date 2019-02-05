from ..XRayShutter.XRayShutter import HWShutter
from ..utils import get_shutter_config
from time import sleep
from pprint import pprint


def test_sutter():
    config = get_shutter_config()
    pprint('Shutter config:')
    pprint(config)
    s = HWShutter(config['port'], config['relay_number'])
    pprint('Shutter state')
    pprint(s.get_state())
    pprint('Shutter state')
    pprint(s.get_state('is_open'))
    pprint('Shutter state')
    pprint(s.get_state(['is_open', 'is_closed']))
    s.open()
    assert s.is_open()['value']
    pprint('Shutter state')
    pprint(s.get_state())
    sleep(0.5)
    s.close()
    assert not s.is_open()['value']
    pprint('Shutter state')
    pprint(s.get_state())

    res = s.set_state({'is_open': True})
    pprint(res)
    res = s.set_state({'is_open': False, 'foo': 'bar'})
    pprint(res)
