import logging
import threading
import time
import json
import requests
from io import BytesIO
import numpy as np
from scipy.ndimage import median_filter
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from .constants import EMERGENCY_STOP_MSG, STORAGE_FRAMES_URI, STORAGE_EXP_FINISH_URI, FRAME_PNG_FILENAME
from . import tomograph

from autologging import traced
from . import tomo_logger


class ModExpError(Exception):
    def __init__(self, error, exception_message='', stop_msg=EMERGENCY_STOP_MSG):
        self.message = error
        self.error = error
        self.exception_message = exception_message
        self.stop_msg = stop_msg

    def __str__(self):
        return repr(self.message)

    def to_event_dict(self, exp_id):
        return create_event(event_type='message',
                            exp_id=exp_id,
                            MoF=self.stop_msg,
                            error=self.error,
                            exception_message=self.exception_message)

    def create_response(self):
        response_dict = {
            'success': False,
            'exception message': self.exception_message,
            'error': self.error,
            'result': None,
        }
        return json.dumps(response_dict)


def create_event(event_type, exp_id, MoF, exception_message='', error=''):
    if event_type == 'message':
        return {
            'type': event_type,
            'exp_id': exp_id,
            'message': MoF,
            'exception message': exception_message,
            'error': error,
        }

    elif event_type == 'frame':
        return {
            'type': event_type,
            'exp_id': exp_id,
            'frame': MoF,
        }

    return None


def safe_hardware_shutdown(tomograph):
    """Закрыть затвор и выключить ВН, не маскируя исходное исключение.

    Вызывается из ``finally`` в ``run()`` экспериментов. Каждый шаг
    выполняется независимо: если сервер оборудования упал и был
    перезапущен, RedisProxy авто-создаст новый ``HWTomograph`` и команда
    дойдёт до генератора; если и это не удалось — ошибка только логируется,
    чтобы наверх ушла первопричина (например, TimeoutError детектора).
    """
    for name, action in (('detector_stop_acquisition', tomograph.detector_stop_acquisition),
                         ('close_shutter', tomograph.close_shutter),
                         ('source_power_off', tomograph.source_power_off)):
        try:
            action()
            tomo_logger.info('safe_hardware_shutdown: {} done'.format(name))
        except Exception as e:
            tomo_logger.error('safe_hardware_shutdown: {} failed: {}'.format(name, e))


