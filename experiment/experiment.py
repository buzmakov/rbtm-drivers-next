import logging
import multiprocessing as mp
import time
import json
import requests
from io import BytesIO
import numpy as np
from scipy.ndimage import median_filter
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
        self.worker_process = None
        self.network_lock = mp.Lock()
        
    def get_and_send_frame(self, exposure, mode):
        numpy_image_with_metadata = self.tomograph.get_frame(exposure=exposure, with_open_shutter=None)
        numpy_image_with_metadata['mode'] = mode
        numpy_image_with_metadata['number'] = str(self.frame_num).zfill(self.total_digits_count)

        self.frame_num += 1
        # prepare_send_frame(numpy_image_with_metadata, self)

        if self.worker_process is not None:
            self.worker_process.join()
        
        self.worker_process = mp.Process(target=prepare_send_frame, args=(numpy_image_with_metadata, self, self.network_lock))
        self.worker_process.start()

    def run(self):
        self.to_be_stopped = False
        self.stop_exception = None
        self.tomograph.source_power_on()
        self.tomograph.reset_to_zero_angle()
        self.collect_dark_frames()
        self.collect_empty_frames()
        self.collect_data_frames()
        self.tomograph.close_shutter()
        self.tomograph.source_power_off()
        return

    def collect_data_frames(self):
        initial_angle = self.tomograph.get_angle()
        initial_angle = initial_angle if initial_angle is not None else 0
        data_angles = np.round((np.arange(0, self.DATA_step_count)) * self.DATA_angle_step + initial_angle, 2) % 360

        exp_angles = data_angles

        self.tomograph.move_back()
        self.tomograph.open_shutter(0)
        for iangle, current_angle in enumerate(exp_angles):
            # self.check_source()
            tomo_logger.info(f'Collecting frame {iangle}/{len(exp_angles)}')
            self.tomograph.set_angle(float(current_angle))

            for j in range(0, self.DATA_count_per_step):
                self.get_and_send_frame(exposure=self.DATA_exposure, mode='data')

        self.tomograph.close_shutter(0)

    def collect_empty_frames(self):
        self.tomograph.move_away()
        self.tomograph.open_shutter(0)
        for i in range(0, self.EMPTY_count):
            # self.check_source()
            self.get_and_send_frame(self.EMPTY_exposure, mode='empty')
        self.tomograph.close_shutter(0)
        self.tomograph.move_back()

    def collect_dark_frames(self):
        self.tomograph.close_shutter(0)
        time.sleep(0.5)
        for _ in range(0, self.DARK_count):
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


# Frame functions
# @traced
def prepare_send_frame(numpy_image_with_metadata, experiment, lock=None):
    image_numpy = numpy_image_with_metadata['image_data']['raw_image']
    del numpy_image_with_metadata['image_data']['raw_image']
    frame_metadata = numpy_image_with_metadata

    try:
        if experiment:
            frame_metadata_event = create_event(event_type='frame', exp_id=experiment.exp_id, MoF=frame_metadata)
            # frame_metadata_event = create_event(event_type='frame', exp_id=1, MoF=frame_metadata)
            send_frame_to_storage_webpage(frame_metadata_event=frame_metadata_event,
                                          image_numpy=image_numpy, lock=lock)
        else:
            make_png(image_numpy)

    except ModExpError as e:
        # logging.error('Can\'t send frame number {} to server. {}'.format(numpy_image_with_metadata['number'], e.message))
        if experiment is not None:
            experiment.stop_exception = e
            experiment.to_be_stopped = True
        return False, e

    # logging.debug('Sended frame number {} to server.'.format(numpy_image_with_metadata['number']))
    return True, None


def send_frame_to_storage_webpage(frame_metadata_event, image_numpy, lock=None):
    s = BytesIO()
    np.savez_compressed(s, frame_data=image_numpy)
    logging.debug(image_numpy.shape)
    # s.seek(0)
    del image_numpy
    data = {'data': json.dumps(frame_metadata_event)}
    files = {'file': s.getvalue()}
    if lock is not None:
        lock.acquire()
    p = mp.Process(target=send_to_storage, args=(STORAGE_FRAMES_URI, data, lock, files))
    p.start()


def send_to_storage(storage_uri, data, lock=None, files=None):
    try:
        storage_resp = requests.post(storage_uri, files=files, data=data)
    except Exception as e:
        raise ModExpError(error='Problems with storage', exception_message='Could not send to storage {}'.format(e.message))

    try:
        storage_resp_dict = json.loads(storage_resp.content)
    except (ValueError, TypeError):
        raise ModExpError(error='Problems with storage', exception_message='Storage\'s response is not JSON')

    if not ('result' in storage_resp_dict.keys()):
        raise ModExpError(error='Problems with storage',
                          exception_message="Storage\'s response has incorrect format (no 'result' key)")

    if storage_resp_dict['result'] != 'success':
        raise ModExpError(error='Problems with storage',
                          exception_message='Storage\'s response:  ' + str(storage_resp_dict['result']))
    if lock is not None:
        lock.release()


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
        raise ModExpError(error="Could not make png-file from image", exception_message=e.message)


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

        if not ('instruction' in exp_param.keys()):
            return False, 'Incorrect format'
        if not (type(exp_param['instruction']) is str):
            return False, 'Type of instruction must be unicode'
        if exp_param['instruction'].find(".__") != -1:
            return False, 'Unacceptable instruction, there must not be substring ".__"'
        if exp_param['instruction'].find("t_0M_o_9_r_") != -1:
            return False, 'Unacceptable instruction, there must not be substring "t_0M_o_9_r_"'
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
