from ..Detector.Detector import HWDetector


def test_detetector():
    d = HWDetector()
    res = d.get_frames(100, 3)
    print(res.mean())
