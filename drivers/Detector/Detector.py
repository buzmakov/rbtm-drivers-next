import logging
from .ximea import xiapi


class HWDetector(object):
    def __init__(self):
        # create instance for first connected camera
        try:
            self.cam = xiapi.Camera()
        except xiapi.Xi_error as err:
            logging.error("Detector.init() failed " + str(err))

    def open(self):
        try:
            self.cam.open_device()
        except xiapi.Xi_error as err:
            logging.error("Detector.open() failed " + str(err))

    def close(self):
        try:
            self.cam.close_device()
        except xiapi.Xi_error as err:
            logging.error("Detector.close() failed " + str(err))
