# encoding: utf-8
import logging
import re
import threading
import warnings

import serial

SERIAL_TIMEOUT = 5        # секунд: максимальное время ожидания ответа от устройства
SERIAL_WRITE_TIMEOUT = 5  # секунд: максимальное время записи в порт (иначе write() может висеть вечно)

#: Об устаревших именах open()/close() предупреждаем один раз на процесс.
_DEPRECATED_ALIASES_WARNED = set()


def _warn_deprecated_alias(old_name, new_name):
    """Один раз предупредить о вызове устаревшего имени метода."""
    if old_name in _DEPRECATED_ALIASES_WARNED:
        return
    _DEPRECATED_ALIASES_WARNED.add(old_name)
    message = (
        'HWShutter.{}() переименован в HWShutter.{}(). У остальных драйверов '
        'close() освобождает ресурс, а не управляет устройством; для '
        'освобождения порта заслонки используйте release().'.format(old_name, new_name)
    )
    warnings.warn(message, DeprecationWarning, stacklevel=3)
    logging.warning(message)


class HWShutter(object):
    """Драйвер рентгеновской заслонки на базе модуля Ke-USB24R.

    Модуль Ke-USB24R подключается к компьютеру через USB и определяется
    системой как виртуальный COM-порт. Управление заслонкой осуществляется
    через одно из четырёх электромагнитных реле модуля.

    Порт открывается один раз в ``__init__`` и живёт вместе с объектом:
    каждое открытие CDC-ACM дёргает линию DTR, а раньше порт открывался
    и закрывался на каждую команду (2–4 раза за одно переключение
    состояния). Освобождается порт явным вызовом :meth:`release`.

    Доступ к порту сериализован внутренним локом, поэтому объектом можно
    пользоваться из нескольких потоков (например, фоновый эксперимент и
    опрос состояния из UI).

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
        """Открыть порт модуля и проверить связь с контроллером.

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
        self._lock = threading.RLock()
        self._port = serial.Serial(
            tty_name,
            timeout=SERIAL_TIMEOUT,
            write_timeout=SERIAL_WRITE_TIMEOUT,
        )
        try:
            self.check_module()
        except Exception:
            # Не оставляем открытый порт, если модуль не отвечает:
            # иначе следующая попытка создать объект получит занятый /dev/ttyACM*.
            self.release()
            raise
        logging.debug('Shutter.__init__ finished.')

    # ------------------------------------------------------------------
    # Порт и низкоуровневый обмен
    # ------------------------------------------------------------------

    def _send_command(self, cmd):
        """Отправить команду в порт и вернуть ответ без завершающего CRLF.

        Args:
            cmd (str): Текст команды без ``\\r\\n`` (они добавляются автоматически).

        Returns:
            str: Декодированная строка ответа без завершающих пробельных символов.

        Raises:
            RuntimeError: Если порт уже освобождён вызовом release().
            serial.SerialException: При ошибке обмена.
            serial.SerialTimeoutException: Если запись не уложилась в write_timeout.
        """
        with self._lock:
            if self._port is None or not self._port.is_open:
                raise RuntimeError(
                    'Shutter: port {} is closed (release() already called)'.format(self.tty_name)
                )
            # Мусор от предыдущей команды не должен попасть в текущий ответ.
            self._port.reset_input_buffer()
            self._port.write('{}\r\n'.format(cmd).encode())
            return self._port.readline().decode('utf-8').strip()

    def release(self):
        """Освободить последовательный порт модуля.

        Состояние заслонки не меняется: реле остаётся в том положении,
        в котором было. Повторный вызов безопасен.
        """
        with self._lock:
            port, self._port = self._port, None
            if port is None:
                return
            try:
                port.close()
            except Exception as e:  # noqa: BLE001 - закрытие порта не должно ронять вызывающего
                logging.warning('Shutter.release(): %s', e)
        logging.debug('Shutter.release() finished.')

    #: Синоним release() для единообразия с остальными драйверами,
    #: где ресурс освобождает close(). После удаления устаревшего
    #: alias close() (= close_shutter) эту роль возьмёт на себя close().
    close_port = release

    def is_port_open(self):
        """True, если порт модуля ещё открыт."""
        with self._lock:
            return self._port is not None and self._port.is_open

    # ------------------------------------------------------------------
    # Диагностика и информация о модуле
    # ------------------------------------------------------------------

    def _handshake(self):
        """Отправить ``$KE`` и вернуть ответ модуля.

        HACK: после подачи питания модуль отвечает ``#ERR`` на первый
        запрос, поэтому команда отправляется дважды и учитывается второй
        ответ. Проверить это на железе в рамках правки было нельзя,
        поэтому поведение сохранено, но изолировано в одном методе:
        если выяснится, что двойная отправка не нужна, править надо
        только здесь. Выполняется один раз при создании объекта.

        Returns:
            str: Ответ модуля на второй ``$KE``.
        """
        with self._lock:
            self._send_command('$KE')
            return self._send_command('$KE')

    def check_module(self):
        """Проверить работоспособность контроллера командой ``$KE``.

        Вызывается один раз из ``__init__``.

        Raises:
            RuntimeError: Если ответ модуля отличается от ``#OK``.
        """
        logging.debug('Shutter.check_module() starting...')
        status = self._handshake()
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
        response = self._send_command('$KE,FW')

        matched = re.match(r'^#FW,(.+)$', response)
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
        response = self._send_command('$KE,SER')

        matched = re.match(r'^#SER,(.+)$', response)
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

    def _set_relay(self, value, what):
        """Переключить реле заслонки командой ``$KE,REL,N,value``.

        Args:
            value (int): 1 — включить реле (открыть), 0 — выключить (закрыть).
            what (str): Имя операции для сообщения об ошибке.

        Raises:
            RuntimeError: Если контроллер не подтверждает выполнение команды.
        """
        response = self._send_command('$KE,REL,{},{}'.format(self.relay_number, value))
        if response != '#REL,OK':
            error = "Shutter.{}(): Can't set relay {} to {}, got: {}".format(
                what, self.relay_number, value, response
            )
            logging.error(error)
            raise RuntimeError(error)

    def open_shutter(self):
        """Открыть заслонку, включив реле (``$KE,REL,N,1``).

        Реле включено: контакты 2–3 замкнуты, 1–2 разомкнуты.

        Raises:
            RuntimeError: Если контроллер не подтверждает выполнение команды.
        """
        logging.debug('Shutter.open_shutter() starting...')
        self._set_relay(1, 'open_shutter')
        logging.debug('Shutter.open_shutter() finished.')

    def close_shutter(self):
        """Закрыть заслонку, выключив реле (``$KE,REL,N,0``).

        Реле выключено: контакты 1–2 замкнуты, 2–3 разомкнуты (исходное состояние).

        Raises:
            RuntimeError: Если контроллер не подтверждает выполнение команды.
        """
        logging.debug('Shutter.close_shutter() starting...')
        self._set_relay(0, 'close_shutter')
        logging.debug('Shutter.close_shutter() finished.')

    def open(self):
        """Устаревший синоним :meth:`open_shutter` (будет удалён).

        .. deprecated::
            Используйте :meth:`open_shutter`.
        """
        _warn_deprecated_alias('open', 'open_shutter')
        self.open_shutter()

    def close(self):
        """Устаревший синоним :meth:`close_shutter` (будет удалён).

        .. deprecated::
            Используйте :meth:`close_shutter` для управления заслонкой и
            :meth:`release` для освобождения порта. После удаления этого
            синонима ``close()`` станет освобождать ресурс, как у остальных
            драйверов.
        """
        _warn_deprecated_alias('close', 'close_shutter')
        self.close_shutter()

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
        response = self._send_command('$KE,RDR,{}'.format(self.relay_number))

        matched = re.match(r'^#RDR,{},([01])$'.format(self.relay_number), response)
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
        response = self._send_command('$KE,RDR,ALL')

        # Ожидаемый формат: #RDR,ALL,0,1,1,1
        matched = re.match(r'^#RDR,ALL,([01]),([01]),([01]),([01])$', response)
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
        response = self._send_command('$KE,ADC,{}'.format(channel))

        # Ожидаемый формат: #ADC,3,0645
        matched = re.match(r'^#ADC,{},(\d+)$'.format(channel), response)
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
        response = self._send_command('$KE,RST')
        if response != '#RST,OK':
            logging.error('Shutter.reset(): unexpected response: %s', response)
            raise RuntimeError(
                'Shutter.reset(): unexpected response: {}'.format(response)
            )
        logging.debug('Shutter.reset() finished.')

    # ------------------------------------------------------------------
    # Интерфейс get_state
    # ------------------------------------------------------------------

    #: Ключи, которые возвращает get_state().
    STATE_KEYS = ('is_open', 'is_closed')

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