@traced(tomo_logger.logger)
class Experiment:
    def __init__(self, _tomograph, exp_param):
        self.tomograph: tomograph.Tomograph = _tomograph
        self.exp_id = exp_param['exp_id']

        self.DARK_count = exp_param['DARK']['count']
        self.DARK_exposure = exp_param['DARK']['exposure']

        self.EMPTY_count = exp_param['EMPTY']['count']
        self.EMPTY_exposure = exp_param['EMPTY']['exposure']

        self.DATA_step_count = exp_param['DATA']['step count']
        self.DATA_exposure = exp_param['DATA']['exposure']
        self.DATA_angle_step = exp_param['DATA']['angle step']
        self.DATA_count_per_step = exp_param['DATA']['count per step']

        frames_total_count = self.DARK_count + self.EMPTY_count + self.DATA_step_count * self.DATA_count_per_step
        self.total_digits_count = len(str(abs(frames_total_count - 1)))

        self.frame_num = 0
        self.to_be_stopped = False
        self.stop_exception = None
        self.worker_thread = None   # threading.Thread для отправки кадра в storage

        # --- Статус и последний кадр (thread-safe) ---
        self._status_lock = threading.Lock()
        self.last_frame = None  # numpy array последнего снятого кадра (для preview)
        self._start_time = None
        self.status_dict = {
            'exp_id': str(self.exp_id),
            'frame_num': 0,
            'total_frames': frames_total_count,
            'current_mode': 'pending',
            'current_angle': 0.0,
            'start_time': None,
            'timeline': [],
            # Unix timestamp последнего снятого кадра (time.time()).
            # Используется фронтендом для детекции зависания:
            # если now() - last_frame_at > порога → показываем предупреждение.
            # None до первого кадра.
            'last_frame_at': None,
        }

    def _update_status(self, mode=None, angle=None):
        """Обновить status_dict потокобезопасно."""
        with self._status_lock:
            # frame_num ещё не инкрементирован — показываем уже снятых = frame_num + 1
            self.status_dict['frame_num'] = self.frame_num + 1
            if mode is not None:
                self.status_dict['current_mode'] = mode
            if angle is not None:
                self.status_dict['current_angle'] = angle
            if self._start_time is None:
                self._start_time = time.time()
                self.status_dict['start_time'] = self._start_time
            # Фиксируем момент снятия кадра. Фронтенд сравнивает это значение
            # с текущим временем браузера; если разница превышает порог —
            # показывается предупреждение о возможном зависании.
            self.status_dict['last_frame_at'] = time.time()
            # Обновляем таймлайн: добавляем к последней группе или создаём новую
            tl = self.status_dict['timeline']
            if mode is not None:
                if tl and tl[-1]['mode'] == mode:
                    tl[-1]['count'] += 1
                else:
                    tl.append({'mode': mode, 'count': 1})

    def get_status(self):
        """Вернуть копию status_dict потокобезопасно."""
        with self._status_lock:
            return dict(self.status_dict)

    def get_and_send_frame(self, exposure, mode):
        numpy_image_with_metadata = self.tomograph.get_frame(exposure=exposure, with_open_shutter=None)
        numpy_image_with_metadata['mode'] = mode
        numpy_image_with_metadata['number'] = str(self.frame_num).zfill(self.total_digits_count)

        # Сохраняем последний кадр для preview (downsampled)
        try:
            raw = numpy_image_with_metadata['image_data']['raw_image']
            self.last_frame = raw[::4, ::4].copy()
        except Exception:
            pass

        # Обновляем статус
        angle = None
        try:
            angle = float(numpy_image_with_metadata.get('object', {}).get('angle position', 0.0) or 0.0)
        except (TypeError, ValueError):
            pass
        self._update_status(mode=mode, angle=angle)

        self.frame_num += 1

        # Ждём завершения отправки предыдущего кадра перед стартом следующей
        if self.worker_thread is not None:
            self.worker_thread.join()

        self.worker_thread = threading.Thread(
            target=prepare_send_frame,
            args=(numpy_image_with_metadata, self),
            daemon=False,
        )
        self.worker_thread.start()

    def run(self):
        self.to_be_stopped = False
        self.stop_exception = None
        try:
            self.tomograph.source_power_on()
            self.tomograph.source_wait_for_ready()
            self.tomograph.reset_to_zero_angle()
            # Один xiStartAcquisition на весь эксперимент (см. Tomograph.detector_start_acquisition)
            self.tomograph.detector_start_acquisition(self.DARK_exposure)
            self.collect_dark_frames()
            if not self.to_be_stopped:
                self.collect_empty_frames()
            if not self.to_be_stopped:
                self.collect_data_frames()
        finally:
            # Выполняется всегда — в том числе при падении tomograph_server
            # посреди съёмки (07.09.2026 источник остался под ВН с открытым
            # затвором, пока хост не выключили вручную).
            safe_hardware_shutdown(self.tomograph)
        # Если была запрошена остановка — сообщаем об этом
        if self.to_be_stopped and self.stop_exception is not None:
            raise self.stop_exception
        return

    def collect_data_frames(self):
        initial_angle = self.tomograph.get_angle()
        initial_angle = initial_angle if initial_angle is not None else 0
        data_angles = np.round((np.arange(0, self.DATA_step_count)) * self.DATA_angle_step + initial_angle, 2) % 360

        exp_angles = data_angles

        self.tomograph.move_back()
        self.tomograph.open_shutter(0)
        for iangle, current_angle in enumerate(exp_angles):
            if self.to_be_stopped:
                break
            # self.check_source()
            tomo_logger.info(f'Collecting frame {iangle}/{len(exp_angles)}')
            # blocking=True: мотор должен достичь целевого угла ДО съёмки кадра.
            # При blocking=False кадры снимались бы во время вращения — данные испорчены.
            self.tomograph.set_angle(float(current_angle), blocking=True)

            for j in range(0, self.DATA_count_per_step):
                self.get_and_send_frame(exposure=self.DATA_exposure, mode='data')

        self.tomograph.close_shutter(0)

    def collect_empty_frames(self):
        self.tomograph.move_away()
        self.tomograph.open_shutter(0)
        for i in range(0, self.EMPTY_count):
            if self.to_be_stopped:
                break
            # self.check_source()
            self.get_and_send_frame(self.EMPTY_exposure, mode='empty')
        self.tomograph.close_shutter(0)
        self.tomograph.move_back()

    def collect_dark_frames(self):
        self.tomograph.close_shutter(0)
        time.sleep(0.5)
        for _ in range(0, self.DARK_count):
            if self.to_be_stopped:
                break
            self.get_and_send_frame(exposure=self.DARK_exposure, mode='dark')

    def check_source(self):

        current = self.tomograph.source_get_current()
        voltage = self.tomograph.source_get_voltage()

        if (current is not None) and (voltage is not None):
            if current > 2 and voltage > 2:
                return

        print('X-ray source in wrong mode, try restart (off/on)')
        print('current = {0}, voltage = {1}'.format(current, voltage))

        self.tomograph.source_power_off()
        time.sleep(5)
        self.tomograph.source_power_on()
        time.sleep(5)


