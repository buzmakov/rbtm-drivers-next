import serial
import logging
import threading
from time import sleep, time
import atexit

TIMEOUT = 10
CACHE_TTL = 3           # секунды: кэшировать значение не дольше
                        # UI опрашивает каждые 3 сек, кадры при съёмке — чаще
WARMUP_TIMEOUT = 1800   # максимальное время прогрева — 30 минут

CL_SETTLE_DELAY = 0.5       # с: пауза после CL, пока генератор снимет сообщение
HV_SETTLE_DELAY = 1.0       # с: пауза после HV:0/HV:1 перед следующей командой
WARMUP_POLL_INTERVAL = 5    # с: период опроса состояния во время прогрева
WAIT_TIMEOUT = 10           # с: ожидание включения ВН / стабилизации kV и mA
WAIT_POLL_INTERVAL = 1      # с: период опроса в _wait_until()

# Коды SR:12, означающие разомкнутую цепь блокировок (руководство §8.5.1).
# Именно они, а не биты SR:30, сообщают о дверях и аварийном останове.
INTERLOCK_ERROR_CODES = (
    35,  # Interlock open
    43,  # Extern STOP
    46,  # EMERGENCY-STOP
    63,  # Door contact 1 and 2 open
    64,  # Door contact 1 open
    65,  # Door contact 2 open
)

# Единственный белый список «неошибок»: коды SR:12, которыми генератор сообщает
# о своём состоянии или просит действия оператора. Используется ВЕЗДЕ, где
# нужно отличить информационное сообщение от настоящего отказа.
# Значения проверены по руководству §8.5.1 (таблица кодов строки ошибок).
INFORMATIONAL_CODES = {
    76:  "Stand-By — генератор в режиме ожидания",
    106: "Warm-up necessary — требуется прогрев трубки",
    109: "Warm-up! 0=No — генератор спрашивает, выполнять ли прогрев",
    118: "Push START button — генератор ждёт START (по RS-232 это HV:1)",
    119: "Warm-up program completed. ENTER — прогрев завершён, сбросить CL",
    # 120 в таблице руководства отсутствует (после 119 сразу 121); код
    # наблюдался прежней версией драйвера во время прогрева как
    # «Warm-up program running» — оставлен информационным, проверить на железе.
    120: "Warm-up program running — прогрев идёт (нет в руководстве)",
    121: "Observe warm-up instructions! ENTER — подтвердить инструкции",
}

# Коды, при которых нужно выполнить прогрев (подмножество информационных).
WARMUP_REQUIRED_CODES = (106, 109)


class SourceCommunicationError(RuntimeError):
    """Обмен с генератором не состоялся (таймаут, порт закрыт, мусор в ответе).

    Отличается от «генератор ответил кодом ошибки»: в последнем случае
    методы возвращают/бросают обычный ``RuntimeError`` с кодом SR:12.
    Наследуется от ``RuntimeError`` — прежние ``except RuntimeError``
    у вызывающего кода продолжают работать.
    """


class SourceBusyError(SourceCommunicationError):
    """Порт занят прогревом: обмен сейчас невозможен, состояние неизвестно.

    Отдельный подкласс, чтобы вызывающий код мог отличить «идёт прогрев»
    от «генератор умер», но обработчики ``SourceCommunicationError``
    ловили и его.
    """


# Реестр долгоживущих экземпляров: один HWSource на порт в процессе.
# Каждое открытие/закрытие serial-порта дёргает линии DTR/RTS на RS-232
# ISOVOLT 3003, а пересоздание HWTomograph через RedisProxy (при любой
# ошибке инициализации других устройств) раньше открывало порт заново
# при каждой попытке — см. HWSource.get_shared().
_shared_sources = {}
_shared_sources_lock = threading.Lock()


