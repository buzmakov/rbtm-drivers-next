import serial
import logging
from time import sleep, time
import atexit

TIMEOUT = 10
CACHE_TTL = 3           # секунды: кэшировать значение не дольше
                        # UI опрашивает каждые 3 сек, кадры при съёмке — чаще
WARMUP_TIMEOUT = 1800   # максимальное время прогрева — 30 минут


class HWSource(object):
    """Драйвер рентгеновского источника ISOVOLT 3003 (Seifert/GE).

    Управление через RS-232 (9600 8N1). Протокол ASCII: команда + '\\n',
    ответ начинается с '*', заканчивается '\\r'. Коды ошибок читаются
    командой SR:12.
    """

    STATUS_STRINGS = {
        # ── Низкие коды: состояние/неготовность генератора ───────────────
        1:  "HV on",
        2:  "Ready",
        3:  "Standby",
        4:  "Warm-up running",
        5:  "Fault",
        6:  "Generator not initialised / not ready",
        7:  "Filament current out of tolerance",
        8:  "Coolant flow insufficient",
        9:  "Anode overtemperature",
        10: "Coolant temperature too high",
        11: "Overtemperature generator",
        12: "Filament error",
        13: "Preselected values out of range",
        14: "Filament open circuit",
        15: "Filament short circuit",
        16: "Focus changeover switch error",
        17: "High voltage too high",
        18: "High voltage too low",
        19: "Tube current too high",
        20: "Tube current too low",
        21: "Anode power too high",
        22: "Anode power too low",
        23: "Ground current error",
        24: "HV contactor error",
        25: "HV lamp error",
        26: "Chopper error",
        27: "Chopper temperature error",
        28: "Bypass charging resistor error",
        29: "Flash lamp error",
        30: "External warning lamp error",
        31: "Buffer battery low",
        32: "Keypad error",
        # ── Стандартные коды аварий ───────────────────────────────────────
        33: "Cooling system failed",
        34: "HV interlock error",
        35: "Interlock open",
        36: "Wrong tube type configured",
        37: "Absolute undervoltage monitoring",
        38: "Absolute overvoltage monitoring",
        39: "Absolute undercurrent monitoring",
        40: "Ground current has released",
        41: "Overcurrent anode has released",
        42: "Overcurrent cathode",
        43: "Extern STOP",
        44: "Focus change-over switch defect",
        45: "HV primary voltage error",
        46: "EMERGENCY-STOP",
        47: "Preselection exceeding rated power",
        48: "Overcurrent cathode has released",
        49: "Filament power too high",
        50: "Tube overpower",
        51: "Preselection out of range",
        52: "Presel. exceeding rated generator current",
        53: "High voltage lamp defective",
        54: "Filament primary power error",
        55: "Relative overcurrent monitoring",
        56: "Relative undervoltage monitoring",
        57: "Wrong tube type",
        58: "Not programmed",
        59: "Power stage error",
        60: "Relative undercurrent monitoring",
        61: "Chopper overcurrent",
        62: "Overtemperature anode",
        63: "Door contact 1 and 2 open",
        64: "Door contact 1 open",
        65: "Door contact 2 open",
        66: "Exposuretime = 0",
        67: "Filament primary overcurrent",
        68: "HV primary overcurrent",
        69: "Filament undercurrent",
        70: "HV bridge fault",
        71: "HV primary fault",
        72: "Preselection out of range, too low",
        73: "Preselection too high",
        74: "High voltage locked",
        75: "Interlock chain fault",
        76: "Stand-By",
        77: "Preselection too large",
        78: "Overwrite program?",
        79: "Parameter storage error",
        80: "Temperature supervision power module",
        81: "Power module fault",
        82: "HV prim. overcurrent",
        83: "Filament stage fault",
        84: "HV stage fault",
        85: "Control board fault",
        86: "HV contactor faulty",
        87: "Flash lamp faulty",
        88: "Chopper temperature",
        89: "Filament primary overcurrent",
        90: "Filament primary undercurrent",
        91: "Buffer battery empty",
        92: "Powerstage, filament failed",
        93: "Powerstage, filament undercurrent",
        94: "Powerstage, high voltage failed",
        95: "Chopper failed",
        96: "HV bridge overcurrent",
        97: "Filament bridge overcurrent",
        98: "Output overvoltage",
        99: "Output undervoltage",
        100: "Driver fault",
        101: "Gate drive fault",
        102: "Bus voltage fault",
        103: "Control power fault",
        104: "External warning lamp failed",
        105: "Temperature supervision generator",
        106: "Warm-up necessary",
        107: "Keypad error",
        108: "Power failure (low voltage)",
        109: "Warm-up! 0=No",
        110: "Warm-up program not available",
        111: "Chopper output voltage failed",
        112: "Absolute overcurrent monitoring",
        113: "Relative overvoltage monitoring (secondary)",
        114: "Relative overvoltage monitoring",
        115: "Maximum test voltage exceeded",
        116: "Warm-up terminated after 3 attempts",
        117: "Warm-up aborted. Try again",
        118: "Push START button",
        119: "Warm-up program completed. ENTER",
        120: "Warm-up program running",
        121: "Observe warm-up instructions! ENTER",
        122: "Warm-up step in progress",
        123: "Bypass charging resistor faulty",
        124: "HV module communication error",
        125: "Filament module communication error",
        126: "Control module fault",
        127: "EEPROM write error",
    }

    def __init__(self, tty_name, mock: bool = False):
        """Открыть соединение с источником.

        Args:
            tty_name: Путь к serial-порту, например '/dev/ttyUSB0'.
            mock: Если True — работает без реального устройства.
        """
        logging.debug('Source.__init__ starting...')
        self.mock = mock
        self.tty_name = tty_name
        self.timer_voltage_nominal = None
        self.timer_voltage_actual = None
        self.timer_current_nominal = None
        self.timer_current_actual = None
        self.timer_power_nominal = None
        self.timer_power_actual = None
        self.last_voltage_nominal = None
        self.last_voltage_actual = None
        self.last_current_nominal = None
        self.last_current_actual = None
        self.last_power_nominal = None
        self.last_power_actual = None

        self.device_id = None
        self.tube_name = None

        if mock:
            self.serial_port = None
        else:
            self.serial_port = serial.Serial(
                self.tty_name,
                baudrate=9600,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=TIMEOUT,
                rtscts=False,
                dsrdtr=False,
            )
            self.serial_port.dtr = False
            self.serial_port.rts = False

        logging.debug('Source.__init__ finished.')
        atexit.register(self.close)

    def close(self):
        """Закрыть serial-порт."""
        if self.mock:
            return
        self.serial_port.close()

    # ------------------------------------------------------------------
    # Ожидание готовности
    # ------------------------------------------------------------------

    def wait_for_high_voltage(self):
        """Ожидать включения высокого напряжения (до 10 секунд)."""
        if self.mock:
            return
        n = 0
        while n < 10 and not self.is_on_high_voltage():
            sleep(1)
            n += 1

    def wait_for_high_voltage_down(self):
        """Ожидать выключения высокого напряжения (до 10 секунд)."""
        if self.mock:
            return
        n = 0
        while n < 10 and self.is_on_high_voltage():
            sleep(1)
            n += 1

    def wait_for_voltage(self):
        """Ожидать стабилизации напряжения (до 10 секунд)."""
        if self.mock:
            return
        if not self.is_on_high_voltage():
            return
        n = 0
        while n < 10 and not self.get_status()['power status']['voltage kv norm']:
            sleep(1)
            n += 1

    def wait_for_current(self):
        """Ожидать стабилизации тока (до 10 секунд)."""
        if self.mock:
            return
        if not self.is_on_high_voltage():
            return
        n = 0
        while n < 10 and not self.get_status()['power status']['current ma norm']:
            sleep(1)
            n += 1

    # ------------------------------------------------------------------
    # Управление высоким напряжением
    # ------------------------------------------------------------------

    def on_high_voltage(self):
        """Включить высокое напряжение.

        Если устройство требует прогрева (код ошибки 106), выполняет
        warmup() и повторяет попытку включения (не более 3 раз).

        Raises:
            RuntimeError: При ошибке от устройства или исчерпании попыток.
        """
        if self.mock:
            return
        logging.debug('Source.on_high_voltage() starting...')
        for attempt in range(3):
            self.serial_port.write("HV:1\n".encode())
            error = self.get_error()
            if error is None:
                break
            if error['code'] == 106:
                logging.info('Source.on_high_voltage: warm-up required (attempt %d)', attempt + 1)
                self.warmup()
            else:
                logging.error("Source.on_high_voltage() error: {}".format(error))
                raise RuntimeError("Source.on_high_voltage() error: {}".format(error))
        else:
            raise RuntimeError("Source.on_high_voltage(): warm-up required after 3 attempts")

        self.wait_for_high_voltage()
        self.wait_for_current()
        self.wait_for_voltage()
        logging.debug('Source.on_high_voltage() finished.')

    def off_high_voltage(self):
        """Выключить высокое напряжение.

        Raises:
            RuntimeError: При ошибке от устройства.
        """
        if self.mock:
            return
        logging.debug('Source.off_high_voltage() starting...')
        self.serial_port.write("HV:0\n".encode())
        error = self.get_error()
        if error is not None:
            logging.error("Source.off_high_voltage() error: {}".format(error))
            raise RuntimeError("Source.off_high_voltage() error: {}".format(error))

        self.wait_for_high_voltage_down()
        logging.debug('Source.off_high_voltage() finished.')

    def is_on_high_voltage(self):
        """Вернуть True, если высокое напряжение включено."""
        logging.debug('Source.is_on_high_voltage() starting...')
        status = self.get_status()
        logging.debug('Source.is_on_high_voltage() finished.')
        return status['power status']['high voltage on']

    # Backward-compat alias (опечатка в старом коде)
    is_on_high_volatge = is_on_high_voltage

    def warmup(self):
        """Запустить программу прогрева трубки (WU).

        Читает установленное напряжение, отправляет команду прогрева,
        включает HV и ждёт завершения (не более WARMUP_TIMEOUT секунд).

        Raises:
            RuntimeError: При ошибке включения HV или превышении таймаута.
        """
        if self.mock:
            return
        logging.debug('Source.warmup() starting...')
        voltage = self.get_nominal_voltage()
        self.serial_port.write("WU:4,{}\n".format(
            str(int(round(voltage))).zfill(3)).encode())
        error = self.get_error()
        if error is not None:
            logging.error("Source.warmup() WU error: {}".format(error))
            raise RuntimeError("Source.warmup() WU error: {}".format(error))

        self.serial_port.write("HV:1\n".encode())
        error = self.get_error()
        if error is not None:
            logging.error("Source.warmup() HV error: {}".format(error))
            raise RuntimeError("Source.warmup() HV error: {}".format(error))

        warmup_start = time()
        while True:
            elapsed = time() - warmup_start
            if elapsed > WARMUP_TIMEOUT:
                logging.error(
                    "Source.warmup(): timeout after %.0f seconds (limit %d s)",
                    elapsed, WARMUP_TIMEOUT)
                raise RuntimeError(
                    "Source.warmup(): timeout after {:.0f}s (limit {}s)".format(
                        elapsed, WARMUP_TIMEOUT))

            status = self.get_status()
            ws = status['warming status']
            ps = status['power status']
            logging.info(
                "Source.warmup(): elapsed=%.0fs in_progress=%s from_pc=%s from_kb=%s hv_norm=%s",
                elapsed, ws['in progress'], ws['warming from pc'],
                ws['warming from kb'], ps['voltage kv norm'])
            if not (ws['in progress'] or ws['warming from kb'] or
                    ws['warming from pc'] or ps['voltage kv norm']):
                break
            sleep(5)

        logging.debug('Source.warmup() finished.')

    # ------------------------------------------------------------------
    # Статус
    # ------------------------------------------------------------------

    def read_status_word(self, word_number):
        """Прочитать слово состояния SR:nn.

        Args:
            word_number: Номер слова (1, 6, 12, 30).

        Returns:
            int: Числовое значение слова состояния.
        """
        logging.debug('Source.read_status_word(%d) starting...', word_number)
        if word_number not in [1, 6, 12, 30]:
            logging.error("Source.read_status_word(): unknown word number %d", word_number)

        self.serial_port.write("SR:{}\n".format(str(word_number).zfill(2)).encode())
        answer = self.get_data_string()
        logging.debug('Source.read_status_word(%d) finished.', word_number)
        return self.get_number(answer)

    def get_status(self):
        """Прочитать полный статус устройства (SW1, SW6, SW30).

        Returns:
            dict: Словарь со структурой::

                {
                    'power status': {
                        'external pc control': bool,
                        'high voltage on': bool,
                        'cooling system ok': bool,
                        'buffer battery ok': bool,
                        'current ma norm': bool,
                        'voltage kv norm': bool,
                    },
                    'warming status': {
                        'in progress': bool,
                        'warming interrupted': bool,
                        'warming from pc': bool,
                        'warming from kb': bool,
                    },
                    'interlock status': {
                        'door 1 ok': bool,
                        'door 2 ok': bool,
                        'extern stop ok': bool,
                        'emergency stop ok': bool,
                    }
                }
        """
        sw_1 = self.read_status_word(1)
        res = {'power status': {
            'external pc control': bool(sw_1 & 128),
            'high voltage on':     bool(sw_1 & 64),
            'cooling system ok':   not bool(sw_1 & 32),
            'buffer battery ok':   not bool(sw_1 & 16),
            'current ma norm':     not bool(sw_1 & 8),
            'voltage kv norm':     not bool(sw_1 & 4),
        }}

        sw_6 = self.read_status_word(6)
        res['warming status'] = {
            'in progress':        bool(sw_6 & 8),
            'warming interrupted': bool(sw_6 & 4),
            'warming from pc':    bool(sw_6 & 2),
            'warming from kb':    bool(sw_6 & 1),
        }

        sw_30 = self.read_status_word(30)
        res['interlock status'] = {
            'door 1 ok':       not bool(sw_30 & 64),
            'door 2 ok':       not bool(sw_30 & 32),
            'extern stop ok':  not bool(sw_30 & 8),
            'emergency stop ok': not bool(sw_30 & 4),
        }

        return res

    # ------------------------------------------------------------------
    # Кэширующий таймер
    # ------------------------------------------------------------------

    def _check_cache(self, timer, value):
        """Вернуть закэшированное значение, если оно ещё актуально.

        Args:
            timer: Время последнего чтения (float) или None.
            value: Последнее прочитанное значение.

        Returns:
            Закэшированное значение, если не истёк CACHE_TTL, иначе None.
        """
        if timer is None or value is None:
            return None
        if time() - timer < CACHE_TTL:
            return value
        return None

    # ------------------------------------------------------------------
    # Чтение параметров
    # ------------------------------------------------------------------

    def get_nominal_voltage(self):
        """Прочитать установленное напряжение (кВ).

        Returns:
            float: Напряжение в кВ.

        Raises:
            RuntimeError: При ошибке от устройства.
        """
        if self.mock:
            return 40.0
        cached = self._check_cache(self.timer_voltage_nominal, self.last_voltage_nominal)
        if cached is not None:
            return cached

        logging.debug('Source.get_nominal_voltage() starting...')
        self.serial_port.write("VN\n".encode())
        answer = self.get_data_string()
        error = self.get_error()
        if error is not None:
            logging.error("Source.get_nominal_voltage() error: {}".format(error))
            raise RuntimeError("Source.get_nominal_voltage() error: {}".format(error))

        self.last_voltage_nominal = self.get_number(answer) / 1000.0
        self.timer_voltage_nominal = time()
        logging.debug('Source.get_nominal_voltage() finished.')
        return self.last_voltage_nominal

    def get_actual_voltage(self):
        """Прочитать фактическое напряжение (кВ).

        При ошибке от устройства возвращает последнее кешированное значение
        (или 0.0 если кеша нет) и логирует предупреждение — не бросает исключение.
        Это позволяет UI продолжать работу когда источник выключен или не готов.

        Returns:
            float: Напряжение в кВ (0.0 если устройство не отвечает корректно).
        """
        if self.mock:
            return 40.0
        cached = self._check_cache(self.timer_voltage_actual, self.last_voltage_actual)
        if cached is not None:
            return cached

        logging.debug('Source.get_actual_voltage() starting...')
        try:
            self.serial_port.write("VA\n".encode())
            answer = self.get_data_string()
            error = self.get_error()
            if error is not None:
                logging.warning(
                    "Source.get_actual_voltage() device error: %s (returning last cached or 0.0)",
                    error)
                return self.last_voltage_actual if self.last_voltage_actual is not None else 0.0

            self.last_voltage_actual = self.get_number(answer) / 1000.0
            self.timer_voltage_actual = time()
            logging.debug('Source.get_actual_voltage() finished.')
            return self.last_voltage_actual
        except Exception as e:
            logging.warning("Source.get_actual_voltage() exception: %s (returning 0.0)", e)
            return self.last_voltage_actual if self.last_voltage_actual is not None else 0.0

    def get_nominal_current(self):
        """Прочитать установленный ток (мА).

        Returns:
            float: Ток в мА.

        Raises:
            RuntimeError: При ошибке от устройства.
        """
        if self.mock:
            return 20.0
        cached = self._check_cache(self.timer_current_nominal, self.last_current_nominal)
        if cached is not None:
            return cached

        logging.debug('Source.get_nominal_current() starting...')
        self.serial_port.write("CN\n".encode())
        answer = self.get_data_string()
        error = self.get_error()
        if error is not None:
            logging.error("Source.get_nominal_current() error: {}".format(error))
            raise RuntimeError("Source.get_nominal_current() error: {}".format(error))

        self.last_current_nominal = self.get_number(answer) / 1000.0
        self.timer_current_nominal = time()
        logging.debug('Source.get_nominal_current() finished.')
        return self.last_current_nominal

    def get_actual_current(self):
        """Прочитать фактический ток (мА).

        При ошибке от устройства возвращает последнее кешированное значение
        (или 0.0 если кеша нет) и логирует предупреждение — не бросает исключение.

        Returns:
            float: Ток в мА (0.0 если устройство не отвечает корректно).
        """
        if self.mock:
            return 20.0
        cached = self._check_cache(self.timer_current_actual, self.last_current_actual)
        if cached is not None:
            return cached

        logging.debug('Source.get_actual_current() starting...')
        try:
            self.serial_port.write("CA\n".encode())
            answer = self.get_data_string()
            error = self.get_error()
            if error is not None:
                logging.warning(
                    "Source.get_actual_current() device error: %s (returning last cached or 0.0)",
                    error)
                return self.last_current_actual if self.last_current_actual is not None else 0.0

            self.last_current_actual = self.get_number(answer) / 1000.0
            self.timer_current_actual = time()
            logging.debug('Source.get_actual_current() finished.')
            return self.last_current_actual
        except Exception as e:
            logging.warning("Source.get_actual_current() exception: %s (returning 0.0)", e)
            return self.last_current_actual if self.last_current_actual is not None else 0.0

    def get_nominal_power(self):
        """Прочитать установленную мощность (Вт).

        Returns:
            float: Мощность в Вт.

        Raises:
            RuntimeError: При ошибке от устройства.
        """
        if self.mock:
            return 800.0
        cached = self._check_cache(self.timer_power_nominal, self.last_power_nominal)
        if cached is not None:
            return cached

        logging.debug('Source.get_nominal_power() starting...')
        self.serial_port.write("PN\n".encode())
        answer = self.get_data_string()
        error = self.get_error()
        if error is not None:
            logging.error("Source.get_nominal_power() error: {}".format(error))
            raise RuntimeError("Source.get_nominal_power() error: {}".format(error))

        self.last_power_nominal = self.get_number(answer) / 1000.0
        self.timer_power_nominal = time()
        logging.debug('Source.get_nominal_power() finished.')
        return self.last_power_nominal

    def get_actual_power(self):
        """Прочитать фактическую мощность (Вт).

        При ошибке от устройства возвращает последнее кешированное значение
        (или 0.0 если кеша нет) и логирует предупреждение — не бросает исключение.

        Returns:
            float: Мощность в Вт (0.0 если устройство не отвечает корректно).
        """
        if self.mock:
            return 800.0
        cached = self._check_cache(self.timer_power_actual, self.last_power_actual)
        if cached is not None:
            return cached

        logging.debug('Source.get_actual_power() starting...')
        try:
            self.serial_port.write("PA\n".encode())
            answer = self.get_data_string()
            error = self.get_error()
            if error is not None:
                logging.warning(
                    "Source.get_actual_power() device error: %s (returning last cached or 0.0)",
                    error)
                return self.last_power_actual if self.last_power_actual is not None else 0.0

            self.last_power_actual = self.get_number(answer) / 1000.0
            self.timer_power_actual = time()
            logging.debug('Source.get_actual_power() finished.')
            return self.last_power_actual
        except Exception as e:
            logging.warning("Source.get_actual_power() exception: %s (returning 0.0)", e)
            return self.last_power_actual if self.last_power_actual is not None else 0.0

    # ------------------------------------------------------------------
    # Установка параметров
    # ------------------------------------------------------------------

    def set_voltage(self, voltage):
        """Установить напряжение.

        Args:
            voltage (float): Напряжение в кВ.

        Raises:
            RuntimeError: При ошибке от устройства.
        """
        if self.mock:
            return
        logging.debug('Source.set_voltage() starting...')
        command = "SV:{}\n".format(str(int(round(voltage * 1000))).zfill(6)).encode()
        self.serial_port.write(command)

        error = self.get_error()
        if error is not None:
            if error['code'] == 106:
                logging.info('Source.set_voltage: warm-up required')
                self.warmup()
                self.on_high_voltage()
            else:
                logging.error("Source.set_voltage() error: {}".format(error))
                raise RuntimeError("Source.set_voltage() error: {}".format(error))

        self.wait_for_voltage()
        logging.debug('Source.set_voltage() finished.')

    def set_current(self, current):
        """Установить ток.

        Args:
            current (float): Ток в мА.

        Raises:
            RuntimeError: При ошибке от устройства.
        """
        if self.mock:
            return
        logging.debug('Source.set_current() starting...')
        command = "SC:{}\n".format(str(int(round(current * 1000))).zfill(6)).encode()
        self.serial_port.write(command)

        error = self.get_error()
        if error is not None:
            logging.error("Source.set_current() error: {}".format(error))
            raise RuntimeError("Source.set_current() error: {}".format(error))

        self.wait_for_current()
        logging.debug('Source.set_current() finished.')

    def set_power(self, power):
        """Установить мощность.

        Args:
            power (float): Мощность в Вт.

        Raises:
            RuntimeError: При ошибке от устройства.
        """
        if self.mock:
            return
        logging.debug('Source.set_power() starting...')
        command = "SP:{}\n".format(str(int(round(power * 1000))).zfill(6)).encode()
        self.serial_port.write(command)

        error = self.get_error()
        if error is not None:
            logging.error("Source.set_power() error: {}".format(error))
            raise RuntimeError("Source.set_power() error: {}".format(error))

        logging.debug('Source.set_power() finished.')

    # ------------------------------------------------------------------
    # Идентификация
    # ------------------------------------------------------------------

    def get_id(self):
        """Прочитать идентификатор генератора (команда ID).

        Результат кэшируется до следующего вызова.

        Returns:
            str: Строка идентификатора.

        Raises:
            RuntimeError: При ошибке от устройства.
        """
        if self.mock:
            return "Mock 40 20"
        if self.device_id is not None:
            return self.device_id

        logging.debug('Source.get_id() starting...')
        self.serial_port.write("ID\n".encode())
        answer = self.get_data_string()
        error = self.get_error()
        if error is not None:
            logging.error("Source.get_id() error: {}".format(error))
            raise RuntimeError("Source.get_id() error: {}".format(error))

        self.device_id = answer
        logging.debug('Source.get_id() finished.')
        return self.device_id

    def get_tube_name(self):
        """Прочитать наименование трубки (команда XT).

        Результат кэшируется до следующего вызова.

        Returns:
            str: Наименование трубки.

        Raises:
            RuntimeError: При ошибке от устройства.
        """
        if self.mock:
            return "Mock Tube 40kV 20mA"
        if self.tube_name is not None:
            return self.tube_name

        logging.debug('Source.get_tube_name() starting...')
        self.serial_port.write("XT\n".encode())
        answer = self.get_data_string()
        error = self.get_error()
        if error is not None:
            logging.error("Source.get_tube_name() error: {}".format(error))
            raise RuntimeError("Source.get_tube_name() error: {}".format(error))

        self.tube_name = answer
        logging.debug('Source.get_tube_name() finished.')
        return self.tube_name

    # ------------------------------------------------------------------
    # Ошибки
    # ------------------------------------------------------------------

    def get_error(self):
        """Прочитать текущий код ошибки (SR:12).

        Returns:
            dict | None: Словарь ``{'code': int, 'message': str}``
            или None если ошибок нет.
        """
        self.serial_port.write("SR:12\n".encode())
        answer = self.get_data_string()
        try:
            error_code = int(answer[1:])
        except ValueError:
            logging.warning("Source.get_error(): cannot parse answer: %r", answer)
            return None

        if error_code != 0:
            message = self.STATUS_STRINGS.get(error_code, "Unknown error code {}".format(error_code))
            return {'code': error_code, 'message': message}
        return None

    def reset_error(self, code):
        """Сбросить ошибку (команда RE:nn).

        Args:
            code (int): Код ошибки для сброса.

        Raises:
            RuntimeError: Если после сброса ошибка не исчезла.
        """
        if self.mock:
            return
        logging.debug('Source.reset_error(%d) starting...', code)
        self.serial_port.write("RE:{}\n".format(str(code).zfill(2)).encode())
        sleep(0.2)
        error = self.get_error()
        if error is not None and error['code'] == code:
            logging.error("Source.reset_error(): error %d persists after reset", code)
            raise RuntimeError("Source.reset_error(): error {} persists after reset".format(code))
        logging.debug('Source.reset_error(%d) finished.', code)

    # ------------------------------------------------------------------
    # Вспомогательные методы
    # ------------------------------------------------------------------

    def get_data_string(self):
        """Прочитать одну строку ответа из serial-порта.

        Протокол: ответ начинается с '*', заканчивается '\\r'.

        Returns:
            str: Строка ответа без завершающих символов.
        """
        sleep(0.2)
        line = self.serial_port.read_until(b'\r')
        return line.decode().strip()

    @staticmethod
    def get_number(line):
        """Преобразовать строку ответа вида '*nnnnn' в целое число.

        Args:
            line (str): Строка ответа, начинающаяся с '*'.

        Returns:
            int: Числовое значение.
        """
        return int(line[1:])

    # ------------------------------------------------------------------
    # Интерфейс get_state / set_state
    # ------------------------------------------------------------------

    def get_state(self, options=None):
        """Прочитать состояние устройства по списку параметров.

        Args:
            options (list | str | None): Список запрашиваемых параметров.
                По умолчанию читаются все доступные параметры.
                Допустимые значения: ``'is_on_high_voltage'``, ``'id'``,
                ``'tube_name'``, ``'actual_voltage'``, ``'nominal_voltage'``,
                ``'actual_current'``, ``'nominal_current'``,
                ``'actual_power'``, ``'nominal_power'``,
                ``'status'``, ``'last_error'``.

        Returns:
            dict: Словарь ``{параметр: значение}``.
        """
        if options is None:
            options = [
                'is_on_high_voltage', 'id', 'tube_name',
                'actual_voltage', 'nominal_voltage',
                'actual_current', 'nominal_current',
                'actual_power', 'nominal_power',
                'status', 'last_error',
            ]
        if not isinstance(options, (list, tuple)):
            options = [options]

        handlers = {
            'is_on_high_voltage': self.is_on_high_voltage,
            'id':                 self.get_id,
            'tube_name':          self.get_tube_name,
            'actual_voltage':     self.get_actual_voltage,
            'nominal_voltage':    self.get_nominal_voltage,
            'actual_current':     self.get_actual_current,
            'nominal_current':    self.get_nominal_current,
            'actual_power':       self.get_actual_power,
            'nominal_power':      self.get_nominal_power,
            'status':             self.get_status,
            'last_error':         self.get_error,
        }

        res = {}
        for option in options:
            if option in handlers:
                res[option] = handlers[option]()
            else:
                res[option] = {'error': 'Unsupported option: {}'.format(option)}
        return res

    def set_state(self, options_dict):
        """Установить параметры устройства.

        Args:
            options_dict (dict): Словарь ``{параметр: значение}``.
                Поддерживаемые ключи: ``'set_voltage'`` (кВ),
                ``'set_current'`` (мА), ``'set_power'`` (Вт),
                ``'high_voltage'`` (bool).

        Returns:
            dict: Словарь с запрошенными и результирующими значениями.
        """
        res = {}
        handlers = {
            'set_voltage': self.set_voltage,
            'set_current': self.set_current,
            'set_power':   self.set_power,
        }

        for option, value in options_dict.items():
            if option in handlers:
                res[option] = handlers[option](value)
            elif option == 'high_voltage':
                if value is True:
                    res[option] = self.on_high_voltage()
                elif value is False:
                    res[option] = self.off_high_voltage()
                else:
                    res[option] = {
                        'error': 'high_voltage must be True or False, got: {}'.format(value)
                    }
            else:
                res[option] = {'error': 'Unsupported option: {}'.format(option)}

        return {'requested_state': options_dict, 'result': res}