@traced(tomo_logger.logger)
class AdvancedExperiment:
    """
    Продвинутый режим эксперимента.

    Алгоритм:
      1. Начальная серия dark (series_length кадров, затвор закрыт)
      2. Начальная серия empty (series_length кадров, образец убран)
      3. Основной цикл по data_total угловым позициям:
         - set_angle(pos * data_angle_step)
         - data_count_per_step кадров mode='data'
         - каждые empty_period позиций (кроме последней):
             * серия empty (series_length кадров, образец убран)
             * data_count_per_step кадров mode='data_check' при том же угле
      4. close_shutter, source_power_off
    """

    def __init__(self, _tomograph, exp_param):
        self.tomograph: tomograph.Tomograph = _tomograph
        self.exp_id = exp_param['exp_id']

        self.exposure = exp_param['exposure']           # мс, единая для всех
        self.series_length = exp_param['series_length']  # кол-во dark/empty в серии
        self.data_total = exp_param['data_total']        # число угловых позиций
        self.data_angle_step = exp_param['data_angle_step']
        self.data_count_per_step = exp_param.get('data_count_per_step', 1)
        self.empty_period = exp_param['empty_period']    # вставлять empty каждые N позиций

        # Число периодических вставок (последняя позиция не триггерит вставку)
        num_empty_inserts = (self.data_total - 1) // self.empty_period
        frames_total = (
            self.series_length                                       # dark
            + self.series_length                                     # начальная empty
            + self.data_total * self.data_count_per_step             # data
            + num_empty_inserts * self.series_length                 # периодические empty
            + num_empty_inserts * self.data_count_per_step           # data_check
        )
        self.total_digits_count = len(str(max(frames_total - 1, 0)))

        self.frame_num = 0
        self.to_be_stopped = False
        self.stop_exception = None
        self.worker_thread = None   # threading.Thread для отправки кадра в storage

        # --- Статус и последний кадр (thread-safe) ---
        self._status_lock = threading.Lock()
        self.last_frame = None
        self._start_time = None
        self.status_dict = {
            'exp_id': str(self.exp_id),
            'frame_num': 0,
            'total_frames': frames_total,
            'current_mode': 'pending',
            'current_angle': 0.0,
            'start_time': None,
            'timeline': [],
            # Unix timestamp последнего снятого кадра (time.time()).
            # Используется фронтендом для детекции зависания:
            # если now() - last_frame_at > порога → показываем предупреждение.
            # None до первого кадра.
            'last_frame_at': None,
        }

    def _update_status(self, mode=None, angle=None):
        with self._status_lock:
            # frame_num ещё не инкрементирован — показываем уже снятых = frame_num + 1
            self.status_dict['frame_num'] = self.frame_num + 1
            if mode is not None:
                self.status_dict['current_mode'] = mode
            if angle is not None:
                self.status_dict['current_angle'] = angle
            if self._start_time is None:
                self._start_time = time.time()
                self.status_dict['start_time'] = self._start_time
            # Фиксируем момент снятия кадра. Фронтенд сравнивает это значение
            # с текущим временем браузера; если разница превышает порог —
            # показывается предупреждение о возможном зависании.
            self.status_dict['last_frame_at'] = time.time()
            tl = self.status_dict['timeline']
            if mode is not None:
                if tl and tl[-1]['mode'] == mode:
                    tl[-1]['count'] += 1
                else:
                    tl.append({'mode': mode, 'count': 1})

    def get_status(self):
        with self._status_lock:
            return dict(self.status_dict)

    def get_and_send_frame(self, exposure, mode):
        numpy_image_with_metadata = self.tomograph.get_frame(exposure=exposure, with_open_shutter=None)
        numpy_image_with_metadata['mode'] = mode
        numpy_image_with_metadata['number'] = str(self.frame_num).zfill(self.total_digits_count)

        # Сохраняем последний кадр для preview
        try:
            raw = numpy_image_with_metadata['image_data']['raw_image']
            self.last_frame = raw[::4, ::4].copy()
        except Exception:
            pass

        # Обновляем статус
        angle = None
        try:
            angle = float(numpy_image_with_metadata.get('object', {}).get('angle position', 0.0) or 0.0)
        except (TypeError, ValueError):
            pass
        self._update_status(mode=mode, angle=angle)

        self.frame_num += 1

        # Ждём завершения отправки предыдущего кадра перед стартом следующей
        if self.worker_thread is not None:
            self.worker_thread.join()

        self.worker_thread = threading.Thread(
            target=prepare_send_frame,
            args=(numpy_image_with_metadata, self),
            daemon=False,
        )
        self.worker_thread.start()

    def run(self):
        self.to_be_stopped = False
        self.stop_exception = None
        self._start_time = time.time()
        with self._status_lock:
            self.status_dict['start_time'] = self._start_time

        try:
            self.tomograph.source_power_on()
            self.tomograph.source_wait_for_ready()
            self.tomograph.reset_to_zero_angle()
            # Один xiStartAcquisition на весь эксперимент (см. Tomograph.detector_start_acquisition)
            self.tomograph.detector_start_acquisition(self.exposure)

            self._collect_dark_frames()
            if not self.to_be_stopped:
                self._collect_initial_empty_frames()
            if not self.to_be_stopped:
                self._collect_data_frames()
        finally:
            # Выполняется всегда — см. комментарий в Experiment.run()
            safe_hardware_shutdown(self.tomograph)

        # Если была запрошена остановка — сообщаем об этом
        if self.to_be_stopped and self.stop_exception is not None:
            raise self.stop_exception

    def _collect_dark_frames(self):
        self.tomograph.close_shutter(0)
        time.sleep(0.5)
        for _ in range(self.series_length):
            if self.to_be_stopped:
                break
            self.get_and_send_frame(exposure=self.exposure, mode='dark')

    def _collect_initial_empty_frames(self):
        self.tomograph.move_away()
        self.tomograph.open_shutter(0)
        for _ in range(self.series_length):
            if self.to_be_stopped:
                break
            self.get_and_send_frame(exposure=self.exposure, mode='empty')
        self.tomograph.close_shutter(0)
        self.tomograph.move_back()

    def _collect_periodic_empty_and_check(self):
        """Вставка empty-серии + data_check при том же угле."""
        self.tomograph.close_shutter(0)
        self.tomograph.move_away()
        self.tomograph.open_shutter(0)
        for _ in range(self.series_length):
            if self.to_be_stopped:
                break
            self.get_and_send_frame(exposure=self.exposure, mode='empty')
        self.tomograph.close_shutter(0)
        self.tomograph.move_back()
        if not self.to_be_stopped:
            # Контрольные кадры при том же угле (не меняем угол)
            self.tomograph.open_shutter(0)
            for _ in range(self.data_count_per_step):
                if self.to_be_stopped:
                    break
                self.get_and_send_frame(exposure=self.exposure, mode='data_check')

    def _collect_data_frames(self):
        self.tomograph.move_back()
        self.tomograph.open_shutter(0)

        for pos_index in range(self.data_total):
            if self.to_be_stopped:
                break

            current_angle = round(pos_index * self.data_angle_step, 4) % 360
            # blocking=True: мотор должен достичь целевого угла ДО съёмки кадра.
            self.tomograph.set_angle(float(current_angle), blocking=True)

            tomo_logger.info(f'Advanced: data position {pos_index}/{self.data_total}, angle={current_angle}')

            for _ in range(self.data_count_per_step):
                if self.to_be_stopped:
                    break
                self.get_and_send_frame(exposure=self.exposure, mode='data')

            if self.to_be_stopped:
                break

            # Вставка empty каждые empty_period позиций, но не после последней
            is_last = (pos_index == self.data_total - 1)
            if not is_last and (pos_index + 1) % self.empty_period == 0:
                tomo_logger.info(f'Advanced: periodic empty insert after position {pos_index}')
                self._collect_periodic_empty_and_check()
                if not self.to_be_stopped:
                    # Возвращаем образец и открываем затвор для продолжения data
                    self.tomograph.open_shutter(0)

        self.tomograph.close_shutter(0)


