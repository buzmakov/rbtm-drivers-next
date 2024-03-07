#pytest --log-cli-level=INFO -s -v test_detector.py
from ..Detector.Detector import HWDetector
import numpy as np
import time
import logging
from PIL import Image


def test_detetector():
    t = time.time()
    d = HWDetector()
    logging.info(d.cam.get_device_name())
    logging.info(d.cam.get_device_inst_path())
    logging.info(d.cam.get_hous_temp())

    # logging.info(d.cam.get_debug_level())
    # res = d.get_frames(1, 1)
    # logging.info(f"\n time = {time.time()-t}")
    # logging.info(f"noise={res.mean()}")
    # im = Image.fromarray(res)
    # im.save('test.tif')
    # np.save('det_test.npy', res)