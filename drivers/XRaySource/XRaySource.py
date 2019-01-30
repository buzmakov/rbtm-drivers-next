import serial
import logging
from time import sleep

command_timeout = 5  # wait 2 seconds for setting voltage


TIMEOUT = 10


def handle_error(s1, s2):
    print(s1, s2)


class HWSource(object):
    def __init__(self, tty_name):
        logging.debug('Source.__init__ starting...')
        self.tty_name = tty_name
        logging.debug('Source.__init__ finished.')

    def on_high_voltage(self):
        logging.debug('Source.on_high_voltage() starting...')
        with serial.Serial(self.tty_name, timeout=TIMEOUT) as serial_port:
            serial_port.write("HV:1\n".encode())
            sleep(10)
            error = self._get_error(serial_port)
            if error is not None:
                logging.error(
                    "Source.on_high_voltage() error: {}".format(error)
                )
        logging.debug('Source.on_high_voltage() finished.')
        return {'error': error}

    def off_high_voltage(self):
        logging.debug('Source.off_high_voltage() starting...')
        with serial.Serial(self.tty_name, timeout=TIMEOUT) as serial_port:
            serial_port.write("HV:0\n".encode())
            sleep(command_timeout)
            error = self._get_error(serial_port)
            if error is not None:
                logging.error(
                    "Source.off_high_voltage() error: {}".format(error)
                )
        logging.debug('Source.off_high_voltage() finished.')
        return {'error': error}

    def is_on_high_volatge(self):
        logging.debug('Source.is_on_high_voltage() starting...')
        with serial.Serial(self.tty_name, timeout=TIMEOUT) as serial_port:
            serial_port.write("SR:01\n".encode())
            answer = self.get_data_string(serial_port)
            error = self._get_error(serial_port)
            if error is not None:
                logging.error(
                    "Source.is_on_high_voltage() error: {}".format(error)
                )
        logging.debug('Sourceis_on_high_voltage() finished.')
        res = self.get_number(answer) & 64 != 0
        return {'is_on_high_volatge': res, 'error': error}

    def get_nominal_voltage(self):
        logging.debug('Source.get_nominal_voltage() starting...')
        with serial.Serial(self.tty_name, timeout=TIMEOUT) as serial_port:
            serial_port.write("VN\n".encode())
            answer = self.get_data_string(serial_port)
            error = self._get_error(serial_port)
            if error is not None:
                logging.error(
                    "Source.get_nominal_voltage() error: {}".format(error)
                )
        logging.debug('Source.get_nominal_voltage() finished.')
        res = self.get_number(answer) / 1000
        return {'nominal_voltage': res, 'error': error}

    def get_actual_voltage(self):
        logging.debug('Source.get_actual_voltage() starting...')
        with serial.Serial(self.tty_name, timeout=TIMEOUT) as serial_port:
            serial_port.write("VA\n".encode())
            answer = self.get_data_string(serial_port)
            error = self._get_error(serial_port)
            if error is not None:
                logging.error(
                    "Source.get_actual_voltage() error: {}".format(error)
                )
        logging.debug('Source.get_actual_voltage() finished.')
        res = self.get_number(answer) / 1000
        return {'actual_voltage': res, 'error': error}

    def get_nominal_current(self):
        logging.debug('Source.get_nominal_current() starting...')
        with serial.Serial(self.tty_name, timeout=TIMEOUT) as serial_port:
            serial_port.write("CN\n".encode())
            answer = self.get_data_string(serial_port)
            error = self._get_error(serial_port)
            if error is not None:
                logging.error(
                    "Source.get_nominal_current() error: {}".format(error)
                )
        logging.debug('Source.get_nominal_current() finished.')
        res = self.get_number(answer) / 1000
        return {'nominal_current': res, 'error': error}

    def get_actual_current(self):
        logging.debug('Source.get_actual_current) starting...')
        with serial.Serial(self.tty_name, timeout=TIMEOUT) as serial_port:
            serial_port.write("CA\n".encode())
            answer = self.get_data_string(serial_port)
            error = self._get_error(serial_port)
            if error is not None:
                logging.error(
                    "Source.get_actual_current() error: {}".format(error)
                )
        logging.debug('Source.get_actual_current() finished.')
        res = self.get_number(answer) / 1000
        return {'actual_current': res, 'error': error}

    def set_voltage(self, voltage):
        logging.debug('Source.set_voltage() starting...')
        command = "SV:{}\n".format(str(voltage*1000).zfill(6)).encode()
        with serial.Serial(self.tty_name, timeout=TIMEOUT) as serial_port:
            serial_port.write(command)
            sleep(command_timeout)
            error = self._get_error(serial_port)
            if error is not None:
                logging.error(
                    "Source.set_voltage() error: {}".format(error)
                )
        logging.debug('Source.set_voltage() finished.')
        return {'error': error}

    def set_current(self, current):
        logging.debug('Source.set_current() starting...')
        command = "SC:{}\n".format(str(current*1000).zfill(6)).encode()
        with serial.Serial(self.tty_name, timeout=TIMEOUT) as serial_port:
            serial_port.write(command)
            sleep(command_timeout)
            error = self._get_error(serial_port)
            if error is not None:
                logging.error(
                    "Source.set_current() error: {}".format(error)
                )
        logging.debug('Source.set_current() finished.')
        return {'error': error}

    def get_id(self):
        logging.debug('Source.get_id() starting...')
        with serial.Serial(self.tty_name, timeout=TIMEOUT) as serial_port:
            serial_port.write("ID\n".encode())
            answer = self.get_data_string(serial_port)
            error = self._get_error(serial_port)
            if error is not None:
                logging.error(
                    "Source.get_id() error: {}".format(error)
                )
        logging.debug('Source.get_id() finished.')
        res = answer
        return {'id': res, 'error': error}

    def get_tube_name(self):
        logging.debug('Source.get_nominal_voltage() starting...')
        with serial.Serial(self.tty_name, timeout=TIMEOUT) as serial_port:
            serial_port.write("XT\n".encode())
            answer = self.get_data_string(serial_port)
            error = self._get_error(serial_port)
            if error is not None:
                logging.error(
                    "Source.get_actual_voltage() error: {}".format(error)
                )
        logging.debug('Source.get_actual_voltage() finished.')
        res = answer
        return {'tube_name': res, 'error': error}

    def get_error(self):
        with serial.Serial(self.tty_name, timeout=TIMEOUT) as serial_port:
            return self._get_error(serial_port)

    def _get_error(self, serial_port):
        serial_port.write("SR:12\n".encode())
        answer = self.get_data_string(serial_port)
        error_code = int(answer[1:-1])

        if error_code != 0:
            serial_port.write("ER\n".encode())
            error_line = self.get_data_string(serial_port)
            print(error_line)
            return ord(error_line[0]), error_line[2:]
        else:
            return None

    # auxiliary functions

    @staticmethod
    def get_data_string(serial_port):
        cur_byte = serial_port.read()
        line = cur_byte
        while cur_byte != '\r'.encode():
            cur_byte = serial_port.read()
            line = line + cur_byte
        return line.decode()

    @staticmethod
    def get_number(line):  # TODO: check it
        return int(line[1:])  # remove first "*"

    def get_state(self, options=None):
        if options is None:
            options = ['is_on_high_voltage', 'id', 'tube_name',
                       'actual_voltage', 'nominal_voltage',
                       'actual_current', 'nominal_current']
        res = {}
        if not isinstance(options, (list, tuple)):
            options = [options, ]

        for option in options:
            if option == 'is_on_high_voltage':
                s = self.is_on_high_volatge()
            elif option == 'id':
                s = self.get_id()
            elif option == 'tube_name':
                s = self.get_tube_name()
            elif option == 'actual_voltage':
                s = self.get_actual_voltage()
            elif option == 'nominal_voltage':
                s = self.get_nominal_voltage()
            elif option == 'actual_current':
                s = self.get_actual_current()
            elif option == 'nominal_current':
                s = self.get_nominal_current()
            else:
                s = {'error': 'Unsupported option'}
            res[option] = s
        return res

    def set_state(self, options_dict, force=False):
        res = {}
        for option in options_dict:
            if option == 'set_voltage':
                s = self.set_voltage(options_dict['set_voltage'])
            elif option == 'set_current':
                s = self.set_current(options_dict['set_current'])
            elif option == 'high_voltage':
                if options_dict['high_voltage'] is True:
                    s = self.on_high_voltage()
                elif options_dict['high_voltage'] is False:
                    s = self.off_high_voltage()
                else:
                    s = {
                        'error': 'Unsupported parameter. Should be True or False, but {} given'.format(options_dict['high_voltage'])}
            else:
                s = {'error': 'Unsupported option'}

            res[option] = s

        return {'requested_state': options_dict,
                'result': res}
