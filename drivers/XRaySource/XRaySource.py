import serial
import logging
from time import sleep
import atexit

command_timeout = 5  # wait 2 seconds for setting voltage

TIMEOUT = 10


def handle_error(s1, s2):
    print(s1, s2)


class HWSource(object):
    def __init__(self, tty_name):
        logging.debug('Source.__init__ starting...')
        self.tty_name = tty_name
        self.serial_port = serial.Serial(self.tty_name, timeout=TIMEOUT)
        logging.debug('Source.__init__ finished.')
        atexit.register(self.cleanup)

    def cleanup(self):
        self.serial_port.close()

    def wait_for_high_voltage(self):
        n = 0
        while n < 10 or not self.get_status()['power status']['voltage kv norm']:
            sleep(1)
            n = n + 1

    def on_high_voltage(self):
        logging.debug('Source.on_high_voltage() starting...')
        self.serial_port.write("HV:1\n".encode())
        error = self.get_error()
        if error is not None:
            logging.error("Source.on_high_voltage() error: {}".format(error))

        self.wait_for_high_voltage()
        logging.debug('Source.on_high_voltage() finished.')
        return {'error': error}

    def off_high_voltage(self):
        logging.debug('Source.off_high_voltage() starting...')
        self.serial_port.write("HV:0\n".encode())
        error = self.get_error()
        if error is not None:
            logging.error("Source.off_high_voltage() error: {}".format(error))

        self.wait_for_high_voltage()

        logging.debug('Source.off_high_voltage() finished.')
        return {'error': error}

    def is_on_high_volatge(self):
        logging.debug('Source.is_on_high_voltage() starting...')
        status = self.get_status()
        logging.debug('Sourceis_on_high_voltage() finished.')
        return {'is_on_high_volatge': status['power status']['high volatge on'], 'error': status}

    def read_status_word(self, word_number):
        logging.debug('Source.read_status_word() starting...')
        if word_number not in [1, 6, 12, 30]:
            logging.error("Source.read_status_word() error: {}".format('unknown status word number'))

        self.serial_port.write("SR:{}\n".format(str(word_number).zfill(2)).encode())
        answer = self.get_data_string()
        error = self.get_error()
        if error is not None:
            logging.error("Source.read_status_word() error: {}".format(error))

        logging.debug('Source.read_status_word() finished.')
        return self.get_number(answer)

    def get_status(self):
        sw_1 = self.read_status_word(1)
        res = {'power status': {
            'external pc control': sw_1 & 128 == 1,
            'high voltage on': sw_1 & 64 == 1,
            'cooling system ok': sw_1 & 32 == 0,
            'buffer battery ok': sw_1 & 16 == 0,
            'current ma norm': sw_1 & 8 == 0,
            'voltage kv norm': sw_1 & 4 == 0
        }}

        sw_6 = self.read_status_word(6)
        res['warming status'] = {
            'in progress': sw_6 & 8 == 1,
            'warming interrupted': sw_6 & 4 == 1,
            'warming from pc': sw_6 & 2 == 1,
            'warming from kb': sw_6 & 1 == 1
        }

        # sw_12 = self.read_status_word(12)
        # res['Error status'] = status_strings[ord(sw_12)] if ord(sw_12) in status_strings else None

        return res

    def get_nominal_voltage(self):
        logging.debug('Source.get_nominal_voltage() starting...')
        self.serial_port.write("VN\n".encode())
        answer = self.get_data_string()
        error = self.get_error()
        if error is not None:
            logging.error("Source.get_nominal_voltage() error: {}".format(error))
        logging.debug('Source.get_nominal_voltage() finished.')
        res = self.get_number(answer) / 1000
        return {'nominal_voltage': res, 'error': error}

    def get_actual_voltage(self):
        logging.debug('Source.get_actual_voltage() starting...')
        self.serial_port.write("VA\n".encode())
        answer = self.get_data_string()
        error = self.get_error()
        if error is not None:
            logging.error(
                "Source.get_actual_voltage() error: {}".format(error)
            )
        logging.debug('Source.get_actual_voltage() finished.')
        res = self.get_number(answer) / 1000
        return {'actual_voltage': res, 'error': error}

    def get_nominal_current(self):
        logging.debug('Source.get_nominal_current() starting...')
        self.serial_port.write("CN\n".encode())
        answer = self.get_data_string()
        error = self.get_error()
        if error is not None:
            logging.error(
                "Source.get_nominal_current() error: {}".format(error)
            )
        logging.debug('Source.get_nominal_current() finished.')
        res = self.get_number(answer) / 1000
        return {'nominal_current': res, 'error': error}

    def get_actual_current(self):
        logging.debug('Source.get_actual_current) starting...')
        self.serial_port.write("CA\n".encode())
        answer = self.get_data_string()
        error = self.get_error()
        if error is not None:
            logging.error(
                "Source.get_actual_current() error: {}".format(error)
            )
        logging.debug('Source.get_actual_current() finished.')
        res = self.get_number(answer) / 1000
        return {'actual_current': res, 'error': error}

    def set_voltage(self, voltage):
        logging.debug('Source.set_voltage() starting...')
        command = "SV:{}\n".format(str(voltage * 1000).zfill(6)).encode()
        self.serial_port.write(command)
        sleep(command_timeout)
        error = self.get_error()
        if error is not None:
            logging.error(
                "Source.set_voltage() error: {}".format(error)
            )
        logging.debug('Source.set_voltage() finished.')
        return {'error': error}

    def set_current(self, current):
        logging.debug('Source.set_current() starting...')
        command = "SC:{}\n".format(str(current * 1000).zfill(6)).encode()
        self.serial_port.write(command)
        sleep(command_timeout)
        error = self.get_error()
        if error is not None:
            logging.error(
                "Source.set_current() error: {}".format(error)
            )
        logging.debug('Source.set_current() finished.')
        return {'error': error}

    def get_id(self):
        logging.debug('Source.get_id() starting...')
        self.serial_port.write("ID\n".encode())
        answer = self.get_data_string()
        error = self.get_error()
        if error is not None:
            logging.error(
                "Source.get_id() error: {}".format(error)
            )
        logging.debug('Source.get_id() finished.')
        res = answer
        return {'id': res, 'error': error}

    def get_tube_name(self):
        logging.debug('Source.get_nominal_voltage() starting...')
        self.serial_port.write("XT\n".encode())
        answer = self.get_data_string()
        error = self.get_error()
        if error is not None:
            logging.error(
                "Source.get_actual_voltage() error: {}".format(error)
            )
        logging.debug('Source.get_actual_voltage() finished.')
        res = answer
        return {'tube_name': res, 'error': error}

    def get_error(self):
        status_strings = {
            33: "Cooling system failed (Неисправность системы охлаждения)",
            35: "Interlock open (Блокировка открыта)",
            37: "Absolute undervoltage monitoring (Абсолютное значение напряжения слишком мало)",
            38: "Absolute overvoltage monitoring (Абсолютное значение напряжения слишком велико)",
            39: "Absolute undercurrent monitoring (Абсолютное значение тока слишком мало)",
            40: "Ground current has released (Ток заземления снят)",
            41: "Overcurrent anode has released (Перегрузка анода по току снята)",
            43: "Extern STOP (Внешний останов)",
            44: "Focus change-over switch defect (Переключатель фокуса неисправен)",
            46: "EMERGENCY-STOP (Аварийный останов)",
            47: "Preselection exceeding rated power (Предустановленное значение превышает номинальную мощность)",
            48: "Overcurrent cathode has released (Перегрузка катода по току снята)",
            50: "Tube overpower (Перегрузка трубки)",
            51: "Preselection out of range (Предустановленное значение за пределами диапазона)",
            52: "Presel. exceeding rated gener. current (Предустановленное значение превышает номинальный ток генератора)",
            53: "High voltage lamp defective (Лампа высокого напряжения неисправна)",
            55: "Relative overcurrent monitoring (Относительное значение тока слишком велико)",
            56: "Relative undervoltage monitoring (Относительное значение напряжения слишком мало)",
            57: "Wrong tube type (Неверный тип трубки)",
            58: "Not programmed (Нет программы)",
            60: "Relative undercurrent monitoring (Относительное значение тока слишком мало)",
            61: "Chopper overcurrent (Ток прерывателя слишком велик)",
            62: "Overtemperature anode (Температура анода слишком велика)",
            63: "Door contact 1 and 2 open (Дверные контакты 1 и 2 разомкнуты)",
            64: "Door contact 1 open (Дверной контакт 1 разомкнут)",
            65: "Door contact 2 open (Дверной контакт 2 разомкнут)",
            66: "Exposuretime = 0 (Нулевое время экспозиции)",
            72: "Preselection out of range, too low (Предустановленное значение за пределами диапазона, слишком мало)",
            74: "High voltage locked (Высокое напряжение заблокировано)",
            76: "Stand-By	(режим ожидания)",
            77: "Preselection too large (Предустановленное значение слишком велико)",
            78: "Overwrite program? (Перезаписать программу?)",
            80: "Temperature supervision power module (Температурный контроль: силовой модуль)",
            82: "HV prim. overcurrent (Ток первичной обмотки высокого напряжения слишком велик)",
            86: "HV contactor faulty (Высоковольтный прерыватель неисправен)",
            87: "Flash lamp faulty (Вспыхивающая лампа неисправна)",
            88: "Chopper temperature (Температура прерывателя)",
            89: "Filament primary overcurrent (Ток первичной обмотки накала слишком велик)",
            90: "Filament primary undercurrent (Ток первичной обмотки накала слишком мал)",
            91: "Buffer battery empty (Буферная батарея разряжена)",
            92: "Powerstage, filament failed (Силовой каскад: неисправность в цепи накала)",
            93: "Powerstage, filament undercurrent (Силовой каскад: ток накала слишком велик)",
            94: "Powerstage, high voltage failed (Силовой каскад: неисправность в цепи высокого напряжения)",
            95: "Chopper failed (неисправность прерывателя)",
            104: "External warning lamp failed (Неисправность внешней сигнальной лампы)",
            105: "Temperature supervision generator (Температурный контроль: генератор)",
            106: "Warm-up necessary (Необходим прогрев)",
            107: "Keypad error (Ошибка клавиатуры)",
            108: "Power failure (low voltage) (Сбой питания или низкое напряжение)",
            109: "Warm-up! 0=No (Прогрев! 0 = Нет)",
            111: "Chopper output voltage failed (Неисправность в цепи выходного напряжения прерывателя)",
            112: "Absolute overcurrent monitoring (Абсолютное значение тока слишком велико)",
            114: "Relative overvoltage monitoring (Относительное значение напряжение слишком велико)",
            115: "Maximum test voltage exceeded (Превышено максимальное значение тестового напряжения)",
            116: "Warm-up terminated after 3 attempts (Прогрев прекращен поле 3 попыток)",
            117: "Warm-up aborted. Try again (Прогрев прерван. Повторите попытку)",
            118: "Push START button (Нажмите кнопку START)",
            119: "Warm-up program completed. ENTER (Программа прогрева завершена. Нажмите ENTER)",
            121: "Observe warm-up instructions! ENTER (Необходимо соблюдать инструкции по прогреву! Нажмите ENTER)",
            123: "Bypass charging resistor faulty (Цепь шунтирования зарядного резистора неисправна)"
        }

        self.serial_port.write("SR:12\n".encode())
        answer = self.get_data_string()
        error_code = int(answer[1:-1])

        if error_code != 0:
            res = status_strings[int(error_code)]
        else:
            res = None

        return res

    # auxiliary functions

    def get_data_string(self):
        cur_byte = self.serial_port.read()
        line = cur_byte
        while cur_byte != '\r'.encode():
            cur_byte = self.serial_port.read()
            line = line + cur_byte
        return line.decode()

    @staticmethod
    def get_number(line):  # TODO: check it
        return int(line[1:])  # remove first "*"

    def get_state(self, options=None):
        if options is None:
            options = ['is_on_high_voltage', 'id', 'tube_name',
                       'actual_voltage', 'nominal_voltage',
                       'actual_current', 'nominal_current', 'status', 'last_error']
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
            elif option == 'status':
                s = self.get_status()
            elif option == 'last_error':
                s = self.get_error()
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
                        'error': 'Unsupported parameter. Should be True or False, but {} given'.format(
                            options_dict['high_voltage'])}
            else:
                s = {'error': 'Unsupported option'}

            res[option] = s

        return {'requested_state': options_dict,
                'result': res}
