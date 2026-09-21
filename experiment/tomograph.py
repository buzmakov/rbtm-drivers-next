import datetime
import logging
import time
import json

import redis

from .experiment import ModExpError, Experiment, AdvancedExperiment, create_event, send_message_to_storage_webpage
from .constants import SUCCESSFUL_STOP_MSG
from hwrpc import HardwareClient, HardwareUnavailable

from autologging import traced
from . import tomo_logger

# Таймауты RPC (с). Обычные запросы к железу — секунды; движение мотора —
# до полного оборота (32400 шагов / 500 шаг/с ≈ 65 с) с запасом; кадр —
# от экспозиции (см. get_frame).
RPC_TIMEOUT_S = 15
RPC_MOVE_TIMEOUT_S = 120
RPC_FRAME_EXTRA_S = 30


@traced(tomo_logger.logger)
class Tomograph:
    """Клиентская сторона томографа: валидация параметров и вызовы HWTomograph через hwrpc.

    Ничего не создаёт на стороне железа: объект HWTomograph живёт в
    tomograph_server и переживает рестарт этого процесса; если упал сам
    сервер железа, вызовы бросают HardwareUnavailable, а Flask продолжает работать.
    """

    def __init__(self, redis_host='redis', redis_port=6379, redis_db=0):
        self.hw = HardwareClient(redis.Redis(host=redis_host, port=redis_port, db=redis_db),
                                 default_timeout_s=RPC_TIMEOUT_S)
        self.current_experiment = None
        self._experiment_starting = False  # поток запущен, current_experiment ещё не присвоен
        self.last_experiment_status = None  # финальный статус последнего эксперимента
        self.y_position = 0  # mock only property
        self.object_present = None  # mock only property

    def shutter_status(self):
        if self.hw.call('shutter.is_open'):
            return "OPEN"  # TODO: replace with enum?
        else:
            return "CLOSE"

    def tomo_state(self):
        """('experiment' | 'ready' | 'unavailable', сообщение)."""
        if self.current_experiment is not None or self._experiment_starting:
            return 'experiment', ""
        try:
            status = self.hw.status()
        except HardwareUnavailable as e:
            return 'unavailable', str(e)
        if not status.get('available'):
            return 'unavailable', 'hardware init failed: {}'.format(status.get('error'))
        return 'ready', ""

    def mark_experiment_starting(self):
        """Вызывается под локом старта до запуска потока эксперимента."""
        self._experiment_starting = True

    def source_power_on(self):
        """Включить высокое напряжение источника.

        Делегирует в HWTomograph.source_power_on_async() — поток запускается
        на стороне tomograph_server, Redis-прокси возвращается мгновенно
        и не блокирует обработку других запросов.
        """
        self.hw.call('source_power_on_async')

    def source_power_off(self):
        """Выключить высокое напряжение источника."""
        self.hw.call('source.off_high_voltage')

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
            on = bool(self.hw.call('source.is_on_high_voltage'))
        except Exception as e:
            # Если источник не отвечает (например, в режиме прогрева),
            # считаем, что HV не включено
            on = False
            logging.getLogger(__name__).warning(
                "source_get_state: is_on_high_voltage failed: %s (assuming on=False)", e)
        try:
            busy = bool(self.hw.call('source_is_busy'))
        except Exception as e:
            # Если источник не отвечает, предполагаем, что он занят (прогревается)
            busy = True
            logging.getLogger(__name__).warning(
                "source_get_state: source_is_busy failed: %s (assuming busy=True)", e)

        # Читаем статус прогрева; используем snake_case для единообразия JSON
        warming_status = None
        try:
            ws = self.hw.call('source.get_status')['warming status']
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
        try:
            mocked = bool(self.hw.call('source.mock'))
        except Exception:
            mocked = False
        return {'on': on, 'busy': busy, 'mocked': mocked, 'warming_status': warming_status}

    def source_set_voltage(self, new_voltage):
        if type(new_voltage) is not float:
            raise ModExpError(error='Incorrect format: type must be float')

        if new_voltage < 2 or 60 < new_voltage:
            raise ModExpError(error='Voltage must have value from 2 to 60!')

        self.hw.call('source.set_voltage', new_voltage)

    def source_set_current(self, new_current):
        if type(new_current) is not float:
            raise ModExpError(error='Incorrect format: type must be float')

        if new_current < 2 or 80 < new_current:
            raise ModExpError(error='Current must have value from 2 to 80!')

        self.hw.call('source.set_current', new_current)

    def source_get_voltage(self):
        return self.hw.call('source.get_actual_voltage')

    def source_get_current(self):
        return self.hw.call('source.get_actual_current')

    def open_shutter(self, time_=0):
        self.hw.call('shutter.open')
        return self.shutter_status()

    def close_shutter(self, time_=0):
        self.hw.call('shutter.close')
        return self.shutter_status()

    def shutter_state(self):
        return json.dumps({'state': self.shutter_status()})

    # ------------------------------------------------------------------
    # Постоянный режим захвата детектора
    # ------------------------------------------------------------------

    def detector_start_acquisition(self, exposure_ms):
        """Запустить постоянный захват на весь эксперимент (software trigger).

        Без этого каждый кадр делает xiStartAcquisition + xiStopAcquisition.
        В libm3api V4.27.21 xiStopAcquisition помечает объект таймаута в
        контексте камеры значением -1, а рабочий поток mm_WorkerThread
        читает его без проверки — гонка, которая роняет tomograph_server
        (segfault at 0x77 в libm3api.so.2, 37 раз с 01.2025). Один старт и
        одна остановка на эксперимент вместо сотен сводят окно гонки к минимуму.

        Возвращает True, если режим включён; при ошибке камеры пишет
        предупреждение и возвращает False — детектор остаётся в legacy-режиме.
        """
        try:
            self.hw.call('detector.start_acquisition', exposure_ms / 1.e3, True)
            return True
        except Exception as e:
            logging.getLogger(__name__).warning(
                'detector_start_acquisition failed: %s (staying in legacy per-frame mode)', e)
            return False

    def detector_stop_acquisition(self):
        """Остановить постоянный захват (безопасно, если он не был запущен)."""
        self.hw.call('detector.stop_acquisition')

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
        self.hw.call('horizontal_motor.move_to_position', new_x, blocking=False)

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
        self.hw.call('angle_motor.move_to_position_deg', new_angle, blocking=blocking,
                     timeout=RPC_MOVE_TIMEOUT_S if blocking else RPC_TIMEOUT_S)

    def get_x(self):
        """
        Получить текущую позицию горизонтального мотора в шагах.

        :return: float — абсолютная позиция в шагах.
        """
        return self.hw.call('horizontal_motor.get_position')

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
        return self.hw.call('angle_motor.get_position_deg')

    def reset_to_zero_angle(self):
        """
        Принять текущую угловую позицию за нулевую (home position углового мотора).
        """
        self.hw.call('angle_motor.set_zero')

    def move_away(self):
        """
        Переместить горизонтальный мотор в позицию парковки объекта
        (вывод образца из рентгеновского пучка).
        Целевая позиция хранится в HWLinearMotor.move_outside_mm и задаётся
        через конфиг при инициализации томографа.
        """
        self.hw.call('horizontal_motor.move_outside', timeout=RPC_MOVE_TIMEOUT_S)
        self.object_present = False

    def move_back(self):
        """
        Переместить горизонтальный мотор в рабочую позицию (позиция 0 — объект в пучке).
        """
        self.hw.call('horizontal_motor.move_to_position', 0, timeout=RPC_MOVE_TIMEOUT_S)
        self.object_present = True

    def get_detector_chip_temperature(self):
        return self.hw.call('detector.get_sensor_temp')

    def get_detector_hous_temperature(self):
        return self.hw.call('detector.get_hous_temp')

    def get_detector_model(self):
        try:
            return self.hw.call('detector.get_model')
        except Exception:
            return 'Ximea xiRAY'

    def get_detector_pixel_size(self):
        try:
            return self.hw.call('detector.get_pixel_size')
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

        raw_image = self.hw.call('detector.get_frames', exposure / 1.e3,
                                 timeout=exposure / 1.e3 * 2 + RPC_FRAME_EXTRA_S)
        
        frame_metadata_json = self.get_detector_frame_metadata()

        try:
            frame_metadata = json.loads(frame_metadata_json)
        except TypeError:
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
        exposure = self.hw.call('detector.get_exposure') * 1e3
        chip_temp = self.hw.call('detector.get_sensor_temp')
        hous_temp = self.hw.call('detector.get_hous_temp')
        
        image_data = {'timestamp': timestamp,
                      'datetime': current_datetime,
                      'exposure': exposure,
                      'detector': detector_data,
                      'chip_temp': chip_temp,
                      'hous_temp': hous_temp
                      }         
        object_data = {'present': self.object_present,
                       'angle position': self.get_angle(),
                       'horizontal position': self.hw.call('horizontal_motor.get_position'),
                       'vertical position': self.y_position
                       }
        shutter_state = json.loads(self.shutter_state())
        shutter_data = {'open': shutter_state['state'] == 'OPEN'}

        voltage = self.hw.call('source.get_actual_voltage')
        current = self.hw.call('source.get_actual_current')
        source_data = {'voltage': voltage,
                       'current': current}
        return json.dumps({'image_data': image_data,
                           'object': object_data,
                           'shutter': shutter_data,
                           'X-ray source': source_data})

    def carry_out_simple_experiment(self, exp_param):
        self.current_experiment = Experiment(_tomograph=self, exp_param=exp_param)
        self._experiment_starting = False
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
        self._experiment_starting = False
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
