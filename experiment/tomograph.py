import logging
import time
import json

import redis

from .experiment import ModExpError, Experiment, AdvancedExperiment, create_event, send_message_to_storage_webpage
from .constants import SUCCESSFUL_STOP_MSG
from hwrpc import HardwareClient, HardwareError, HardwareUnavailable

from autologging import traced
from . import tomo_logger

# Таймауты RPC (с). Обычные запросы к железу — секунды; движение мотора —
# угловой идёт кратчайшим путём (≤ 180°, ≈ 33 с при speed=500), линейный
# до парковки ≈ 20 с; берём с запасом. Кадр — от экспозиции (см. get_frame).
RPC_TIMEOUT_S = 15
RPC_MOVE_TIMEOUT_S = 120
# Таймаут кадра = 2·экспозиция + RPC_FRAME_EXTRA_S; должен быть больше
# Detector.expected_frame_timeout_s (1.5·экспозиция + 15.5 с) — иначе клиент
# отвалится раньше, чем драйвер сообщит о зависании.
RPC_FRAME_EXTRA_S = 30
MAX_EXPOSURE_MS = 60000.0


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
        self.hw.call('shutter.open_shutter')
        return self.shutter_status()

    def close_shutter(self, time_=0):
        self.hw.call('shutter.close_shutter')
        return self.shutter_status()

    def shutter_state(self):
        return json.dumps({'state': self.shutter_status()})

    # ------------------------------------------------------------------
    # Постоянный режим захвата детектора
    # ------------------------------------------------------------------

    def detector_start_acquisition(self, exposure_ms):
        """Запустить постоянный захват на весь эксперимент (software trigger).

        Один xiStartAcquisition на эксперимент вместо старт/стоп на каждый кадр —
        обход гонки в libm3api (см. drivers/Detector/README.md). Драйвер сам
        поднимет захват лениво при первом кадре, но явный старт даёт понятную
        ошибку до начала съёмки.

        Raises:
            ModExpError: если камера не смогла начать захват.
        """
        try:
            self.hw.call('detector.start_acquisition', exposure_ms / 1.e3)
        except HardwareError as e:
            raise ModExpError(error='Detector could not start acquisition',
                              exception_message=e.message)

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
        """Модель камеры (кэшируется драйвером при инициализации)."""
        return self.hw.call('detector.get_model')

    def get_detector_pixel_size(self):
        """Размер пикселя, мм (по модели; при неизвестной модели драйвер пишет WARNING)."""
        return self.hw.call('detector.get_pixel_size')

    def get_frame(self, exposure, with_open_shutter=None):
        """Снять один кадр детектором.

        :param exposure: выдержка в миллисекундах.
        :param with_open_shutter: True — открыть заслонку перед съёмкой,
               False — закрыть, None — не трогать.
        :return: dict с ключами image_data (в т.ч. raw_image — numpy array),
                 object, shutter, 'X-ray source'.
        :raises ModExpError: при неверном типе параметра.
        """
        if type(exposure) not in (int, float):
            raise ModExpError(error='Incorrect type! Exposure type must be int, but it is ' + str(type(exposure)))
        if exposure < 0.1 or MAX_EXPOSURE_MS < exposure:
            raise ModExpError(error='Exposure must have value from 0.1 to {} ms (given {})'.format(
                MAX_EXPOSURE_MS, exposure))

        if with_open_shutter is not None:
            if with_open_shutter:
                self.open_shutter()
            else:
                self.close_shutter()

        exposure_s = exposure / 1.e3
        # Один серверный вызов: кадр + все метаданные (см. HWTomograph.capture_frame).
        raw_image, frame = self.hw.call('capture_frame', exposure_s,
                                        timeout=exposure_s * 2 + RPC_FRAME_EXTRA_S)
        # Состояние, которое знает только Flask-сторона
        frame['object']['present'] = self.object_present
        frame['object']['vertical position'] = self.y_position
        frame['image_data']['raw_image'] = raw_image
        return frame

    def carry_out_experiment(self, exp_param):
        """Провести эксперимент (в отдельном потоке) и сообщить storage о завершении."""
        cls = AdvancedExperiment if exp_param.get('advanced') else Experiment
        self.current_experiment = cls(_tomograph=self, exp_param=exp_param)
        self._experiment_starting = False
        exp_id = self.current_experiment.exp_id
        try:
            self.current_experiment.run()
            event_for_send = create_event(event_type='message', exp_id=exp_id, MoF=SUCCESSFUL_STOP_MSG)
        except ModExpError as e:
            event_for_send = e.to_event_dict(exp_id)
        except Exception as e:
            logging.exception("carry_out_experiment: unexpected error (exp_id=%s)", exp_id)
            event_for_send = ModExpError(error='Unexpected error: {}'.format(e)).to_event_dict(exp_id)
        finally:
            self.last_experiment_status = self.current_experiment.get_status()
            self.current_experiment = None
        try:
            send_message_to_storage_webpage(event_for_send)
        except ModExpError as e:
            logging.error("carry_out_experiment: could not report finish to storage: %s", e.exception_message)
