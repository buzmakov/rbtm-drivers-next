from ..XRayShutter import XRayShutter
from ..XRaySource import XRaySource
from ..Motors import Motor
from ..Detector import Detector
from ..utils import get_shutter_config, get_source_config, \
    get_horizontal_motor_config, get_angle_motor_config

# import logging
# import sys
# from autologging import traced, TRACE

# logging.basicConfig(
#     level=TRACE, stream=sys.stdout,
#     format="%(levelname)s:%(filename)s,%(lineno)d:%(name)s.%(funcName)s:%(message)s")

from autologging import traced
from .. import tomo_logger

@traced(tomo_logger.logger)
class HWTomograph(object):
    def __init__(self, mock=True):

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
        # steps_on_deg=None: горизонтальный мотор линейный, deg-методы не применяются.
        # TODO: архитектурная проблема — линейный и вращательный моторы используют один класс HWMotor.
        #       Требуется рефакторинг на HWRotaryMotor / HWLinearMotor.
        self.horizontal_motor = Motor.HWMotor(horizontal_motor_config['port'],
                                              horizontal_motor_config['speed'],
                                              horizontal_motor_config['acceleration'],
                                              steps_on_deg=None)
        # Позиция парковки объекта — вынос из рентгеновского пучка (в шагах).
        self.horizontal_motor_move_object_outside = horizontal_motor_config['move_object_outside']

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
