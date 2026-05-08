import threading
import logging

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
    def __init__(self, mock=None):
        """Инициализировать все устройства томографа.

        Args:
            mock: Если передано явно (True/False) — переопределяет значение
                из конфигурационного файла. Если None (по умолчанию) — режим
                mock читается из ``drivers/config/devices.cfg``,
                секция ``[x-ray source]``, ключ ``mock``.
        """
        shutter_config = get_shutter_config()
        self.shutter = XRayShutter.HWShutter(
            shutter_config["port"],
            shutter_config["relay_number"]
        )

        source_config = get_source_config()
        source_mock = source_config["mock"] if mock is None else mock
        self.source = XRaySource.HWSource(
            source_config["port"],
            mock=source_mock
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

        self._source_busy = False  # True пока on_high_voltage() выполняется в фоне

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

    def source_power_on_async(self):
        """Включить высокое напряжение в фоновом потоке (не блокирует RedisProxyServer).

        Сразу возвращает управление. Статус можно опросить через source_is_busy().
        """
        if self._source_busy:
            return  # уже включается — игнорируем повторный вызов

        def _do():
            self._source_busy = True
            try:
                self.source.on_high_voltage()
            except Exception as e:
                logging.getLogger(__name__).error('source_power_on_async error: %s', e)
            finally:
                self._source_busy = False

        threading.Thread(target=_do, daemon=True).start()

    def source_is_busy(self):
        """Вернуть True если включение источника ещё выполняется."""
        return self._source_busy

    def set_state(self, options):
        pass