# Frame functions
# @traced
def prepare_send_frame(numpy_image_with_metadata, experiment):
    """Подготовить и отправить кадр в storage.
    Вызывается в отдельном потоке (threading.Thread) из get_and_send_frame().
    """
    image_numpy = numpy_image_with_metadata['image_data']['raw_image']
    del numpy_image_with_metadata['image_data']['raw_image']
    frame_metadata = numpy_image_with_metadata

    try:
        if experiment:
            frame_metadata_event = create_event(event_type='frame', exp_id=experiment.exp_id, MoF=frame_metadata)
            send_frame_to_storage_webpage(frame_metadata_event=frame_metadata_event,
                                          image_numpy=image_numpy)
        else:
            make_png(image_numpy)

    except ModExpError as e:
        if experiment is not None:
            experiment.stop_exception = e
            experiment.to_be_stopped = True
        return False, e

    return True, None


def send_frame_to_storage_webpage(frame_metadata_event, image_numpy):
    """Сжать кадр и синхронно отправить в storage.
    Блокирует поток (threading.Thread) до завершения — это нормально,
    так как get_and_send_frame() вызывает join() перед следующим кадром.
    Lock больше не нужен: один поток на кадр, следующий ждёт join().
    """
    s = BytesIO()
    np.savez_compressed(s, frame_data=image_numpy)
    logging.debug(image_numpy.shape)
    del image_numpy
    data = {'data': json.dumps(frame_metadata_event)}
    files = {'file': s.getvalue()}
    send_to_storage(STORAGE_FRAMES_URI, data, files=files)


