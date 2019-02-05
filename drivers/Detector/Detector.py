import logging
from .ximea import xiapi, xidefs
import atexit

class HWDetector(object):
    def __init__(self):
        # create instance for first connected camera
        try:
            self.cam = xiapi.Camera()
            self.cam.open_device()
        except xiapi.Xi_error as err:
            logging.error("Detector.init() failed " + str(err))

        atexit.register(self.close)

        try:
            self.cam.disable_aeag()
            self.cam.disable_auto_wb()
            self.cam.enable_recent_frame()
            self.cam.set_cooling(xidefs.XI_PRM_COOLING)

            print(self.cam.get_cooling())
            print(self.cam.get_gain())
            print(self.cam.get_exposure())

        except xiapi.Xi_error as err:
            logging.error("Detector.init() failed " + str(err))


    def close(self):
        try:
            self.cam.close_device()
        except xiapi.Xi_error as err:
            logging.error("Detector.close() failed " + str(err))
