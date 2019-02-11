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
            self.cam.set_gain(0.0)
            # self.cam.enable_recent_frame()
            self.cam.set_cooling("XI_TEMP_CTRL_MODE_AUTO")
            self.cam.set_target_temp(5.0)
            self.cam.set_imgdataformat("XI_MONO16")
            # logging.info(self.cam.get_cooling())
            # # logging.info(self.cam.get_gain())
            # # logging.info(self.cam.get_exposure_minimum())
            # logging.info(self.cam.get_target_temp())
            # logging.info(self.cam.get_temp_selector())
            logging.info(self.cam.get_acq_frame_burst_count())
            # TODO: add waiting for cooling

        except xiapi.Xi_error as err:
            logging.error("Detector.init() failed " + str(err))

    def close(self):
        try:
            self.cam.close_device()
        except xiapi.Xi_error as err:
            logging.error("Detector.close() failed " + str(err))

    def get_sensor_temp(self):
        return self.cam.get_chip_temp()

    def get_hous_temp(self):
        return self.cam.get_hous_temp()

    def get_get_exposure(self):
        return self.cam.get_exposure() / 1e6

    def get_frames(self, exposure, number_frames=None):
        data = None
        try:
            self.cam.set_exposure(exposure * 1e6)
            img = xiapi.Image()
            self.cam.start_acquisition()

            for frame_numb in range(number_frames):
                self.cam.get_image(img)
                if frame_numb == 0:
                    data = img.get_image_data_numpy()
                else:
                    data += img.get_image_data_numpy()  # TODO: check overflow

        except xiapi.Xi_error as err:
            logging.error("Detector.get_frame() failed " + str(err))

        return data
