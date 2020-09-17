from ..Detector.Detector import HWDetector
import numpy as np
import time


def test_detetector():
    t = time.time()
    d = HWDetector()
    print(d.cam.get_debug_level())
    res = d.get_frames(1, 1)
    print(f"\n time = {time.time()-t}")
    print(f"noise={res.mean()}")
    np.save('det_test.npy', res)
    

