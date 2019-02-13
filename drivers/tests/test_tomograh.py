from ..Tomograph.Tomograph import Tomograph
import logging


def test_tomograph():
    t = Tomograph()
    logging.info(t.get_state())
