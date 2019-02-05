# encoding: utf-8
import serial
import re
import logging


class HWShutter(object):
    """Shutter for X-ray source """

    def __init__(self, tty_name, relay_number):
        """
        Init shutter object

        :param tty_name: COM port name to connect
        :param relay_number: number of relay 1-4

        """
        logging.debug('Shutter.__init__ starting...')
        super(HWShutter, self).__init__()
        self.tty_name = tty_name
        self.relay_number = relay_number
        self.check_module()
        logging.debug('Shutter.__init__ finished.')

    def check_module(self):
        """
        Is controller alive?
        """
        logging.debug('Shutter.check_module() starting...')
        with serial.Serial(self.tty_name) as serial_port:
            # HACK: check twice because at startup #ERR is always returned.
            # So it's important to call this method at initialization.

            serial_port.write("$KE\r\n".encode())
            serial_port.readline()
            serial_port.write("$KE\r\n".encode())
            status = serial_port.readline()
            if status != '#OK\r\n'.encode():
                error = status.decode('utf-8')
                logging.error("Shutter.check_module() error: {}".format(error))
            else:
                error = None

        logging.debug('Shutter.check_module() finished.')
        return {'error': error}

    def open(self):
        """
        Open relay

        """
        logging.debug('Shutter.open() starting...')
        with serial.Serial(self.tty_name) as serial_port:
            serial_port.write("$KE,REL,{},1\r\n".format(
                self.relay_number).encode())
            if serial_port.readline() != "#REL,OK\r\n".encode():
                error = "Shutter.open(): Can't set value 1 to relay"
                logging.error(error)
            else:
                error = None

        logging.debug('Shutter.open() finished.')
        return {'error': error}

    def close(self):
        """
        Close relay

        """
        logging.debug('Shutter.close() starting...')
        with serial.Serial(self.tty_name) as serial_port:
            serial_port.write("$KE,REL,{},0\r\n".format(
                self.relay_number).encode())
            if serial_port.readline() != "#REL,OK\r\n".encode():
                error = "Shutter.close(): Can't set value 0 to relay"
                logging.error(error)
            else:
                error = None
        logging.debug('Shutter.close() finished.')
        return {'error': error}

    def is_open(self):
        logging.debug('Shutter.is_open() starting...')
        with serial.Serial(self.tty_name) as serial_port:
            serial_port.write("$KE,RDR,{}\r\n".format(
                self.relay_number).encode())
            relay_state = serial_port.readline().decode().strip()

        pattern = re.compile("^#RDR,{},(0|1)$".format(self.relay_number))
        matched = pattern.match(relay_state)
        if matched:
            relay_state = bool(int(matched.group(1)))
            error = None
        else:
            error = relay_state
            logging.error(
                "Shutter.is_open(): Can't get relay state, got {}".format(relay_state))
        logging.debug('Shutter.is_open() finished.')

        return {'value': relay_state, 'error': error}

    def get_state(self, options=None):
        if options is None:
            options = ['is_open']
        res = {}
        if not isinstance(options, (list, tuple)):
            options = [options, ]

        for option in options:
            if option == 'is_open':
                s = self.is_open()
            else:
                s = {'error': 'Unsupported option'}
            res[option] = s

        return res

    def set_state(self, options_dict, force=False):
        res = {}
        for option in options_dict:
            if option == 'is_open':
                if options_dict['is_open']:
                    s = self.open()
                elif not options_dict['is_open']:
                    s = self.close()
                else:
                    s = {'error': 'Unsupported option'}
            else:
                s = {'error': 'Unsupported option'}
            res[option] = s

        return {'requested_state': options_dict,
                'result': res}
