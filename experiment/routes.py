from flask import Blueprint, request, send_file, Response
import io
import numpy as np

import threading
import json
from .tomograph import Tomograph
from .experiment import check_and_prepare_exp_parameters, send_to_storage, ModExpError, prepare_send_frame, make_preview_data
from .constants import FRAME_PNG_FILENAME, STORAGE_EXP_START_URI, SOMEONE_STOP_MSG

from . import tomologger
tomo_logger = tomologger.tomologger

bp_main = Blueprint('main', __name__, url_prefix='/')
bp_tomograph = Blueprint('tomograph', __name__, url_prefix='/tomograph/<int:tomo_num>')

tomograph = Tomograph(mock=True)

@bp_tomograph.before_request
@bp_main.before_request
def log_request_info():
    # tomo_logger.logger.info('Headers: %s', request.headers)
    # tomo_logger.logger.info('Body: %s', request.get_data())
    tomo_logger.logger.info('Path: %s', request.path)

@bp_tomograph.after_request
def after_request(response):
    header = response.headers
    header['Access-Control-Allow-Origin'] = '*'
    return response


# Base route
@bp_main.route('/', methods=['GET'])
def main_route():
    return 'RBTM experiment mock'


# State route
@bp_tomograph.route('/state', methods=['GET'])
def check_state(tomo_num):
    tomo_state, exception_message = tomograph.tomo_state()
    return create_response(success=True, result=tomo_state, exception_message=exception_message)


# Source routes
@bp_tomograph.route('/source/power-on', methods=['GET'])
def source_power_on(tomo_num):
    return call_method_create_response(tomo_num, method_name='source_power_on')


@bp_tomograph.route('/source/power-off', methods=['GET'])
def source_power_off(tomo_num):
    return call_method_create_response(tomo_num, method_name='source_power_off')


@bp_tomograph.route('/source/set-voltage', methods=['POST'])
def source_set_voltage(tomo_num):
    success, new_voltage, response_if_fail = check_request(request.data)
    if not success:
        return response_if_fail
    return call_method_create_response(tomo_num, method_name='source_set_voltage', args=new_voltage)


@bp_tomograph.route('/source/set-current', methods=['POST'])
def source_set_current(tomo_num):
    success, new_current, response_if_fail = check_request(request.data)
    if not success:
        return response_if_fail
    return call_method_create_response(tomo_num, method_name='source_set_current', args=new_current)


@bp_tomograph.route('/source/get-voltage', methods=['GET'])
def source_get_voltage(tomo_num):
    return call_method_create_response(tomo_num, method_name='source_get_voltage')


@bp_tomograph.route('/source/get-current', methods=['GET'])
def source_get_current(tomo_num):
    return call_method_create_response(tomo_num, method_name='source_get_current')


# Shutter routes
@bp_tomograph.route('/shutter/open/<int:time_>', methods=['GET'])
def shutter_open(tomo_num, time_):
    return call_method_create_response(tomo_num, method_name='open_shutter', args=time_)


@bp_tomograph.route('/shutter/close/<int:time_>', methods=['GET'])
def shutter_close(tomo_num, time_):
    return call_method_create_response(tomo_num, method_name='close_shutter', args=time_)


@bp_tomograph.route('/shutter/state', methods=['GET'])
def shutter_state(tomo_num):
    return call_method_create_response(tomo_num, method_name='shutter_state')


# Motor routes
@bp_tomograph.route('/motor/set-horizontal-position', methods=['POST'])
def motor_set_horizontal_position(tomo_num):
    success, new_pos, response_if_fail = check_request(request.data)
    if not success:
        return response_if_fail
    return call_method_create_response(tomo_num, method_name='set_x', args=new_pos)


@bp_tomograph.route('/motor/set-vertical-position', methods=['POST'])
def motor_set_vertical_position(tomo_num):
    success, new_pos, response_if_fail = check_request(request.data)
    if not success:
        return response_if_fail
    return call_method_create_response(tomo_num, method_name='set_y', args=new_pos)


