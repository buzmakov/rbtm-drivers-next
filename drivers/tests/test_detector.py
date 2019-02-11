from ..Detector.Detector import HWDetector
import numpy as np

def test_detetector():
    d = HWDetector()
    res = d.get_frames(1, 3)
    print(res.mean())
    np.save('det_test.npy', res)
    