def send_to_storage(storage_uri, data, files=None):
    """Отправить данные кадра в storage с повторными попытками.
    Вызывается синхронно из send_frame_to_storage_webpage() в потоке threading.Thread.
    Lock не нужен: изоляция обеспечивается join() в get_and_send_frame().
    """
    max_retries = 3
    retry_delay = 5  # seconds between attempts
    last_error = None
    for attempt in range(max_retries):
        try:
            storage_resp = requests.post(storage_uri, files=files, data=data, timeout=120)
        except Exception as e:
            last_error = ModExpError(
                error='Problems with storage',
                exception_message='Could not send to storage (attempt {}/{}): {}'.format(
                    attempt + 1, max_retries, str(e)))
            logging.warning('send_to_storage: attempt {}/{} failed: {}'.format(
                attempt + 1, max_retries, str(e)))
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
            continue

        try:
            storage_resp_dict = json.loads(storage_resp.content)
        except (ValueError, TypeError):
            last_error = ModExpError(
                error='Problems with storage',
                exception_message='Storage\'s response is not JSON (attempt {}/{})'.format(
                    attempt + 1, max_retries))
            logging.warning('send_to_storage: response not JSON on attempt {}/{}'.format(
                attempt + 1, max_retries))
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
            continue

        if 'result' not in storage_resp_dict:
            last_error = ModExpError(
                error='Problems with storage',
                exception_message="Storage's response has incorrect format (no 'result' key), attempt {}/{}".format(
                    attempt + 1, max_retries))
            logging.warning('send_to_storage: no "result" key on attempt {}/{}'.format(
                attempt + 1, max_retries))
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
            continue

        if storage_resp_dict['result'] != 'success':
            last_error = ModExpError(
                error='Problems with storage',
                exception_message='Storage\'s response: {} (attempt {}/{})'.format(
                    str(storage_resp_dict['result']), attempt + 1, max_retries))
            logging.warning('send_to_storage: non-success result on attempt {}/{}: {}'.format(
                attempt + 1, max_retries, storage_resp_dict['result']))
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
            continue

        logging.debug('send_to_storage: success on attempt {}/{}'.format(attempt + 1, max_retries))
        return

    # All retries exhausted
    raise last_error or ModExpError(
        error='Problems with storage',
        exception_message='All {} retries exhausted'.format(max_retries))


