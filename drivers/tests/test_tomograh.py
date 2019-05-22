from ..Tomograph.Tomograph import HWTomograph
import logging
from pprint import pprint

def test_tomograph():
    t = HWTomograph()
    state = t.get_state()
    pprint(state)
    logging.info(state)
