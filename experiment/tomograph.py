import datetime
import time
import json

from .experiment import ModExpError, Experiment, create_event, send_message_to_storage_webpage
from .constants import *
from drivers.Tomograph.Tomograph import HWTomograph

class Tomograph:

    def __init__(self):
        self.hwtomo = HWTomograph()
        self.current_experiment = None
        self.x_position = 0  # mock only property
        self.y_position = 0  # mock only property
        self.angle_position = 0  # mock only property
        self.prev_x_position = None  # mock only property
        self.exposure = None  # mock only property
        self.chip_temp = 10  # mock only property
        self.hous_temp = 12  # mock only property
        self.object_present = True  # mock only property

    def shutter_status(self):
        if self.hwtomo.shutter.is_open():
            return "OPEN"
        else:
            return "CLOSE"

    def basic_tomo_check(self, from_experiment):
        if not from_experiment:
            if self.current_experiment is not None:
                raise ModExpError(error='On this tomograph experiment is running')
        else:
            if self.current_experiment.to_be_stopped:
                raise self.current_experiment.stop_exception

    def tomo_state(self):
        if self.current_experiment is not None:
            return 'experiment', ""
        else:
            return 'ready', ""

    def source_power_on(self, from_experiment=False):
        self.basic_tomo_check(from_experiment)

    def source_power_off(self, from_experiment=False):
        self.basic_tomo_check(from_experiment)

    def source_set_voltage(self, new_voltage, from_experiment=False):
        self.basic_tomo_check(from_experiment=from_experiment)

        if type(new_voltage) is not float:
            raise ModExpError(error='Incorrect format: type must be float')

        if new_voltage < 2 or 60 < new_voltage:
            raise ModExpError(error='Voltage must have value from 2 to 60!')

        self.hwtomo.source.set_voltage(new_voltage)

    def source_set_current(self, new_current, from_experiment=False):
        self.basic_tomo_check(from_experiment=from_experiment)

        if type(new_current) is not float:
            raise ModExpError(error='Incorrect format: type must be float')

        if new_current < 2 or 80 < new_current:
            raise ModExpError(error='Current must have value from 2 to 80!')

        self.hwtomo.source.set_current(new_current)

    def source_get_voltage(self, from_experiment=False):
        self.basic_tomo_check(from_experiment=from_experiment)
        return self.hwtomo.source.get_actual_voltage()

    def source_get_current(self, from_experiment=False):
        self.basic_tomo_check(from_experiment=from_experiment)
        return self.hwtomo.source.get_actual_current()

    def open_shutter(self, time_=0, from_experiment=False):
        self.basic_tomo_check(from_experiment)
        self.hwtomo.shutter.open()
        return self.shutter_status()

    def close_shutter(self, time_=0, from_experiment=False):
        self.basic_tomo_check(from_experiment)
        self.hwtomo.shutter.close()
        return self.shutter_status()

    def shutter_state(self, from_experiment=False):
        self.basic_tomo_check(from_experiment)
        return json.dumps({'state': self.shutter_status()})

    def set_x(self, new_x, from_experiment=False):
        self.basic_tomo_check(from_experiment)

        if type(new_x) not in (int, float):
            raise ModExpError(error='Incorrect type! Position type must be int, but it is ' + str(type(new_x)))

        if new_x < -5000 or 2000 < new_x:
            raise ModExpError(error='Position must have value from -5000 to 2000')

        self.x_position = new_x

    def set_y(self, new_y, from_experiment=False):
        self.basic_tomo_check(from_experiment)

        if type(new_y) not in (int, float):
            raise ModExpError(error='Incorrect type! Position type must be int, but it is ' + str(type(new_y)))

        if new_y < -5000 or 2000 < new_y:
            raise ModExpError(error='Position must have value from -30 to 30')

        self.y_position = new_y

    def set_angle(self, new_angle, from_experiment=False):
        self.basic_tomo_check(from_experiment)

        if type(new_angle) not in (int, float):
            raise ModExpError(
                error='Incorrect type! Position type must be int or float, but it is ' + str(type(new_angle)))

        new_angle %= 360

        self.angle_position = new_angle

    def get_x(self, from_experiment=False):
        self.basic_tomo_check(from_experiment)
        return self.x_position

    def get_y(self, from_experiment=False):
        self.basic_tomo_check(from_experiment)
        return self.y_position

    def get_angle(self, from_experiment=False):
        self.basic_tomo_check(from_experiment)
        return self.angle_position

    def reset_to_zero_angle(self, from_experiment=False):
        self.basic_tomo_check(from_experiment)
        self.angle_position = 0

    def move_away(self, from_experiment=False):
        self.basic_tomo_check(from_experiment)
        if self.object_present:
            self.prev_x_position = self.x_position
            self.x_position = -4200
            self.object_present = False

    def move_back(self, from_experiment=False):
        self.basic_tomo_check(from_experiment)
        if not self.object_present:
            if self.prev_x_position is not None:
                self.x_position = self.prev_x_position
                self.prev_x_position = None
                self.object_present = True

    def get_frame(self, exposure, with_open_shutter, send_to_webpage=False, from_experiment=False):
        self.basic_tomo_check(from_experiment)

        if exposure:
            self.set_exposure(exposure, from_experiment=from_experiment)

        if with_open_shutter:
            self.open_shutter(from_experiment=from_experiment)
        else:
            self.close_shutter(from_experiment=from_experiment)

        try:
            frame_metadata_json = self.get_detector_frame(from_experiment=from_experiment)
        except Exception as e:
            raise e
        finally:
            self.close_shutter(from_experiment=from_experiment)

        try:
            frame_metadata = json.loads(frame_metadata_json)
        except TypeError:
            raise ModExpError(error='Could not convert frame\'s JSON into dict')

        raw_image = None

        frame_metadata['image_data']['raw_image'] = raw_image
        raw_image_with_metadata = frame_metadata
        return raw_image_with_metadata

    def get_detector_chip_temperature(self, from_experiment=False):
        self.basic_tomo_check(from_experiment)
        return self.chip_temp

    def get_detector_hous_temperature(self, from_experiment=False):
        self.basic_tomo_check(from_experiment)
        return self.hous_temp

    def set_exposure(self, new_exposure, from_experiment=False):
        self.basic_tomo_check(from_experiment)

        if type(new_exposure) not in (int, float):
            raise ModExpError(error='Incorrect type! Exposure type must be int, but it is ' + str(type(new_exposure)))

        if new_exposure < 0.1 or 16000 < new_exposure:
            raise ModExpError(error=('Exposure must have value from 0.1 to 16000 (given is %.1f )' % new_exposure))

        new_exposure = round(new_exposure)
        self.exposure = new_exposure

    def get_exposure(self, from_experiment=False):
        self.basic_tomo_check(from_experiment)
        return self.exposure

    def get_detector_frame(self, from_experiment=False):

        image = None
        current_datetime = datetime.datetime.now().strftime("%d.%m.%Y %H:%M:%S")
        timestamp = time.time()
        detector_data = {'model': 'Ximea xiRAY'}
        image_data = {'timestamp': timestamp,
                      'datetime': current_datetime,
                      'exposure': self.exposure,
                      'detector': detector_data,
                      'chip_temp': self.chip_temp,
                      'hous_temp': self.hous_temp}  # 'image': image,
        object_data = {'present': self.object_present,
                       'angle position': self.angle_position,
                       'horizontal position': self.x_position,
                       # 'vertical position': self.y_position
                       }
        shutter_state = json.loads(self.shutter_state(from_experiment=from_experiment))
        shutter_data = {'open': shutter_state['state'] == 'OPEN'}
        source_data = {'voltage': self.hwtomo.source.get_actual_voltage(),
                       'current': self.hwtomo.source.get_actual_current()}

        return json.dumps({'image_data': image_data,
                           'object': object_data,
                           'shutter': shutter_data,
                           'X-ray source': source_data})

    def carry_out_simple_experiment(self, exp_param):
        time_of_experiment_start = time.time()
        self.current_experiment = Experiment(tomograph=self, exp_param=exp_param)

        exp_id = self.current_experiment.exp_id

        try:
            self.current_experiment.run()
        except ModExpError as e:
            event_for_send = e.to_event_dict(exp_id)
            stop_msg = e.stop_msg
        else:
            event_for_send = create_event(event_type='message', exp_id=exp_id, MoF=SUCCESSFUL_STOP_MSG)
            stop_msg = SUCCESSFUL_STOP_MSG

        send_message_to_storage_webpage(event_for_send)

        self.current_experiment = None