class HWSource(object):
    """Драйвер рентгеновского источника ISOVOLT 3003 (Seifert/GE).

    Управление через RS-232 (9600 8N1). Протокол ASCII: команда + '\\r\\n',
    ответ начинается с '*', заканчивается '\\r'. Коды ошибок читаются
    командой SR:12.

    **Документация устройства:** vendor/docs/ISOVOLT_3003_manual_rus.pdf

    **Важные моменты из документации:**
    - Команда **`CL`** (Clear) — единственная команда для сброса ошибки 119.
      Не путать с `RE:19` — такой команды не существует в протоколе!
    - После прогрева (`WU:4,NNN`) устройство выдаёт ошибку 119. Нужно
      отправить `CL`, затем `HV:1` для включения высокого напряжения.
    - Если прогрев прерван, даётся 3 попытки (код 116 = неудача).
    - Статус прогрева: SR:06 биты 1/2/4/8 (вкл с клавиатуры/PC, прерван, в процессе).
    - Статус ВН: SR:01 бит 6 (1=вкл), бит 4/8 (0=напряжение/ток стабилизированы).
    - Двери и аварийный стоп — это НЕ биты SR:30, а коды ошибки SR:12:
      35 (Interlock open), 43 (Extern STOP), 46 (EMERGENCY-STOP),
      63/64/65 (двери 1+2 / 1 / 2 разомкнуты). В SR:30 лежат режим работы,
      вид стабилизации и состояние внешней лампы (руководство §8.5).
    """

    # Коды сообщений строки ошибок (SR:12), руководство §8.5.1.
    # Нумерация начинается с 033 — кодов 1–32 в протоколе нет.
    STATUS_STRINGS = {
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
        self.timer_current_nominal = None
        self.last_voltage_nominal = None
        self.last_current_nominal = None

        self.device_id = None
        self.tube_name = None

        # Мьютекс: только один поток одновременно работает с serial-портом.
        # RLock позволяет одному потоку многократно захватывать блокировку
        # (например, warmup() вызывает get_error() под той же блокировкой).
        self._port_lock = threading.RLock()
        # Флаг: True пока идёт прогрев. UI-опросы видят его и не лезут в порт,
        # возвращая последнее кэшированное значение — иначе вклиниваются
        # между командами warmup() и сбивают протокол.
        self._warming_up = threading.Event()
        # Поток, выполняющий прогрев: ему самому флаг не мешает работать
        # с портом (см. _busy_warming_up()).
        self._warming_thread = None

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
                dsrdtr=True,  # DTR=True: требуется ISOVOLT 3003 для активации интерфейса
            )
            sleep(0.5)  # пауза для инициализации устройства

        logging.info('Source.__init__: port %s opened (mock=%s)', tty_name, mock)
        atexit.register(self.close)

    @classmethod
    def get_shared(cls, tty_name, mock=False):
        """Вернуть долгоживущий экземпляр драйвера для порта (один на процесс).

        Повторные вызовы с тем же ``tty_name`` возвращают уже открытый
        объект и НЕ переоткрывают serial-порт. Если экземпляр был явно
        закрыт через ``close()``, создаётся новый.

        Args:
            tty_name: Путь к serial-порту, например '/dev/ttyUSB0'.
            mock: Если True — работает без реального устройства.

        Returns:
            HWSource: Общий экземпляр драйвера.
        """
        key = (tty_name, bool(mock))
        with _shared_sources_lock:
            instance = _shared_sources.get(key)
            if instance is None or not instance.is_open():
                instance = cls(tty_name, mock=mock)
                _shared_sources[key] = instance
            else:
                logging.debug('Source.get_shared(): reusing open instance for %s', tty_name)
            return instance

    def _busy_warming_up(self):
        """True, если идёт прогрев и вызов пришёл из другого потока.

        Все методы, работающие с портом, спрашивают это вместо того, чтобы
        ждать ``_port_lock``: прогрев длится до получаса, и UI-опрос не
        должен на нём висеть. Поток самого прогрева получает False и
        работает с портом обычным образом.
        """
        return (self._warming_up.is_set()
                and threading.current_thread() is not self._warming_thread)

    def _refuse_if_warming(self, where):
        """Бросить SourceBusyError, если порт занят прогревом."""
        if self._busy_warming_up():
            raise SourceBusyError(
                "{}: warm-up in progress, port is busy".format(where))

    def is_open(self):
        """Вернуть True, если serial-порт открыт (в mock-режиме — всегда True)."""
        if self.mock:
            return True
        return self.serial_port is not None and self.serial_port.is_open

    def close(self):
        """Закрыть serial-порт (повторный вызов безопасен)."""
        if self.mock:
            return
        if self.serial_port is not None and self.serial_port.is_open:
            logging.info('Source.close(): closing port %s', self.tty_name)
            self.serial_port.close()

    # ------------------------------------------------------------------
    # Ожидание готовности
    # ------------------------------------------------------------------

    def _wait_until(self, predicate, description, timeout=WAIT_TIMEOUT):
        """Ждать, пока ``predicate()`` не вернёт True, но не дольше ``timeout``.

        Исключение из предиката трактуется как «ещё не готово»: генератор
        во время переходных процессов может не отвечать, ронять из-за этого
        включение ВН не нужно.

        Args:
            predicate (callable): Проверка, возвращающая bool.
            description (str): Что именно ждём — попадает в лог.
            timeout (float): Предел ожидания, с.

        Returns:
            bool: True — дождались, False — вышло время.
        """
        if self.mock:
            return True
        deadline = time() + timeout
        while True:
            try:
                if predicate():
                    return True
            except Exception as e:
                logging.warning("Source._wait_until(%s): check failed: %s",
                                description, e)
            if time() >= deadline:
                logging.warning("Source._wait_until(%s): not ready after %.0fs",
                                description, timeout)
                return False
            sleep(WAIT_POLL_INTERVAL)

    def wait_for_high_voltage(self):
        """Ожидать включения высокого напряжения (до ``WAIT_TIMEOUT`` секунд)."""
        return self._wait_until(self.is_on_high_voltage, 'high voltage on')

    def wait_for_high_voltage_down(self):
        """Ожидать выключения высокого напряжения (до ``WAIT_TIMEOUT`` секунд)."""
        return self._wait_until(lambda: not self.is_on_high_voltage(),
                                'high voltage off')

    def wait_for_voltage(self):
        """Ожидать стабилизации напряжения (SR:01 бит 2 = 0)."""
        return self._wait_for_power_flag('voltage kv norm', 'voltage stabilized')

    def wait_for_current(self):
        """Ожидать стабилизации тока (SR:01 бит 3 = 0)."""
        return self._wait_for_power_flag('current ma norm', 'current stabilized')

    def _wait_for_power_flag(self, flag, description):
        """Ждать флаг из ``get_status()['power status']``, если ВН включено."""
        if self.mock:
            return True
        try:
            if not self.is_on_high_voltage():
                return True
        except Exception as e:
            logging.warning("Source._wait_for_power_flag(%s): "
                            "is_on_high_voltage failed: %s, skipping wait",
                            description, e)
            return True
        return self._wait_until(
            lambda: self.get_status()['power status'][flag], description)

    # ------------------------------------------------------------------
    # Управление высоким напряжением
    # ------------------------------------------------------------------

    def on_high_voltage(self):
        """Включить высокое напряжение.

        Если устройство требует прогрева (коды 106 или 109), выполняет
        warmup() и повторяет попытку включения (не более 3 раз).
        Информационные коды (``INFORMATIONAL_CODES``) отказом не считаются.

        Raises:
            SourceCommunicationError: Если генератор не отвечает — метод
                НЕ рапортует успех при мёртвом порте.
            RuntimeError: При ошибке от устройства или исчерпании попыток.
        """
        if self.mock:
            return
        self._refuse_if_warming("Source.on_high_voltage()")
        logging.info('Source.on_high_voltage() starting...')
        for attempt in range(3):
            # HV:1 и чтение SR:12 — одна транзакция; при мёртвом порте
            # бросается SourceCommunicationError, успех не рапортуется.
            error = self._send_and_read_error("HV:1")
            logging.info('Source.on_high_voltage(): error after HV:1 = %r', error)
            if error is None:
                break
            if error['code'] in WARMUP_REQUIRED_CODES:
                logging.info('Source.on_high_voltage: warm-up required (attempt %d)', attempt + 1)
                self.warmup(voltage=self.last_voltage_nominal)
            elif error['code'] in (118, 119, 121):
                # Генератор ждёт подтверждения (ENTER/START) — по RS-232 это CL,
                # после чего повторяем HV:1.
                logging.info("Source.on_high_voltage(): code %d (%s) — sending CL and retrying",
                             error['code'], INFORMATIONAL_CODES[error['code']])
                self._transact("CL", expect_answer=False, read_error=False)
                sleep(CL_SETTLE_DELAY)
            elif error['code'] in INFORMATIONAL_CODES:
                logging.info("Source.on_high_voltage(): informational code %d (%s)",
                             error['code'], INFORMATIONAL_CODES[error['code']])
                break
            else:
                logging.error("Source.on_high_voltage() error: {}".format(error))
                raise RuntimeError("Source.on_high_voltage() error: {}".format(error))
        else:
            raise RuntimeError("Source.on_high_voltage(): warm-up required after 3 attempts")

        logging.info('Source.on_high_voltage(): waiting for HV to stabilize...')
        self.wait_for_high_voltage()
        self.wait_for_current()
        self.wait_for_voltage()
        logging.info('Source.on_high_voltage() finished.')

    def off_high_voltage(self):
        """Выключить высокое напряжение.

        Выключение выполняется и во время прогрева (это команда безопасности):
        ``HV:0`` уходит в порт, а невозможность прочитать SR:12 из-за прогрева
        отказом не считается.

        Raises:
            RuntimeError: При ошибке от устройства.
            SourceCommunicationError: Генератор не отвечает.
        """
        if self.mock:
            return
        # INFO, а не DEBUG: выключение ВН должно быть видно в логах сервера
        # наравне с on_high_voltage() — иначе невозможно отличить команду
        # драйвера от самопроизвольного отключения генератора.
        logging.info('Source.off_high_voltage() starting...')
        with self._port_lock:
            self._write_command("HV:0")
            logging.info('Source.off_high_voltage(): HV:0 sent')
        try:
            self._check_error(self.get_error(), "Source.off_high_voltage()")
        except SourceBusyError:
            logging.warning(
                "Source.off_high_voltage(): warm-up in progress, SR:12 not read "
                "(HV:0 has been sent)")

        self.wait_for_high_voltage_down()
        logging.info('Source.off_high_voltage() finished.')

    def is_on_high_voltage(self):
        """Вернуть True, если высокое напряжение включено.

        При ошибке связи с устройством (например, во время прогрева)
        возвращает False и логирует предупреждение — не бросает исключение.
        Во время прогрева (_busy_warming_up()) сразу возвращает False,
        чтобы не вклиниваться в монопольный доступ warmup() к порту.
        """
        logging.debug('Source.is_on_high_voltage() starting...')
        if self._busy_warming_up():
            return False
        try:
            status = self.get_status()
            result = status['power status']['high voltage on']
            logging.debug('Source.is_on_high_voltage() finished.')
            return result
        except Exception as e:
            logging.warning("Source.is_on_high_voltage(): failed to read status: %s (returning False)", e)
            return False

    def warmup(self, voltage=None):
        """Запустить программу прогрева трубки (``WU``).

        Прогрев идёт от нескольких минут до получаса (лимит —
        ``WARMUP_TIMEOUT``), поэтому порт монопольно не захватывается:
        под ``_port_lock`` выполняется каждая отдельная транзакция, между
        опросами блокировка отпускается. На время прогрева взведён флаг
        ``_warming_up``: остальные методы видят его (``_busy_warming_up()``)
        и возвращают известное состояние вместо ожидания на блокировке.

        Args:
            voltage (float | None): Напряжение прогрева в кВ.
                Если None — берётся кэш номинала или читается с устройства.

        Raises:
            RuntimeError: При ошибке включения HV или превышении таймаута.
            SourceCommunicationError: Генератор не ответил на команды запуска.
        """
        if self.mock:
            return
        logging.info('Source.warmup() starting... voltage=%s', voltage)
        self._warming_thread = threading.current_thread()
        self._warming_up.set()
        try:
            # ── Запуск прогрева: одна атомарная последовательность ──────────
            with self._port_lock:
                # Определяем напряжение для прогрева.
                if voltage is None:
                    voltage = self.last_voltage_nominal
                if voltage is None:
                    try:
                        voltage = self.get_nominal_voltage()
                    except RuntimeError:
                        logging.warning(
                            "Source.warmup(): cannot read nominal voltage, "
                            "using WU:4,000")
                        voltage = 0

                # Выключаем HV перед прогревом
                logging.info("Source.warmup(): sending HV:0...")
                self._write_command("HV:0")
                sleep(HV_SETTLE_DELAY)

                # WU:4,NNN — прогрев по нерабочему интервалу из часов генератора
                # (руководство §8.2: x=4 — «прогрев через RTC»), NNN — тестовое
                # напряжение в кВ.
                logging.info("Source.warmup(): sending WU:4,%03d...", int(round(voltage)))
                self._write_command("WU:4,{}".format(
                    str(int(round(voltage))).zfill(3)))

                # Читаем ошибку
                self._write_command("SR:12")
                error_code = self._parse_error_code(self.get_data_string())
                if error_code and error_code not in INFORMATIONAL_CODES:
                    error = {'code': error_code, 'message': self.describe_code(error_code)}
                    logging.error("Source.warmup() WU error: {}".format(error))
                    raise RuntimeError("Source.warmup() WU error: {}".format(error))
                if error_code == 119:
                    logging.info("Source.warmup(): warm-up already completed (error 119), clearing")
                    self._write_command("CL")
                    sleep(CL_SETTLE_DELAY)
                    # Не выходим — HV был выключен выше, включится в конце

                # HV:1 = программный START прогрева
                logging.info("Source.warmup(): sending HV:1 to start warmup...")
                self._write_command("HV:1")

                self._write_command("SR:12")
                error_code = self._parse_error_code(self.get_data_string())
                if error_code and error_code not in INFORMATIONAL_CODES:
                    error = {'code': error_code, 'message': self.describe_code(error_code)}
                    logging.error("Source.warmup() HV error: {}".format(error))
                    raise RuntimeError("Source.warmup() HV error: {}".format(error))

            # Пауза перед первым опросом: биты SW6 генератор поднимает не сразу.
            sleep(WARMUP_POLL_INTERVAL)
            logging.info("Source.warmup(): polling status...")

            # ── Опрос до завершения: блокировка берётся на одну транзакцию ───
            warmup_start = time()
            last_log_elapsed = 0
            while True:
                elapsed = time() - warmup_start
                if elapsed > WARMUP_TIMEOUT:
                    raise RuntimeError(
                        "Source.warmup(): timeout after {:.0f}s".format(elapsed))

                if int(elapsed) - last_log_elapsed >= WARMUP_POLL_INTERVAL:
                    logging.info("Source.warmup(): elapsed=%.0fs polling...", elapsed)
                    last_log_elapsed = int(elapsed)

                try:
                    if self._warmup_poll_once(elapsed):
                        break
                except Exception as e:
                    if int(elapsed) % 30 == 0:
                        logging.warning(
                            "Source.warmup(): elapsed=%.0fs status read failed: %s (continuing)",
                            elapsed, e)
                sleep(WARMUP_POLL_INTERVAL)

            # ── Хвост: включаем HV, который был выключен в начале ────────────
            # Раньше эти две команды шли вне блокировки — параллельный опрос
            # мог вклиниться между HV:1 и SR:12 и получить чужой ответ.
            with self._port_lock:
                logging.info("Source.warmup(): turning HV ON after warm-up...")
                self._write_command("HV:1")
                sleep(HV_SETTLE_DELAY)
                self._write_command("SR:12")
                err_code = self._parse_error_code(self.get_data_string())
            if err_code and err_code not in INFORMATIONAL_CODES:
                error = {'code': err_code, 'message': self.describe_code(err_code)}
                logging.error("Source.warmup() post-warmup HV error: {}".format(error))
                raise RuntimeError("Source.warmup() post-warmup HV error: {}".format(error))
            logging.info("Source.warmup(): HV ON after warm-up confirmed")
        finally:
            self._warming_up.clear()
            self._warming_thread = None

        # Ждём стабилизации напряжения и тока — аналогично on_high_voltage().
        # Уже без флага прогрева, чтобы wait_* действительно читали порт.
        self.wait_for_high_voltage()
        self.wait_for_current()
        self.wait_for_voltage()
        logging.info("Source.warmup(): warm-up sequence fully completed")
        logging.debug('Source.warmup() finished.')

    def _warmup_poll_once(self, elapsed):
        """Один опрос состояния прогрева под ``_port_lock``.

        Returns:
            bool: True, если прогрев завершён и цикл можно прекращать.
        """
        with self._port_lock:
            self._write_command("SR:01")
            sw_1 = self.get_number(self.get_data_string())

            self._write_command("SR:06")
            sw_6 = self.get_number(self.get_data_string())

            in_progress = bool(sw_6 & 8)
            from_pc = bool(sw_6 & 2)
            from_kb = bool(sw_6 & 1)
            hv_norm = not bool(sw_1 & 4)

            logging.info(
                "Source.warmup(): elapsed=%.0fs in_progress=%s from_pc=%s from_kb=%s hv_norm=%s",
                elapsed, in_progress, from_pc, from_kb, hv_norm)

            if in_progress or from_kb or from_pc:
                return False

            # Прогрев не значится активным — выясняем, почему.
            self._write_command("SR:12")
            err_code = self._parse_error_code(self.get_data_string())
            if err_code == 109:
                logging.info(
                    "Source.warmup(): status=no warmup but error 109 persists — waiting")
                return False
            # Сбрасываем код 119 "Warm-up program completed. ENTER"
            if err_code == 119:
                logging.info("Source.warmup(): clearing error 119 (warm-up completed)")
                self._write_command("CL")
                sleep(CL_SETTLE_DELAY)
            logging.info("Source.warmup(): warm-up finished.")
            return True

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
        if self.mock:
            return 0
        self._refuse_if_warming("Source.read_status_word()")
        if word_number not in [1, 6, 12, 30]:
            logging.error("Source.read_status_word(): unknown word number %d", word_number)

        answer, _ = self._transact("SR:{}".format(str(word_number).zfill(2)),
                                   read_error=False)
        logging.debug('Source.read_status_word(%d) finished.', word_number)
        return self.get_number(answer)

    def get_status(self):
        """Прочитать статус устройства (слова состояния SR:01 и SR:06).

        Во время прогрева (``_warming_up`` взведён) в порт не лезет и
        возвращает известное состояние: прогрев идёт, ВН выключено.

        Двери/аварийный стоп здесь не возвращаются: в SR:30 их нет,
        они приходят кодами ошибки SR:12 (35, 43, 46, 63–65) — см. get_error().

        Raises:
            SourceCommunicationError: Если обмен не состоялся. Раньше в этом
                случае возвращалось ``in progress: True`` — смерть порта
                выглядела как прогрев.

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
                }
        """
        if self.mock:
            return {
                'power status': {
                    'external pc control': True,
                    'high voltage on': False,
                    'cooling system ok': True,
                    'buffer battery ok': True,
                    'current ma norm': True,
                    'voltage kv norm': True,
                },
                'warming status': {
                    'in progress': False,
                    'warming interrupted': False,
                    'warming from pc': False,
                    'warming from kb': False,
                },
            }
        # Во время прогрева не лезем в порт. Это не выдумка: флаг взведён
        # самим warmup(), значит прогрев действительно идёт, а ВН выключено.
        if self._busy_warming_up():
            logging.debug("Source.get_status(): warming up in progress — returning known state")
            return {
                'power status': {
                    'external pc control': False,
                    'high voltage on': False,
                    'cooling system ok': True,
                    'buffer battery ok': True,
                    'current ma norm': False,
                    'voltage kv norm': False,
                },
                'warming status': {
                    'in progress': True,
                    'warming interrupted': False,
                    'warming from pc': False,
                    'warming from kb': False,
                },
            }
        try:
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

            return res
        except SourceCommunicationError:
            raise
        except Exception as e:
            # Сбой связи — это НЕ «идёт прогрев»: раньше умерший порт
            # выглядел в UI как бесконечный прогрев. Состояние неизвестно,
            # говорим об этом явно.
            raise SourceCommunicationError(
                "Source.get_status(): communication failed: {}".format(e))

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
        if self._busy_warming_up():
            # Во время прогрева в порт не лезем: отдаём последнее
            # известное значение, даже если истёк CACHE_TTL.
            if self.last_voltage_nominal is not None:
                return self.last_voltage_nominal
            raise SourceBusyError(
                "Source.get_nominal_voltage(): warm-up in progress, no cached value")

        logging.debug('Source.get_nominal_voltage() starting...')
        answer, error = self._transact("VN")
        self._check_error(error, "Source.get_nominal_voltage()")

        self.last_voltage_nominal = self.get_number(answer) / 1000.0
        self.timer_voltage_nominal = time()
        logging.debug('Source.get_nominal_voltage() finished.')
        return self.last_voltage_nominal

    def get_actual_voltage(self):
        """Прочитать фактическое напряжение (кВ).

        Всегда читает свежее значение с устройства (кэширование убрано,
        чтобы избежать показа устаревших значений после изменения напряжения).
        Во время прогрева (_busy_warming_up()) возвращает 0.0,
        чтобы не вклиниваться в монопольный доступ warmup() к порту.

        Returns:
            float: Напряжение в кВ (0.0 если устройство не отвечает корректно).
        """
        if self.mock:
            return 40.0
        # Если идёт прогрев — не лезем в порт
        if self._busy_warming_up():
            return 0.0

        logging.debug('Source.get_actual_voltage() starting...')
        try:
            answer, error = self._transact("VA")
            if error is not None and error['code'] not in INFORMATIONAL_CODES:
                logging.warning(
                    "Source.get_actual_voltage() device error: %s (returning 0.0)",
                    error)
                return 0.0

            voltage = self.get_number(answer) / 1000.0
            logging.debug('Source.get_actual_voltage() finished.')
            return voltage
        except Exception as e:
            logging.warning("Source.get_actual_voltage() exception: %s (returning 0.0)", e)
            return 0.0

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
        if self._busy_warming_up():
            # Во время прогрева в порт не лезем: отдаём последнее
            # известное значение, даже если истёк CACHE_TTL.
            if self.last_current_nominal is not None:
                return self.last_current_nominal
            raise SourceBusyError(
                "Source.get_nominal_current(): warm-up in progress, no cached value")

        logging.debug('Source.get_nominal_current() starting...')
        answer, error = self._transact("CN")
        self._check_error(error, "Source.get_nominal_current()")

        self.last_current_nominal = self.get_number(answer) / 1000.0
        self.timer_current_nominal = time()
        logging.debug('Source.get_nominal_current() finished.')
        return self.last_current_nominal

    def get_actual_current(self):
        """Прочитать фактический ток (мА).

        Всегда читает свежее значение с устройства (кэширование убрано,
        чтобы избежать показа устаревших значений).
        Во время прогрева (_busy_warming_up()) возвращает 0.0.

        Returns:
            float: Ток в мА (0.0 если устройство не отвечает корректно).
        """
        if self.mock:
            return 20.0
        if self._busy_warming_up():
            return 0.0

        logging.debug('Source.get_actual_current() starting...')
        try:
            answer, error = self._transact("CA")
            if error is not None and error['code'] not in INFORMATIONAL_CODES:
                logging.warning(
                    "Source.get_actual_current() device error: %s (returning 0.0)",
                    error)
                return 0.0

            current = self.get_number(answer) / 1000.0
            logging.debug('Source.get_actual_current() finished.')
            return current
        except Exception as e:
            logging.warning("Source.get_actual_current() exception: %s (returning 0.0)", e)
            return 0.0

    # ------------------------------------------------------------------
    # Установка параметров
    # ------------------------------------------------------------------

    def set_voltage(self, voltage):
        """Установить напряжение.

        Команда ``SV:NNNNNN`` — напряжение в вольтах (кВ × 1000), см. пример
        в руководстве §8.4: 123 кВ → ``SV:123000``.

        Args:
            voltage (float): Напряжение в кВ.

        Raises:
            RuntimeError: Генератор отверг команду (код SR:12 вне
                ``INFORMATIONAL_CODES``).
            SourceCommunicationError: Генератор не отвечает.

        Если генератор требует прогрева (коды 106/109), метод только кэширует
        номинал и возвращается — прогрев делает :meth:`on_high_voltage`.
        """
        if self.mock:
            return
        self._refuse_if_warming("Source.set_voltage()")
        logging.info('Source.set_voltage() starting... voltage=%.3f', voltage)

        command = "SV:{}".format(str(int(round(voltage * 1000))).zfill(6))

        # На SV генератор ответа не шлёт (руководство §8.2: у SV только
        # параметр передачи) — сразу читаем код ошибки SR:12.
        try:
            error = self._send_and_read_error(command)
        except SourceCommunicationError as e:
            # Эвристика по опыту эксплуатации: в состоянии 109 («Warm-up! 0=No»)
            # генератор молчит и на SR:12. Считаем, что нужен прогрев, но если
            # молчание повторится после прогрева — ошибка уйдёт наверх.
            logging.warning(
                "Source.set_voltage(): no answer to SR:12 after SV (%s); "
                "assuming warm-up required (code 109)", e)
            error = {'code': 109, 'message': self.describe_code(109)}
        logging.info('Source.set_voltage(): after SV command, error=%r', error)

        if error is not None and error['code'] in WARMUP_REQUIRED_CODES:
            # Прогрев здесь НЕ запускаем: метод вызывается из единственного
            # потока сервера железа, и синхронный warmup() (до 30 мин) блокировал
            # все RPC — 21.09.2026 UI и эксперимент получали HardwareUnavailable,
            # пока генератор грелся. Запоминаем номинал; прогрев до него
            # выполнит on_high_voltage() (он идёт в фоновом потоке через
            # HWTomograph.source_power_on_async).
            logging.warning('Source.set_voltage(): warm-up required (code %d) — deferred to '
                            'on_high_voltage(); nominal %.3f kV cached', error['code'], voltage)
            self.last_voltage_nominal = voltage
            self.timer_voltage_nominal = time()
            return

        if error is not None and error['code'] in (118, 119, 121):
            # Генератор ждёт подтверждения сообщения — снимаем его CL и повторяем.
            logging.info('Source.set_voltage(): code %d (%s) — CL and retry SV',
                         error['code'], INFORMATIONAL_CODES[error['code']])
            self._transact("CL", expect_answer=False, read_error=False)
            sleep(CL_SETTLE_DELAY)
            error = self._send_and_read_error(command)
            logging.info('Source.set_voltage(): after CL and retry SV, error=%r', error)

        # Остаточная ошибка: раньше этот блок не проверялся и метод рапортовал
        # успех, обновляя кэш номинала, даже когда SV не принят.
        if error is not None and error['code'] not in INFORMATIONAL_CODES:
            logging.error("Source.set_voltage() error: {}".format(error))
            raise RuntimeError("Source.set_voltage() error: {}".format(error))
        if error is not None:
            logging.info("Source.set_voltage(): informational code %d (%s) — SV accepted",
                         error['code'], INFORMATIONAL_CODES[error['code']])

        # Обновляем кэш номинального напряжения
        self.last_voltage_nominal = voltage
        self.timer_voltage_nominal = time()

        self.wait_for_voltage()
        logging.info('Source.set_voltage() finished.')

    def set_current(self, current):
        """Установить ток.

        Команда ``SC:NNNNNN`` — ток в микроамперах (мА × 1000), формат тот же,
        что у ``SV`` (руководство §8.2, §8.4).

        Args:
            current (float): Ток в мА.

        Raises:
            RuntimeError: Генератор отверг команду.
            SourceCommunicationError: Генератор не отвечает.
        """
        if self.mock:
            return
        self._refuse_if_warming("Source.set_current()")
        logging.debug('Source.set_current() starting...')
        command = "SC:{}".format(str(int(round(current * 1000))).zfill(6))
        error = self._send_and_read_error(command)
        if error is not None and error['code'] not in INFORMATIONAL_CODES:
            logging.error("Source.set_current() error: {}".format(error))
            raise RuntimeError("Source.set_current() error: {}".format(error))
        if error is not None:
            logging.info("Source.set_current(): informational code %d (%s)",
                         error['code'], INFORMATIONAL_CODES[error['code']])

        self.last_current_nominal = current
        self.timer_current_nominal = time()
        self.wait_for_current()
        logging.debug('Source.set_current() finished.')

    # ------------------------------------------------------------------
    # Идентификация
    # ------------------------------------------------------------------

    def get_id(self):
        """Прочитать идентификатор генератора (команда ID).

        Результат читается один раз и хранится в объекте до его
        пересоздания (значение не меняется в работе).

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
        answer, error = self._transact("ID")
        self._check_error(error, "Source.get_id()")

        self.device_id = answer
        logging.debug('Source.get_id() finished.')
        return self.device_id

    def get_tube_name(self):
        """Прочитать наименование трубки (команда XT).

        Результат читается один раз и хранится в объекте до его
        пересоздания (значение не меняется в работе).

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
        answer, error = self._transact("XT")
        self._check_error(error, "Source.get_tube_name()")

        self.tube_name = answer
        logging.debug('Source.get_tube_name() finished.')
        return self.tube_name

    # ------------------------------------------------------------------
    # Ошибки
    # ------------------------------------------------------------------

    def get_error(self):
        """Прочитать текущий код ошибки (SR:12).

        Returns:
            dict | None: ``{'code': int, 'message': str}`` если генератор
            сообщает код, либо None если кода нет (SR:12 = 0).

        Raises:
            SourceCommunicationError: Если обмен не состоялся (таймаут,
                закрытый порт, неразбираемый ответ). «Нет ошибки» и
                «нет связи» — разные исходы: раньше оба давали None,
                и ``on_high_voltage()`` при мёртвом порте рапортовал успех.
        """
        if self.mock:
            return None
        self._refuse_if_warming("Source.get_error()")
        try:
            answer, _ = self._transact("SR:12", read_error=False)
        except SourceCommunicationError:
            raise
        except Exception as e:
            raise SourceCommunicationError(
                "Source.get_error(): communication failed: {}".format(e))

        error_code = self._parse_error_code(answer)
        if error_code:
            return {'code': error_code, 'message': self.describe_code(error_code)}
        return None

    @staticmethod
    def _check_error(error, where):
        """Бросить RuntimeError, если код SR:12 — отказ, а не информация.

        Единая точка применения ``INFORMATIONAL_CODES``: раньше по коду были
        разбросаны три разных набора «неошибок», а 76 (Stand-By) везде
        считался отказом.
        """
        if error is None:
            return
        if error['code'] in INFORMATIONAL_CODES:
            logging.info("%s: informational code %d (%s)",
                         where, error['code'], INFORMATIONAL_CODES[error['code']])
            return
        logging.error("%s error: %s", where, error)
        raise RuntimeError("{} error: {}".format(where, error))

    @classmethod
    def describe_code(cls, code):
        """Расшифровка кода SR:12 (текст из руководства или заглушка)."""
        return cls.STATUS_STRINGS.get(code, "Unknown error code {}".format(code))

    @staticmethod
    def _parse_error_code(answer):
        """Разобрать ответ на SR:12 в целый код ошибки.

        Raises:
            SourceCommunicationError: Ответ не похож на ``*<число>``.
        """
        try:
            return int(answer[1:])
        except (ValueError, IndexError):
            raise SourceCommunicationError(
                "Source: cannot parse SR:12 answer: {!r}".format(answer))

    # ------------------------------------------------------------------
    # Вспомогательные методы
    # ------------------------------------------------------------------

    def get_data_string(self):
        """Прочитать одну строку ответа из serial-порта.

        Протокол: ответ начинается с '*', заканчивается '\\r'.

        Returns:
            str: Строка ответа без завершающих символов.

        Raises:
            SourceCommunicationError: При таймауте или пустом ответе.
        """
        if self.mock:
            return "*0"
        line = self.serial_port.read_until(b'\r')
        logging.debug("Source.get_data_string(): raw=%r", line)
        if not line:
            raise SourceCommunicationError(
                "Source.get_data_string(): timeout — no response from device "
                "(possibly warming up)")
        answer = line.decode().strip()
        # Проверка: ответ должен начинаться с '*'
        if not answer.startswith('*'):
            logging.warning("Source.get_data_string(): unexpected response %r (expected to start with '*')", answer)
        return answer

    def _write_command(self, command):
        """Отправить команду на устройство с корректным окончанием строки.

        Блокировку НЕ захватывает: вызывающий код обязан держать
        ``_port_lock`` на всё время транзакции (команда + ответ) — обычно
        через ``_transact()``. Сбрасывает входной и выходной буферы перед
        отправкой, поэтому неподобранный ответ на предыдущую команду
        отбрасывается.
        """
        if self.mock:
            return
        self.serial_port.reset_input_buffer()
        self.serial_port.reset_output_buffer()
        full = (command + "\r\n").encode()
        self.serial_port.write(full)
        self.serial_port.flush()
        logging.debug("Source._write_command(): sent %r", full)

    def _transact(self, command, expect_answer=True, read_error=True):
        """Отправить команду и вернуть ``(answer, error)`` под ``_port_lock``.

        Атомарная транзакция: write → read answer → read SR:12 — всё под
        мьютексом, параллельный опрос не вклинится между командой и ответом.

        Args:
            command: Строка команды ("VN", "SV:000200"…).
            expect_answer: False для команд-установок (``SV``, ``SC``, ``HV``,
                ``CL``), на которые генератор ответа не шлёт (руководство §8.2:
                у них есть только параметр передачи).
            read_error: Если True, после ответа читается код ошибки SR:12.

        Returns:
            tuple(str | None, dict | None): (строка ответа, ошибка или None).

        Raises:
            SourceCommunicationError: Ответа нет или он неразбираем.
        """
        with self._port_lock:
            self._write_command(command)
            answer = self.get_data_string() if expect_answer else None
            error = None
            if read_error:
                self._write_command("SR:12")
                error_code = self._parse_error_code(self.get_data_string())
                if error_code:
                    error = {'code': error_code,
                             'message': self.describe_code(error_code)}
        return answer, error

    def _send_and_read_error(self, command):
        """Отправить команду без ответа и вернуть код ошибки SR:12 (или None)."""
        return self._transact(command, expect_answer=False)[1]

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
    # Интерфейс get_state
    # ------------------------------------------------------------------

    def get_state(self, options=None):
        """Прочитать состояние устройства по списку параметров.

        Args:
            options (list | str | None): Список запрашиваемых параметров.
                По умолчанию читаются все доступные параметры.
                Допустимые значения: ``'is_on_high_voltage'``, ``'id'``,
                ``'tube_name'``, ``'actual_voltage'``, ``'nominal_voltage'``,
                ``'actual_current'``, ``'nominal_current'``,
                ``'status'``, ``'last_error'``.

        Returns:
            dict: Словарь ``{параметр: значение}``.
        """
        if options is None:
            options = [
                'is_on_high_voltage', 'id', 'tube_name',
                'actual_voltage', 'nominal_voltage',
                'actual_current', 'nominal_current',
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
            'status':             self.get_status,
            'last_error':         self.get_error,
        }

        res = {}
        for option in options:
            if option not in handlers:
                res[option] = {'error': 'Unsupported option: {}'.format(option)}
                continue
            # Один недоступный параметр не должен ронять весь снимок состояния:
            # get_state() вызывается из HWTomograph.get_state() для UI.
            try:
                res[option] = handlers[option]()
            except Exception as e:
                logging.warning("Source.get_state(): '%s' failed: %s", option, e)
                res[option] = {'error': '{}: {}'.format(type(e).__name__, e)}
        return res