def make_preview_data(image_numpy, downsample=4):
    """
    Downsample image by integer factor, then apply 3×3 median filter on the
    small array (fast). Returns raw uint16 values — no normalisation.

    Args:
        image_numpy: 2-D uint16 ndarray from detector
        downsample:  integer stride (default 4 → image is 1/4 size each axis)

    Returns dict:
        data   : uint16 2-D ndarray
        width  : int
        height : int
    """
    try:
        k = max(1, int(downsample))

        # Fast integer stride downsampling (view, no copy)
        arr = image_numpy[::k, ::k]

        # Median filter on the small array — much faster than on full image
        arr = median_filter(arr, size=3).astype(np.uint16)

        return {
            'data': arr,
            'width': int(arr.shape[1]),
            'height': int(arr.shape[0]),
        }

    except Exception as e:
        logging.error("Could not make preview data from image: %s", e)
        raise ModExpError(error="Could not make preview data from image",
                          exception_message=str(e))


def make_png(image_numpy, png_filename=FRAME_PNG_FILENAME):
    try:
        small_res = np.fliplr(image_numpy)[::4, ::4]
        small_res = median_filter(small_res, 3)
        fig = plt.figure(figsize=(8, 4))
        img = plt.imshow(small_res)
        fig.colorbar(img)
        fig.tight_layout()
        plt.gray()
        plt.axis('off')
        plt.savefig(png_filename)

    except Exception as e:
        logging.error("Could not make png-file from image")
        raise ModExpError(error="Could not make png-file from image", exception_message=str(e))


def send_message_to_storage_webpage(event_dict):
    event_json_for_storage = json.dumps(event_dict)
    try:
        send_to_storage(STORAGE_EXP_FINISH_URI, data=event_json_for_storage)
    except ModExpError as e:
        logging.error("Could not message to storage")
        raise ModExpError(error="Could not message to storage", exception_message=e.message)


