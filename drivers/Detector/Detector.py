import logging
import sys

#check os
try: 
    from .ximea import xiapi
except ImportError:
    sys.path.insert(0, r"C:\Users\topo-tomo\workspace\rbtm-drivers-next\vendor\ximea_win\API\Python\v3") #TODO: replace to ximea drivers path
    from ximea import xiapi

import atexit


class HWDetector(object):
    def __init__(self):
        # create instance for first connected camera
        try:
            self.cam = xiapi.Camera()
            self.cam.set_debug_level("XI_DL_DISABLED")
            self.cam.open_device()
        except xiapi.Xi_error as err:
            logging.error("Detector.init() failed " + str(err))
            raise RuntimeError("Detector.init() failed " + str(err))

        atexit.register(self.close)

        self.target_temperature = 15.0
        try:
            self.cam.disable_aeag()
            self.cam.disable_auto_wb()
            self.cam.set_gain(0.0)
            self.cam.set_cooling("XI_TEMP_CTRL_MODE_AUTO")
            self.cam.set_target_temp(self.target_temperature)
            self.cam.set_imgdataformat("XI_MONO16")
            # TODO: add waiting for cooling

        except xiapi.Xi_error as err:
            logging.error("Detector.init() failed " + str(err))
            raise RuntimeError("Detector.init() failed " + str(err))

    def close(self):
        try:
            self.cam.close_device()
        except xiapi.Xi_error as err:
            logging.error("Detector.close() failed " + str(err))
            raise RuntimeError("Detector.close() failed " + str(err))

    def set_gain(self, gain):
        self.cam.set_gain(gain)

    def get_gain(self):
        return self.cam.get_gain()

    def get_sensor_temp(self):
        return self.cam.get_chip_temp()

    def get_hous_temp(self):
        return self.cam.get_hous_temp()

    def get_exposure(self):
        return self.cam.get_exposure() / 1e6

    def get_frames(self, exposure, number_frames=1):
        """
        :param: exposure: exposition in seconds
        """
        data = None
        try:
            self.cam.set_exposure(int(round(exposure * 1e6)))
            img = xiapi.Image()
            self.cam.start_acquisition()

            for frame_numb in range(number_frames):
                self.cam.get_image(img, timeout=int(exposure * 1.5 * 1e6))
                if frame_numb == 0:
                    data = img.get_image_data_numpy()
                else:
                    data += img.get_image_data_numpy()  # TODO: check overflow
            self.cam.stop_acquisition()

        except xiapi.Xi_error as err:
            logging.error("Detector.get_frame() failed " + str(err))
            raise RuntimeError("Detector.get_frame() failed " + str(err))

        return data

    def get_state(self, options=None):
        if options is None:
            options = ['exposure', 'sensor_temp', 'hous_temp']
        res = {}
        if not isinstance(options, (list, tuple)):
            options = [options, ]

        for option in options:
            if option == 'exposure':
                s = self.get_exposure()
            elif option == 'sensor_temp':
                s = self.get_sensor_temp()
            elif option == 'hous_temp':
                s = self.get_hous_temp()
            else:
                s = {'error': 'Unsupported option'}
            res[option] = s
        return res
