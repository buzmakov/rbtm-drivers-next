import datetime
import time
import json

from .experiment import ModExpError, Experiment, create_event, send_message_to_storage_webpage
from .constants import SUCCESSFUL_STOP_MSG
# from drivers.Tomograph.Tomograph import HWTomograph
from .redis_proxy import RedisProxy

from autologging import traced
from . import tomo_logger

class HWTomograph:
    pass

@traced(tomo_logger.logger)
class Tomograph:
    def __init__(self, mock=True, redis_host='redis', redis_port=6379, redis_db=0):
        # Используем RedisProxy для инициализации HWTomograph
        HWTomographProxy = RedisProxy.create(HWTomograph, 
                                     redis_host=redis_host, 
                                     redis_port=redis_port, 
                                     redis_db=redis_db, 
                                     )
        self.hwtomo = HWTomographProxy(mock=mock)
        self.current_experiment = None
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
        pass

    def source_power_off(self):
        pass

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
        if type(new_x) not in (int, float):
            raise ModExpError(error='Incorrect type! Position type must be int, but it is ' + str(type(new_x)))

        if new_x < -5000 or 2000 < new_x:
            raise ModExpError(error='Position must have value from -5000 to 2000')

        self.hwtomo.horizontal_motor.move_to_position(new_x)

    def set_y(self, new_y):
        if type(new_y) not in (int, float):
            raise ModExpError(error='Incorrect type! Position type must be int, but it is ' + str(type(new_y)))

        if new_y < -5000 or 2000 < new_y:
            raise ModExpError(error='Position must have value from -30 to 30')

        self.y_position = new_y

    def set_angle(self, new_angle):
        """

        :param new_angle: angle in degrees
        """
        if type(new_angle) not in (int, float):
            raise ModExpError(
                error='Incorrect type! Position type must be int or float, but it is ' + str(type(new_angle)))

        new_angle %= 360
        self.hwtomo.angle_motor.move_to_position_deg(new_angle)

    def get_x(self):
        return self.hwtomo.horizontal_motor.get_position()

    def get_y(self):
        return self.y_position

    def get_angle(self):
        return self.hwtomo.angle_motor.get_position_deg()

    def reset_to_zero_angle(self):
        self.hwtomo.angle_motor.set_zero()

    def move_away(self):
        self.hwtomo.horizontal_motor.move_to_position(-6000) #TODO: take value from config
        self.object_present = False

    def move_back(self):
        self.hwtomo.horizontal_motor.move_to_position(0)
        self.object_present = True

    def get_detector_chip_temperature(self):
        return self.hwtomo.detector.get_sensor_temp()

    def get_detector_hous_temperature(self):
        return self.hwtomo.detector.get_hous_temp()

    def get_detector_model(self):
        return self.hwtomo.detector.get_model()

    def get_frame(self, exposure: float, with_open_shutter=None, send_to_webpage=False):
        """
        :param: exposue: exposition in millisecomds
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
        detector_data = {'model': self.hwtomo.detector.get_model()}
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

        try:
            self.current_experiment.run()
        except ModExpError as e:   # TODO: should we crashed here?
            event_for_send = e.to_event_dict(exp_id)
            # stop_msg = e.stop_msg
        else:
            event_for_send = create_event(event_type='message', exp_id=exp_id, MoF=SUCCESSFUL_STOP_MSG)
            # stop_msg = SUCCESSFUL_STOP_MSG

        send_message_to_storage_webpage(event_for_send)

        self.current_experiment = None