# Experiment
def check_and_prepare_exp_parameters(exp_param):
    if not (('exp_id' in exp_param.keys()) and ('advanced' in exp_param.keys())):
        return False, 'Incorrect format of keywords'
    if not ((type(exp_param['exp_id']) is str) and (type(exp_param['advanced']) is bool)):
        return False, 'Incorrect format: incorrect types'
    if exp_param['advanced']:
        # Валидация параметров продвинутого режима
        required_keys = ['exposure', 'series_length', 'data_total', 'data_angle_step', 'empty_period']
        for key in required_keys:
            if key not in exp_param:
                return False, f'Missing required parameter: {key}'

        if not isinstance(exp_param['exposure'], (int, float)):
            return False, "'exposure' must be a number"
        if exp_param['exposure'] < 0.1:
            return False, "'exposure' must be >= 0.1 ms"

        if not isinstance(exp_param['series_length'], int):
            return False, "'series_length' must be an integer"
        if exp_param['series_length'] < 1:
            return False, "'series_length' must be >= 1"

        if not isinstance(exp_param['data_total'], int):
            return False, "'data_total' must be an integer"
        if exp_param['data_total'] < 1:
            return False, "'data_total' must be >= 1"

        if not isinstance(exp_param['data_angle_step'], (int, float)):
            return False, "'data_angle_step' must be a number"

        if not isinstance(exp_param['empty_period'], int):
            return False, "'empty_period' must be an integer"
        if exp_param['empty_period'] < 1:
            return False, "'empty_period' must be >= 1"

        data_count_per_step = exp_param.get('data_count_per_step', 1)
        if not isinstance(data_count_per_step, int):
            return False, "'data_count_per_step' must be an integer"
        if data_count_per_step < 1:
            return False, "'data_count_per_step' must be >= 1"

    else:
        if not (('DARK' in exp_param.keys()) and ('EMPTY' in exp_param.keys()) and ('DATA' in exp_param.keys())):
            return False, 'Incorrect format3'
        if not ((type(exp_param['DARK']) is dict) and (type(exp_param['EMPTY']) is dict) and (
                type(exp_param['DATA']) is dict)):
            return False, 'Incorrect format4'

        if not ('count' in exp_param['DARK'].keys()) and ('exposure' in exp_param['DARK'].keys()):
            return False, 'Incorrect format in \'DARK\' parameters'
        if not ((type(exp_param['DARK']['count']) is int) and (type(exp_param['DARK']['exposure']) is float)):
            return False, 'Incorrect format in \'DARK\' parameters'

        if not ('count' in exp_param['EMPTY'].keys()) and ('exposure' in exp_param['EMPTY'].keys()):
            return False, 'Incorrect format in \'EMPTY\' parameters'
        if not ((type(exp_param['EMPTY']['count']) is int) and (type(exp_param['EMPTY']['exposure']) is float)):
            return False, 'Incorrect format in \'EMPTY\' parameters'

        if not ('step count' in exp_param['DATA'].keys()) and ('exposure' in exp_param['DATA'].keys()):
            return False, 'Incorrect format in \'DATA\' parameters'
        if not ((type(exp_param['DATA']['step count']) is int) and (type(exp_param['DATA']['exposure']) is float)):
            return False, 'Incorrect format in \'DATA\' parameters'

        if not ('angle step' in exp_param['DATA'].keys()) and ('count per step' in exp_param['DATA'].keys()):
            return False, 'Incorrect format in \'DATA\' parameters'
        if not (
                (type(exp_param['DATA']['angle step']) is float) and (
                type(exp_param['DATA']['count per step']) is int)):
            return False, 'Incorrect format in \'DATA\' parameters'

        # TO DELETE AFTER WEB-PAGE OF ADJUSTMENT START CHECK PARAMETERS
        if exp_param['DARK']['exposure'] < 0.1:
            return False, 'Bad parameters in \'DARK\' parameters'
        if exp_param['EMPTY']['exposure'] < 0.1:
            return False, 'Bad parameters in \'EMPTY\' parameters'
        if exp_param['DATA']['exposure'] < 0.1:
            return False, 'Bad parameters in \'DATA\' parameters'

    # we don't multiply and round  exp_param['DATA']['angle step'] here, we will do it during experiment,
    # because it will be more accurate this way
    return True, ''