@bp_tomograph.route('/motor/set-angle-position', methods=['POST'])
def motor_set_angle_position(tomo_num):
    success, new_pos, response_if_fail = check_request(request.data)
    if not success:
        return response_if_fail
    return call_method_create_response(tomo_num, method_name='set_angle', args=new_pos)


@bp_tomograph.route('/motor/get-horizontal-position', methods=['GET'])
def motor_get_horizontal_position(tomo_num):
    return call_method_create_response(tomo_num, method_name='get_x')


@bp_tomograph.route('/motor/get-vertical-position', methods=['GET'])
def motor_get_vertical_position(tomo_num):
    return call_method_create_response(tomo_num, method_name='get_y')


@bp_tomograph.route('/motor/get-angle-position', methods=['GET'])
def motor_get_angle_position(tomo_num):
    return call_method_create_response(tomo_num, method_name='get_angle')


@bp_tomograph.route('/motor/reset-angle-position', methods=['GET'])
def motor_reset_angle_position(tomo_num):
    return call_method_create_response(tomo_num, method_name='reset_to_zero_angle')


@bp_tomograph.route('/motor/move-away', methods=['GET'])
def motor_move_away(tomo_num):
    return call_method_create_response(tomo_num, method_name='move_away')


@bp_tomograph.route('/motor/move-back', methods=['GET'])
def motor_move_back(tomo_num):
    return call_method_create_response(tomo_num, method_name='move_back')


# Detector routes
@bp_tomograph.route('/detector/get-frame', methods=['POST'])
def detector_get_frame(tomo_num):
    success, exposure, response_if_fail = check_request(request.data)
    if not success:
        return response_if_fail
    return call_method_create_response(tomo_num, method_name='get_frame', args=(exposure, True), GET_FRAME_method=True)


@bp_tomograph.route('/detector/get-frame-with-closed-shutter', methods=['POST'])
def detector_get_frame_with_closed_shutter(tomo_num):
    success, exposure, response_if_fail = check_request(request.data)
    if not success:
        return response_if_fail
    return call_method_create_response(tomo_num, method_name='get_frame', args=(exposure, False), GET_FRAME_method=True)


@bp_tomograph.route('/detector/chip_temp', methods=['GET'])
def detector_get_chip_temperature(tomo_num):
    return call_method_create_response(tomo_num, method_name='get_detector_chip_temperature')


@bp_tomograph.route('/detector/hous_temp', methods=['GET'])
def detector_get_hous_temperature(tomo_num):
    return call_method_create_response(tomo_num, method_name='get_detector_hous_temperature')


@bp_tomograph.route('/detector/model', methods=['GET'])
def detector_get_model(tomo_num):
    return call_method_create_response(tomo_num, method_name='get_detector_model')


@bp_tomograph.route('/detector/get-frame-preview', methods=['POST'])
def detector_get_frame_preview(tomo_num):
    """
    Capture a frame and return a downsampled uint16 numpy array (npz).

    Request body JSON:
      exposure_ms  : float  — exposure in milliseconds
      downsample   : int    — integer stride for downsampling (default 4)

    Response: application/octet-stream, npz with keys:
      data   : uint16 2-D array (downsampled + median-filtered)
      width  : scalar int
      height : scalar int
    """
    if not request.data:
        return create_response(success=False, error='Request is empty')

    try:
        body = json.loads(request.data)
    except (TypeError, ValueError):
        return create_response(success=False, error='Request body is not valid JSON')

    # Body can be a bare number (legacy) or a dict {exposure_ms, downsample}
    if isinstance(body, dict):
        exposure = float(body.get('exposure_ms', 1000.0))
        downsample = int(body.get('downsample', 4))
    else:
        try:
            exposure = float(body)
            downsample = 4
        except (TypeError, ValueError):
            return create_response(success=False, error='Invalid exposure value')

    try:
        result = tomograph.get_frame(exposure, with_open_shutter=True)
    except ModExpError as e:
        return e.create_response()

    tomograph.close_shutter()

    image_numpy = result['image_data']['raw_image']

    try:
        preview = make_preview_data(image_numpy, downsample=downsample)
    except ModExpError as e:
        return e.create_response()

    buf = io.BytesIO()
    np.savez_compressed(buf,
                        data=preview['data'],
                        width=np.array(preview['width']),
                        height=np.array(preview['height']))
    buf.seek(0)
    return Response(buf.read(),
                    mimetype='application/octet-stream',
                    headers={'Content-Disposition': 'attachment; filename=preview.npz'})


