# encoding: utf-8
import serial
import re
import logging

SERIAL_TIMEOUT = 5  # секунд: максимальное время ожидания ответа от устройства


class HWShutter(object):
    """Драйвер рентгеновской заслонки на базе модуля Ke-USB24R.

    Модуль Ke-USB24R подключается к компьютеру через USB и определяется
    системой как виртуальный COM-порт. Управление заслонкой осуществляется
    через одно из четырёх электромагнитных реле модуля.

    Протокол:
        Команды отправляются в текстовом формате, начинаются с '$KE',
        заканчиваются CR+LF (\\r\\n). Ответы начинаются с '#' и также
        заканчиваются CR+LF. При синтаксической ошибке в команде модуль
        возвращает '#ERR'.

    Состояние заслонки:
        - ``is_open() == True``  (реле включено,  Value=1) → заслонка открыта
        - ``is_open() == False`` (реле выключено, Value=0) → заслонка закрыта
    """

    def __init__(self, tty_name, relay_number):
        """Инициализировать объект заслонки и проверить связь с контроллером.

        Args:
            tty_name (str): Имя COM-порта, например ``'/dev/ttyACM2'``
                или ``'COM3'``.
            relay_number (int): Номер реле модуля (от 1 до 4 включительно).

        Raises:
            RuntimeError: Если контроллер не отвечает или возвращает ошибку.
            serial.SerialException: При ошибке открытия порта.
        """
        logging.debug('Shutter.__init__ starting...')
        super(HWShutter, self).__init__()
        self.tty_name = tty_name
        self.relay_number = relay_number
        self.check_module()
        logging.debug('Shutter.__init__ finished.')

    # ------------------------------------------------------------------
    # Внутренние вспомогательные методы
    # ------------------------------------------------------------------

    @staticmethod
    def _send_command(serial_port, cmd):
        """Отправить команду в порт и вернуть ответ без завершающего CRLF.

        Args:
            serial_port (serial.Serial): Открытый объект последовательного порта.
            cmd (str): Текст команды без ``\\r\\n`` (они добавляются автоматически).

        Returns:
            str: Декодированная строка ответа без завершающих пробельных символов.
        """
        serial_port.write("{}\r\n".format(cmd).encode())
        return serial_port.readline().decode('utf-8').strip()

    def _open_port(self):
        """Открыть последовательный порт с нужными параметрами.

        Returns:
            serial.Serial: Открытый объект порта. Следует использовать
            как контекстный менеджер (``with``).
        """
        return serial.Serial(self.tty_name, timeout=SERIAL_TIMEOUT)

    # ------------------------------------------------------------------
    # Диагностика и информация о модуле
    # ------------------------------------------------------------------

    def check_module(self):
        """Проверить работоспособность контроллера командой ``$KE``.

        На первый вызов после подачи питания модуль возвращает ``#ERR``,
        поэтому команда отправляется дважды.

        Raises:
            RuntimeError: Если второй ответ отличается от ``#OK``.
        """
        logging.debug('Shutter.check_module() starting...')
        with self._open_port() as port:
            # HACK: при старте модуль всегда возвращает #ERR на первый запрос,
            # поэтому посылаем команду дважды.
            self._send_command(port, '$KE')
            status = self._send_command(port, '$KE')
            if status != '#OK':
                logging.error('Shutter.check_module() error: %s', status)
                raise RuntimeError('Shutter.check_module() error: {}'.format(status))
        logging.debug('Shutter.check_module() finished.')

    def get_firmware_version(self):
        """Получить версию прошивки модуля командой ``$KE,FW``.

        Команда доступна начиная со 2-й аппаратной версии Ke-USB24R.
        Модули более ранних версий вернут ``#ERR``.

        Returns:
            str: Строка версии прошивки, например ``'2.0'``.

        Raises:
            RuntimeError: Если ответ модуля не соответствует ожидаемому формату.
        """
        logging.debug('Shutter.get_firmware_version() starting...')
        with self._open_port() as port:
            response = self._send_command(port, '$KE,FW')

        pattern = re.compile(r'^#FW,(.+)$')
        matched = pattern.match(response)
        if not matched:
            logging.error('Shutter.get_firmware_version(): unexpected response: %s', response)
            raise RuntimeError(
                'Shutter.get_firmware_version(): unexpected response: {}'.format(response)
            )
        version = matched.group(1)
        logging.debug('Shutter.get_firmware_version() finished: %s', version)
        return version

    def get_serial_number(self):
        """Получить уникальный серийный номер модуля командой ``$KE,SER``.

        Каждый модуль Ke-USB24R имеет собственный уникальный серийный номер.

        Returns:
            str: Серийный номер модуля.

        Raises:
            RuntimeError: Если ответ модуля не соответствует ожидаемому формату.
        """
        logging.debug('Shutter.get_serial_number() starting...')
        with self._open_port() as port:
            response = self._send_command(port, '$KE,SER')

        pattern = re.compile(r'^#SER,(.+)$')
        matched = pattern.match(response)
        if not matched:
            logging.error('Shutter.get_serial_number(): unexpected response: %s', response)
            raise RuntimeError(
                'Shutter.get_serial_number(): unexpected response: {}'.format(response)
            )
        serial_number = matched.group(1)
        logging.debug('Shutter.get_serial_number() finished: %s', serial_number)
        return serial_number

    # ------------------------------------------------------------------
    # Управление заслонкой (реле)
    # ------------------------------------------------------------------

    def open(self):
        """Открыть заслонку, включив реле (``$KE,REL,N,1``).

        Реле включено: контакты 2–3 замкнуты, 1–2 разомкнуты.

        Raises:
            RuntimeError: Если контроллер не подтверждает выполнение команды.
        """
        logging.debug('Shutter.open() starting...')
        with self._open_port() as port:
            response = self._send_command(
                port, '$KE,REL,{},1'.format(self.relay_number)
            )
            if response != '#REL,OK':
                error = "Shutter.open(): Can't set relay {} to 1, got: {}".format(
                    self.relay_number, response
                )
                logging.error(error)
                raise RuntimeError(error)
        logging.debug('Shutter.open() finished.')

    def close(self):
        """Закрыть заслонку, выключив реле (``$KE,REL,N,0``).

        Реле выключено: контакты 1–2 замкнуты, 2–3 разомкнуты (исходное состояние).

        Raises:
            RuntimeError: Если контроллер не подтверждает выполнение команды.
        """
        logging.debug('Shutter.close() starting...')
        with self._open_port() as port:
            response = self._send_command(
                port, '$KE,REL,{},0'.format(self.relay_number)
            )
            if response != '#REL,OK':
                error = "Shutter.close(): Can't set relay {} to 0, got: {}".format(
                    self.relay_number, response
                )
                logging.error(error)
                raise RuntimeError(error)
        logging.debug('Shutter.close() finished.')

    def is_open(self):
        """Проверить, открыта ли заслонка, командой ``$KE,RDR,N``.

        Состояние реле: 1 → реле включено (заслонка открыта),
        0 → реле выключено (заслонка закрыта).

        Returns:
            bool: ``True`` если заслонка открыта, ``False`` если закрыта.

        Raises:
            RuntimeError: Если ответ модуля не соответствует ожидаемому формату.
        """
        logging.debug('Shutter.is_open() starting...')
        with self._open_port() as port:
            response = self._send_command(
                port, '$KE,RDR,{}'.format(self.relay_number)
            )

        pattern = re.compile(r'^#RDR,{},([01])$'.format(self.relay_number))
        matched = pattern.match(response)
        if not matched:
            logging.error('Shutter.is_open(): unexpected response: %s', response)
            raise RuntimeError(
                'Shutter.is_open(): unexpected response: {}'.format(response)
            )
        relay_state = bool(int(matched.group(1)))
        logging.debug('Shutter.is_open() finished: %s', relay_state)
        return relay_state

    def get_all_relay_states(self):
        """Получить состояния всех четырёх реле командой ``$KE,RDR,ALL``.

        Команда доступна начиная со 2-й аппаратной версии Ke-USB24R.

        Returns:
            dict: Словарь вида ``{1: False, 2: True, 3: True, 4: True}``,
            где ключ — номер реле (1–4), значение — ``True`` если реле включено.

        Raises:
            RuntimeError: Если ответ модуля не соответствует ожидаемому формату.
        """
        logging.debug('Shutter.get_all_relay_states() starting...')
        with self._open_port() as port:
            response = self._send_command(port, '$KE,RDR,ALL')

        # Ожидаемый формат: #RDR,ALL,0,1,1,1
        pattern = re.compile(r'^#RDR,ALL,([01]),([01]),([01]),([01])$')
        matched = pattern.match(response)
        if not matched:
            logging.error('Shutter.get_all_relay_states(): unexpected response: %s', response)
            raise RuntimeError(
                'Shutter.get_all_relay_states(): unexpected response: {}'.format(response)
            )
        states = {i + 1: bool(int(matched.group(i + 1))) for i in range(4)}
        logging.debug('Shutter.get_all_relay_states() finished: %s', states)
        return states

    def read_adc(self, channel):
        """Считать значение с одного из АЦП-каналов модуля (``$KE,ADC,N``).

        Модуль имеет 4 канала 10-битного АЦП с входным диапазоном 0–5 В.
        Для перевода сырого значения в вольты используется формула::

            voltage = raw_value * 5.0 / 1023.0

        Args:
            channel (int): Номер канала АЦП (от 1 до 4 включительно).

        Returns:
            dict: Словарь ``{'raw': int, 'voltage_v': float}``, где
            ``raw`` — 10-битное целое (0–1023),
            ``voltage_v`` — напряжение в вольтах (0.0–5.0).

        Raises:
            ValueError: Если ``channel`` не в диапазоне 1–4.
            RuntimeError: Если ответ модуля не соответствует ожидаемому формату.
        """
        if channel not in range(1, 5):
            raise ValueError(
                'Shutter.read_adc(): channel must be 1..4, got {}'.format(channel)
            )
        logging.debug('Shutter.read_adc(channel=%d) starting...', channel)
        with self._open_port() as port:
            response = self._send_command(port, '$KE,ADC,{}'.format(channel))

        # Ожидаемый формат: #ADC,3,0645
        pattern = re.compile(r'^#ADC,{},(\d+)$'.format(channel))
        matched = pattern.match(response)
        if not matched:
            logging.error('Shutter.read_adc(): unexpected response: %s', response)
            raise RuntimeError(
                'Shutter.read_adc(): unexpected response: {}'.format(response)
            )
        raw = int(matched.group(1))
        voltage = raw * 5.0 / 1023.0
        result = {'raw': raw, 'voltage_v': round(voltage, 4)}
        logging.debug('Shutter.read_adc() finished: %s', result)
        return result

    def reset(self):
        """Сбросить все настройки модуля в значения по умолчанию (``$KE,RST``).

        После сброса:
        - все линии ввода/вывода переводятся в режим выхода с логическим нулём;
        - сохранённые в памяти настройки направления линий стираются;
        - все реле возвращаются в исходное состояние (выключены);
        - пользовательские данные и USB-дескриптор сбрасываются.

        .. warning::
            Вызов этой команды закроет заслонку, если она была открыта,
            а также сбросит настройки остальных реле и линий ввода/вывода.

        Raises:
            RuntimeError: Если контроллер не подтверждает выполнение сброса.
        """
        logging.debug('Shutter.reset() starting...')
        with self._open_port() as port:
            response = self._send_command(port, '$KE,RST')
        if response != '#RST,OK':
            logging.error('Shutter.reset(): unexpected response: %s', response)
            raise RuntimeError(
                'Shutter.reset(): unexpected response: {}'.format(response)
            )
        logging.debug('Shutter.reset() finished.')

    # ------------------------------------------------------------------
    # Интерфейс get_state / set_state
    # ------------------------------------------------------------------

    def get_state(self, options=None):
        """Получить состояние заслонки по указанным ключам.

        Args:
            options (str | list | tuple | None): Один ключ или список ключей.
                Допустимые ключи:

                - ``'is_open'``   — ``True`` если заслонка открыта.
                - ``'is_closed'`` — ``True`` если заслонка закрыта.

                По умолчанию (``None``) — возвращает ``['is_open']``.

        Returns:
            dict: Словарь ``{ключ: значение}``. Для неизвестных ключей
            значение равно ``{'error': 'Unsupported option'}``.

        Example::

            shutter.get_state()                      # {'is_open': True}
            shutter.get_state('is_closed')           # {'is_closed': False}
            shutter.get_state(['is_open', 'is_closed'])
            # {'is_open': True, 'is_closed': False}
        """
        if options is None:
            options = ['is_open']
        if not isinstance(options, (list, tuple)):
            options = [options]

        res = {}
        for option in options:
            if option == 'is_open':
                res[option] = self.is_open()
            elif option == 'is_closed':
                res[option] = not self.is_open()
            else:
                res[option] = {'error': 'Unsupported option'}
        return res

    def set_state(self, options_dict):
        """Установить состояние заслонки согласно переданному словарю.

        Args:
            options_dict (dict): Словарь вида ``{ключ: значение}``.
                Допустимые ключи и значения:

                - ``'is_open': True``  — открыть заслонку.
                - ``'is_open': False`` — закрыть заслонку.

                Прочие ключи или нелогические значения записываются в результат
                как ``{'error': 'Unsupported option'}``.

        Returns:
            dict: Словарь вида::

                {
                    'requested_state': options_dict,
                    'result': {ключ: None | {'error': str}}
                }

            ``None`` в ``result`` означает успешное выполнение команды.

        Example::

            shutter.set_state({'is_open': True})
            # {'requested_state': {'is_open': True}, 'result': {'is_open': None}}
        """
        res = {}
        for option, value in options_dict.items():
            if option == 'is_open':
                if not isinstance(value, bool):
                    res[option] = {'error': 'Unsupported option: value must be bool'}
                elif value:
                    self.open()
                    res[option] = None
                else:
                    self.close()
                    res[option] = None
            else:
                res[option] = {'error': 'Unsupported option'}

        return {'requested_state': options_dict, 'result': res}
