from ..XRayShutter import XRayShutter
from ..XRaySource import XRaySource
from ..Motors import Motor
from ..Detector import Detector
from ..utils import get_shutter_config, get_source_config, \
    get_horizontal_motor_config, get_angle_motor_config

import logging
import sys
from autologging import traced, TRACE

logging.basicConfig(
    level=TRACE, stream=sys.stderr,
    format="%(levelname)s:%(filename)s,%(lineno)d:%(name)s.%(funcName)s:%(message)s")


@traced
class HWTomograph(object):
    def __init__(self, mock=False):

        shutter_config = get_shutter_config()
        self.shutter = XRayShutter.HWShutter(
            shutter_config["port"],
            shutter_config["relay_number"]
        )

        source_config = get_source_config()
        self.source = XRaySource.HWSource(
            source_config["port"],
            mock=mock
        )

        horizontal_motor_config = get_horizontal_motor_config()
        self.horizontal_motor = Motor.HWMotor(horizontal_motor_config['port'],
                                              horizontal_motor_config['speed'],
                                              horizontal_motor_config['acceleration'],
                                              horizontal_motor_config['step_360'])

        angle_motor_config = get_angle_motor_config()
        self.angle_motor = Motor.HWMotor(angle_motor_config['port'],
                                         angle_motor_config['speed'],
                                         angle_motor_config['acceleration'],
                                         angle_motor_config['step_360'])

        self.detector = Detector.HWDetector()

        self.devices = {'shutter': self.shutter,
                        'source': self.source,
                        'horizontal_motor': self.horizontal_motor,
                        'angle_motor': self.angle_motor,
                        'detector': self.detector
                        }

    def __del__(self):
        for d in self.devices:
            del d

    def get_state(self, devices=None):
        if devices is None:
            devices = {k: None for k in self.devices}
        res = {}

        for device in devices:
            if device in self.devices:
                tomo_device = self.devices[device]
                state = tomo_device.get_state(devices[device])
                res[device] = state

        return res

    def set_state(self, options):
        pass