# Experiment routes
@bp_tomograph.route('/experiment/start', methods=['POST'])  # TODO: POST?
def experiment_start(tomo_num):
    success, data, response_if_fail = check_request(request.data)
    if not success:
        return response_if_fail

    if not (('experiment parameters' in data.keys()) and ('exp_id' in data.keys())):
        return create_response(success=False, error='Incorrect format of keywords')

    if not ((type(data['experiment parameters']) is dict) and (type(data['exp_id']) is str)):
        return create_response(success=False, error='Incorrect format: incorrect types')

    exp_param = data['experiment parameters']
    exp_param['exp_id'] = data['exp_id']

    success, error = check_and_prepare_exp_parameters(exp_param)
    if not success:
        return create_response(success=success, error=error)

    tomo_state, exception_message = tomograph.tomo_state()
    if tomo_state == 'unavailable':
        return create_response(success=False, error="Could not connect with tomograph",
                               exception_message=exception_message)
    elif tomo_state == 'experiment':
        return create_response(success=False, error="On this tomograph experiment is running")
    elif tomo_state != 'ready':
        return create_response(success=False, error="Undefined tomograph state")

    try:
        # Обогащаем данные эксперимента параметрами детектора
        try:
            data_dict = json.loads(request.data)
            data_dict['detector_model'] = tomograph.get_detector_model()
            data_dict['pixel_size'] = tomograph.get_detector_pixel_size()
            enriched_data = json.dumps(data_dict).encode()
        except Exception:
            enriched_data = request.data
        send_to_storage(STORAGE_EXP_START_URI, data=enriched_data)
    except ModExpError as e:  #TODO: should we crashed here?
        return e.create_response()

    if exp_param['advanced']:
        pass
        # thr = threading.Thread(target=carry_out_advanced_experiment, args=(tomograph, exp_param))
    else:
        thr = threading.Thread(target=tomograph.carry_out_simple_experiment, args=(exp_param,))
        thr.start()

    return create_response(True)


@bp_tomograph.route('/experiment/stop', methods=['GET'])  # TODO: GET?
def experiment_stop(tomo_num):
    exp_stop_reason_txt = "unknown"

    if tomograph.current_experiment is not None:
        tomograph.current_experiment.to_be_stopped = True
        tomograph.current_experiment.stop_exception = ModExpError(error=exp_stop_reason_txt, stop_msg=SOMEONE_STOP_MSG)

    return create_response(True)


# functions
def create_response(success=True, exception_message='', error='', result=None):
    response_dict = {
        'success': success,
        'exception message': exception_message,
        'error': error,
        'result': result,
    }
    return json.dumps(response_dict)


def call_method_create_response(tomo_num, method_name, args=(), GET_FRAME_method=False):
    if type(args) not in (tuple, list):
        args = (args,)

    try:
        result = getattr(tomograph, method_name)(*args)
    except ModExpError as e:   #TODO: should we crashed here?
        return e.create_response()

    if not GET_FRAME_method:
        return create_response(success=True, result=result)
    else:
        success, ModExpError_if_fail = prepare_send_frame(numpy_image_with_metadata=result, experiment=None)
        tomograph.close_shutter()
        if not success:
            return ModExpError_if_fail.create_response()

        return send_file('../' + FRAME_PNG_FILENAME, mimetype='image/png')


def check_request(request_data):
    if not request_data:
        return False, None, create_response(success=False, error='Request is empty')

    try:
        request_data_dict = json.loads(request_data)
    except TypeError:
        return False, None, create_response(success=False, error='Request has not JSON data')
    else:
        return True, request_data_dict, ''
