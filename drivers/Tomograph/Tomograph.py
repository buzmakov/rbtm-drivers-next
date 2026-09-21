import threading
import logging

from ..XRayShutter import XRayShutter
from ..XRaySource import XRaySource
from ..Motors.Motor import HWRotaryMotor, HWLinearMotor
from ..Detector import Detector
from ..utils import get_shutter_config, get_source_config, \
    get_horizontal_motor_config, get_angle_motor_config

from autologging import traced
from .. import tomo_logger

_log = logging.getLogger(__name__)


@traced(tomo_logger.logger)
class HWTomograph(object):
    """Агрегатор всех устройств томографа.

    Правила инициализации (важно для стабильности рентгеновского источника):

    * Источник берётся через :meth:`HWSource.get_shared` — один долгоживущий
      объект на процесс. Пересоздание ``HWTomograph`` через RedisProxy
      (при любой ошибке инициализации других устройств UI создаёт объект
      заново каждую минуту) больше НЕ открывает и не закрывает serial-порт
      ISOVOLT, т.е. не дёргает линии DTR/RTS генератора.
    * Если инициализация моторов/затвора падает, уже открытые устройства
      закрываются явно — иначе они утекали через ``atexit`` и следующая
      попытка получала ``Motor.open(): open failed`` на занятом контроллере.
    * Детектор инициализируется последним и не обязателен для создания
      объекта: при ошибке (например, камера XIMEA не найдена после
      загрузки) источник, моторы и затвор остаются управляемыми, а детектор
      пытается открыться заново при первом обращении к ``self.detector``.
    """

    def __init__(self, mock=None):
        """Инициализировать все устройства томографа.

        Args:
            mock: Если передано явно (True/False) — переопределяет значение
                из конфигурационного файла. Если None (по умолчанию) — режим
                mock читается из ``drivers/config/devices.cfg``,
                секция ``[x-ray source]``, ключ ``mock``.
        """
        self.shutter = None
        self.source = None
        self.horizontal_motor = None
        self.angle_motor = None
        self._detector = None
        self._detector_error = None
        self._detector_lock = threading.Lock()
        self._source_busy = False  # True пока on_high_voltage() выполняется в фоне

        try:
            shutter_config = get_shutter_config()
            self.shutter = XRayShutter.HWShutter(
                shutter_config["port"],
                shutter_config["relay_number"]
            )

            source_config = get_source_config()
            source_mock = source_config["mock"] if mock is None else mock
            self.source = XRaySource.HWSource.get_shared(
                source_config["port"],
                mock=source_mock
            )
            # Предустанавливаем кэш напряжения/тока, чтобы warmup()/on_high_voltage()
            # знали целевые значения, но НЕ обращаемся к устройству — при пересоздании
            # объекта через RedisProxy это вызывало циклическое вкл/выкл ВН.
            if self.source.last_voltage_nominal is None:
                self.source.last_voltage_nominal = 20.0
            if self.source.last_current_nominal is None:
                self.source.last_current_nominal = 10.0

            horizontal_motor_config = get_horizontal_motor_config()
            self.horizontal_motor = HWLinearMotor(
                horizontal_motor_config['port'],
                horizontal_motor_config['speed'],
                horizontal_motor_config['acceleration'],
                steps_per_mm=horizontal_motor_config['steps_per_mm'],
                move_outside_mm=horizontal_motor_config['move_outside_mm'],
            )

            angle_motor_config = get_angle_motor_config()
            self.angle_motor = HWRotaryMotor(
                angle_motor_config['port'],
                angle_motor_config['speed'],
                angle_motor_config['acceleration'],
                steps_on_deg=angle_motor_config['step_360'],
            )
        except Exception as e:
            _log.error('HWTomograph.__init__ failed: %s - releasing opened devices', e)
            self._release_devices()
            raise

        # Детектор — последним и без падения всего объекта.
        self._try_init_detector()

    # ------------------------------------------------------------------
    # Жизненный цикл устройств
    # ------------------------------------------------------------------

    def _release_devices(self):
        """Закрыть устройства, открытые в неудавшемся __init__.

        Источник НЕ закрываем: он общий на процесс (см. HWSource.get_shared),
        и его закрытие/переоткрытие как раз и дёргает интерфейс генератора.
        Затвор держит serial-порт открытым всё время жизни объекта, поэтому
        его освобождаем явно через release() (close() у него исторически
        закрывает заслонку, а не порт — см. HWShutter).
        """
        for name in ('horizontal_motor', 'angle_motor', '_detector'):
            device = getattr(self, name, None)
            if device is None:
                continue
            try:
                device.close()
            except Exception as e:
                _log.warning('HWTomograph: close(%s) failed: %s', name, e)
            setattr(self, name, None)

        if self.shutter is not None:
            try:
                self.shutter.release()
            except Exception as e:
                _log.warning('HWTomograph: release(shutter) failed: %s', e)
            self.shutter = None

    def _try_init_detector(self):
        """Попытаться открыть детектор; при ошибке запомнить её и не падать."""
        try:
            self._detector = Detector.HWDetector()
            self._detector_error = None
        except Exception as e:
            self._detector = None
            self._detector_error = e
            _log.error('HWTomograph: detector init failed: %s '
                       '(will retry on next access to .detector)', e)
        return self._detector

    @property
    def detector(self):
        """Детектор с ленивой повторной инициализацией.

        Raises:
            RuntimeError: если детектор не удалось открыть и в этот раз.
        """
        if self._detector is not None:
            return self._detector
        with self._detector_lock:
            if self._detector is None:
                self._try_init_detector()
        if self._detector is None:
            raise RuntimeError(
                'Detector is not available: {}'.format(self._detector_error))
        return self._detector

    @property
    def detector_available(self):
        """True, если детектор открыт (без попытки переоткрыть)."""
        return self._detector is not None

    @property
    def devices(self):
        return {'shutter': self.shutter,
                'source': self.source,
                'horizontal_motor': self.horizontal_motor,
                'angle_motor': self.angle_motor,
                'detector': self._detector,
                }

    # ------------------------------------------------------------------
    # Состояние
    # ------------------------------------------------------------------

    def get_state(self, devices=None):
        all_devices = self.devices
        if devices is None:
            devices = {k: None for k in all_devices}
        res = {}

        for device in devices:
            if device in all_devices:
                tomo_device = all_devices[device]
                if tomo_device is None:
                    res[device] = {'error': 'device is not available'}
                    continue
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
