from ..Detector.Detector import HWDetector


def test_detetector():
    d = HWDetector()
    d.open()
    d.close()
