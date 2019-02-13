from ..Tomograph.Tomograph import Tomograph
import logging
from pprint import pprint

def test_tomograph():
    t = Tomograph()
    state = t.get_state()
    pprint(state)
    logging.info(state)
