import datetime
import time
import json

from .experiment import ModExpError, Experiment, AdvancedExperiment, create_event, send_message_to_storage_webpage
from .constants import SUCCESSFUL_STOP_MSG
# from drivers.Tomograph.Tomograph import HWTomograph
from .redis_proxy import RedisProxy

from autologging import traced
from . import tomo_logger

class HWTomograph:
    pass

@traced(tomo_logger.logger)
class Tomograph:
    def __init__(self, redis_host='redis', redis_port=6379, redis_db=0):
        # Используем RedisProxy для инициализации HWTomograph.
        # Режим mock источника определяется из drivers/config/devices.cfg.
        HWTomographProxy = RedisProxy.create(HWTomograph,
                                     redis_host=redis_host,
                                     redis_port=redis_port,
                                     redis_db=redis_db,
                                     # 60 сек: покрывает полный оборот мотора (~65 с при speed=500)
                                     # + детектор с watchdog бросает ошибку раньше через hard timeout.
                                     # Было 600 сек × 3 попытки = 30 мин при USB-зависании.
                                     timeout=60,
                                     max_retries=1,
                                     )
        self.hwtomo = HWTomographProxy()
        self.current_experiment = None
        self.last_experiment_status = None  # финальный статус последнего эксперимента
        self.y_position = 0  # mock only property
        self.object_present = None  # mock only property

    # def __del__(self):
    #     del self.hwtomo

    def shutter_status(self):
        if self.hwtomo.shutter.is_open():
            return "OPEN"  # TODO: replace with enum?
        else:
            return "CLOSE"

    def tomo_state(self):
        if self.current_experiment is not None:
            return 'experiment', ""  # TODO: replace with enum?
        else:
            return 'ready', ""

    def source_power_on(self):
        """Включить высокое напряжение источника.

        Делегирует в HWTomograph.source_power_on_async() — поток запускается
        на стороне tomograph_server, Redis-прокси возвращается мгновенно
        и не блокирует обработку других запросов.
        """
        self.hwtomo.source_power_on_async()

    def source_power_off(self):
        """Выключить высокое напряжение источника."""
        self.hwtomo.source.off_high_voltage()

    def source_wait_for_ready(self, timeout=1800, poll_interval=5):
        """Ожидать готовности рентгеновского источника.

        Блокирует выполнение до тех пор, пока источник не выйдет из
        состояния прогрева (busy=False) и высокое напряжение не включится (on=True).

        Args:
            timeout: максимальное время ожидания в секундах (по умолчанию 30 мин).
            poll_interval: интервал опроса состояния в секундах.

        Raises:
            ModExpError: если источник не стал готов за отведённое время.
        """
        state = self.source_get_state()
        if state.get('mocked'):
            return

        start = time.time()
        while time.time() - start < timeout:
            state = self.source_get_state()
            if state.get('on') and not state.get('busy'):
                return
            time.sleep(poll_interval)

        raise ModExpError(
            error='X-ray source is warming up or failed to turn on',
            exception_message='Source did not become ready within {} seconds. '
                              'Please wait until warm-up completes and try again.'.format(timeout)
        )

    def source_get_state(self):
        """Вернуть текущее состояние рентгеновского источника.

        Returns:
            dict с ключами:
                on             (bool) — True если высокое напряжение включено,
                busy           (bool) — True пока идёт процесс включения (warmup),
                mocked         (bool) — True если источник работает в режиме заглушки
                                        (физически не подключён, mock=True в devices.cfg).
                                        В этом случае команды on/off игнорируются,
                                        а UI должен показывать «Не управляется».
                warming_status (dict) — статус прогрева из get_status()['warming status']:
                                        {
                                          'in_progress':         bool,
                                          'warming_interrupted': bool,
                                          'warming_from_pc':     bool,
                                          'warming_from_kb':     bool,
                                        }
                                        None если статус недоступен.
        """
        try:
            on = bool(self.hwtomo.source.is_on_high_voltage())
        except Exception as e:
            # Если источник не отвечает (например, в режиме прогрева),
            # считаем, что HV не включено
            on = False
            logging.getLogger(__name__).warning(
                "source_get_state: is_on_high_voltage failed: %s (assuming on=False)", e)
        try:
            busy = bool(self.hwtomo.source_is_busy())
        except Exception as e:
            # Если источник не отвечает, предполагаем, что он занят (прогревается)
            busy = True
            logging.getLogger(__name__).warning(
                "source_get_state: source_is_busy failed: %s (assuming busy=True)", e)

        # Читаем статус прогрева; используем snake_case для единообразия JSON
        warming_status = None
        try:
            ws = self.hwtomo.source.get_status()['warming status']
            warming_status = {
                'in_progress':         ws['in progress'],
                'warming_interrupted': ws['warming interrupted'],
                'warming_from_pc':     ws['warming from pc'],
                'warming_from_kb':     ws['warming from kb'],
            }
        except Exception as e:
            logging.getLogger(__name__).warning(
                "source_get_state: get_status failed: %s (warming_status=None)", e)

        # source.mock — флаг заглушки, установленный при инициализации HWSource
        mocked = bool(getattr(self.hwtomo.source, 'mock', False))
        return {'on': on, 'busy': busy, 'mocked': mocked, 'warming_status': warming_status}

    def source_set_voltage(self, new_voltage):
        if type(new_voltage) is not float:
            raise ModExpError(error='Incorrect format: type must be float')

        if new_voltage < 2 or 60 < new_voltage:
            raise ModExpError(error='Voltage must have value from 2 to 60!')

        self.hwtomo.source.set_voltage(new_voltage)

    def source_set_current(self, new_current):
        if type(new_current) is not float:
            raise ModExpError(error='Incorrect format: type must be float')

        if new_current < 2 or 80 < new_current:
            raise ModExpError(error='Current must have value from 2 to 80!')

        self.hwtomo.source.set_current(new_current)

    def source_get_voltage(self):
        return self.hwtomo.source.get_actual_voltage()

    def source_get_current(self):
        return self.hwtomo.source.get_actual_current()

    def open_shutter(self, time_=0):
        self.hwtomo.shutter.open()
        return self.shutter_status()

    def close_shutter(self, time_=0):
        self.hwtomo.shutter.close()
        return self.shutter_status()

    def shutter_state(self):
        return json.dumps({'state': self.shutter_status()})

    def set_x(self, new_x):
        """
        Переместить горизонтальный (линейный) мотор на абсолютную позицию в шагах.

        :param new_x: int | float — позиция в шагах, диапазон [-5000, 2000].
        :raises ModExpError: при неверном типе или выходе за границы диапазона.
        """
        if type(new_x) not in (int, float):
            raise ModExpError(error='Incorrect type! Position type must be int, but it is ' + str(type(new_x)))

        if new_x < -5000 or 2000 < new_x:
            raise ModExpError(error='Position must have value from -5000 to 2000')

        # blocking=False: не блокируем Redis-сервер во время движения,
        # чтобы поллинг get_x() со страницы adjustment работал в реальном времени
        self.hwtomo.horizontal_motor.move_to_position(new_x, blocking=False)

    def set_y(self, new_y):
        """
        Установить вертикальную позицию объекта (заглушка — вертикальный мотор отсутствует).
        Значение сохраняется только в памяти и используется в метаданных кадров.

        :param new_y: int | float — вертикальная позиция, диапазон [-5000, 2000].
        :raises ModExpError: при неверном типе или выходе за границы диапазона.
        """
        if type(new_y) not in (int, float):
            raise ModExpError(error='Incorrect type! Position type must be int, but it is ' + str(type(new_y)))

        if new_y < -5000 or 2000 < new_y:
            raise ModExpError(error='Position must have value from -5000 to 2000')

        self.y_position = new_y

    def set_angle(self, new_angle, blocking=False):
        """
        Повернуть угловой мотор на абсолютную позицию в градусах.
        Угол нормализуется в диапазон [0, 360).

        :param new_angle: int | float — угол в градусах.
        :param blocking: bool — если True, ждать завершения движения перед возвратом.
                         False (по умолчанию) — для ручного управления со страницы юстировки,
                         чтобы Redis-сервер оставался отзывчивым.
                         True — обязательно при съёмке кадров в эксперименте: кадр должен
                         сниматься только после достижения целевого угла.
        :raises ModExpError: при неверном типе аргумента.
        """
        if type(new_angle) not in (int, float):
            raise ModExpError(
                error='Incorrect type! Position type must be int or float, but it is ' + str(type(new_angle)))

        new_angle %= 360
        self.hwtomo.angle_motor.move_to_position_deg(new_angle, blocking=blocking)

    def get_x(self):
        """
        Получить текущую позицию горизонтального мотора в шагах.

        :return: float — абсолютная позиция в шагах.
        """
        return self.hwtomo.horizontal_motor.get_position()

    def get_y(self):
        """
        Получить текущую вертикальную позицию объекта.
        Заглушка: возвращает значение из памяти, вертикального мотора нет.

        :return: float — вертикальная позиция (установленная через set_y).
        """
        return self.y_position

    def get_angle(self):
        """
        Получить текущий угол поворота углового мотора в градусах.

        :return: float — угол в градусах.
        """
        return self.hwtomo.angle_motor.get_position_deg()

    def reset_to_zero_angle(self):
        """
        Принять текущую угловую позицию за нулевую (home position углового мотора).
        """
        self.hwtomo.angle_motor.set_zero()

    def move_away(self):
        """
        Переместить горизонтальный мотор в позицию парковки объекта
        (вывод образца из рентгеновского пучка).
        Целевая позиция хранится в HWLinearMotor.move_outside_mm и задаётся
        через конфиг при инициализации томографа.
        """
        self.hwtomo.horizontal_motor.move_outside()
        self.object_present = False

    def move_back(self):
        """
        Переместить горизонтальный мотор в рабочую позицию (позиция 0 — объект в пучке).
        """
        self.hwtomo.horizontal_motor.move_to_position(0)
        self.object_present = True

    def get_detector_chip_temperature(self):
        return self.hwtomo.detector.get_sensor_temp()

    def get_detector_hous_temperature(self):
        return self.hwtomo.detector.get_hous_temp()

    def get_detector_model(self):
        try:
            return self.hwtomo.detector.get_model()
        except Exception:
            return 'Ximea xiRAY'

    def get_detector_pixel_size(self):
        try:
            return self.hwtomo.detector.get_pixel_size()
        except Exception:
            return 4.25e-3

    def get_frame(self, exposure: float, with_open_shutter=None, send_to_webpage=False):
        """
        Сделать один кадр детектором.

        :param exposure: float — выдержка в миллисекундах.
        :param with_open_shutter: bool | None —
               True  — открыть заслонку перед съёмкой (светлый кадр),
               False — закрыть заслонку перед съёмкой (тёмный кадр),
               None  — не менять состояние заслонки.
        :param send_to_webpage: bool — зарезервирован, в текущей реализации не используется.
        :return: dict с ключами image_data, object, shutter, X-ray source и
                 дополнительным полем image_data['raw_image'] (numpy array).
        :raises ModExpError: при неверном типе параметра или ошибке декодирования метаданных.
        """
        if type(exposure) not in (int, float):
            raise ModExpError(error='Incorrect type! Exposure type must be int, but it is ' + str(type(exposure)))

        # if exposure < 0.1 or 16000 < exposure:
        #     raise ModExpError(error=('Exposure must have value from 0.1 to 16000 (given is %.1f )' % exposure))
        
        if with_open_shutter is not None:
            if with_open_shutter:
                self.open_shutter()
            else:
                self.close_shutter()

        raw_image = self.hwtomo.detector.get_frames(exposure / 1.e3)
        
        frame_metadata_json = self.get_detector_frame_metadata()

        try:
            frame_metadata = json.loads(frame_metadata_json)
        except TypeError as e:
            raise ModExpError(error='Could not convert frame\'s JSON into dict')

        frame_metadata['image_data']['raw_image'] = raw_image
        raw_image_with_metadata = frame_metadata
        return raw_image_with_metadata

    def get_detector_frame_metadata(self):
        current_datetime = datetime.datetime.now().strftime("%d.%m.%Y %H:%M:%S")
        timestamp = time.time()
        detector_data = {
            'model': self.get_detector_model(),
            'pixel_size': self.get_detector_pixel_size(),  # mm
        }
        exposure = self.hwtomo.detector.get_exposure() * 1e3
        chip_temp = self.hwtomo.detector.get_sensor_temp()
        hous_temp = self.hwtomo.detector.get_hous_temp()
        
        image_data = {'timestamp': timestamp,
                      'datetime': current_datetime,
                      'exposure': exposure,
                      'detector': detector_data,
                      'chip_temp': chip_temp,
                      'hous_temp': hous_temp
                      }         
        object_data = {'present': self.object_present,
                       'angle position': self.get_angle(),
                       'horizontal position': self.hwtomo.horizontal_motor.get_position(),
                       'vertical position': self.y_position
                       }
        shutter_state = json.loads(self.shutter_state())
        shutter_data = {'open': shutter_state['state'] == 'OPEN'}

        voltage = self.hwtomo.source.get_actual_voltage()
        current = self.hwtomo.source.get_actual_current()
        source_data = {'voltage': voltage,
                       'current': current}
        return json.dumps({'image_data': image_data,
                           'object': object_data,
                           'shutter': shutter_data,
                           'X-ray source': source_data})

    def carry_out_simple_experiment(self, exp_param):
        self.current_experiment = Experiment(_tomograph=self, exp_param=exp_param)
        exp_id = self.current_experiment.exp_id
        event_for_send = None
        try:
            self.current_experiment.run()
            event_for_send = create_event(event_type='message', exp_id=exp_id, MoF=SUCCESSFUL_STOP_MSG)
        except ModExpError as e:
            event_for_send = e.to_event_dict(exp_id)
        except Exception as e:
            import logging as _logging
            _logging.exception("carry_out_simple_experiment: unexpected error (exp_id=%s)", exp_id)
            err = ModExpError(error='Unexpected error: {}'.format(str(e)))
            event_for_send = err.to_event_dict(exp_id)
        finally:
            self.last_experiment_status = self.current_experiment.get_status()
            self.current_experiment = None
        if event_for_send:
            send_message_to_storage_webpage(event_for_send)

    def carry_out_advanced_experiment(self, exp_param):
        self.current_experiment = AdvancedExperiment(_tomograph=self, exp_param=exp_param)
        exp_id = self.current_experiment.exp_id
        event_for_send = None
        try:
            self.current_experiment.run()
            event_for_send = create_event(event_type='message', exp_id=exp_id, MoF=SUCCESSFUL_STOP_MSG)
        except ModExpError as e:
            event_for_send = e.to_event_dict(exp_id)
        except Exception as e:
            import logging as _logging
            _logging.exception("carry_out_advanced_experiment: unexpected error (exp_id=%s)", exp_id)
            err = ModExpError(error='Unexpected error: {}'.format(str(e)))
            event_for_send = err.to_event_dict(exp_id)
        finally:
            self.last_experiment_status = self.current_experiment.get_status()
            self.current_experiment = None
        if event_for_send:
            send_message_to_storage_webpage(event_for_send)
