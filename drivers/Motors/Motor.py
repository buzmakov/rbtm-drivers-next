import logging
import atexit
import time

from .motor_math import (move_timeout_s, to_steps, from_steps,
                         normalize_deg, shortest_delta_deg)

try:
    from .pyximc import lib, get_position_t, byref, Result, cast, POINTER, c_int, \
        device_information_t, string_at, edges_settings_t, engine_settings_t, \
        MicrostepMode, status_t, power_settings_t, move_settings_t, MoveState, MvcmdStatus
except ImportError as err:
    raise ImportError(
        "Can't import pyximc module. The most probable reason is that you haven't copied pyximc.py to the "
        "working directory. See developers' documentation for details."
    ) from err
except OSError as err:
    raise ImportError(
        "Can't load libximc library. Please add all shared libraries to the appropriate places (next to "
        "pyximc.py on Windows). It is described in detail in developers' documentation. On Linux make sure "
        "you installed libximc-dev package."
    ) from err


#: Интервал опроса статуса контроллера при ожидании остановки, с.
WAIT_FOR_STOP_POLL_INTERVAL_S = 0.05
#: Таймаут команд, не являющихся перемещением (zero и т.п.), с.
COMMAND_TIMEOUT_S = 5.0


class MotorTimeoutError(RuntimeError):
    """Мотор не остановился за отведённое время.

    Наследуется от :class:`RuntimeError`, поэтому существующий код,
    ловящий ``RuntimeError``, продолжает работать.
    """


class BaseMotor(object):
    """
    Базовый класс для шаговых двигателей XIMC (Standa).

    Инкапсулирует открытие/закрытие устройства, применение начальных настроек
    контроллера и низкоуровневые команды позиционирования (в шагах).

    Не создавайте напрямую — используйте :class:`HWRotaryMotor` или :class:`HWLinearMotor`.
    """

    def __init__(self, device_name, speed, acceleration):
        """
        Инициализация и открытие устройства мотора.

        :param device_name: str | bytes — имя устройства (порт), например 'xi-com:///dev/ximc/0000037A'.
        :param speed: int — скорость движения в шагах/с (записывается в контроллер при открытии).
        :param acceleration: int — ускорение/торможение в шагах/с² (записывается в контроллер при открытии).
        """
        self.device_name = device_name
        self.speed = int(speed)
        self.acceleration = int(acceleration)
        self.device_id = -1
        self.open()
        atexit.register(self.close)

    # ─── Device lifecycle ────────────────────────────────────────────────────────

    def open(self):
        """
        Открыть устройство и применить конфигурацию к контроллеру:
        - отключить граничные флаги (BorderFlags = 0),
        - установить HoldCurrent = 0 (нет удерживающего тока после остановки),
        - записать speed и acceleration из конфига,
        - установить режим микрошага 1/256.

        Вызывается автоматически в __init__.
        :raises RuntimeError: если устройство не открылось или любая команда вернула ошибку.
        """
        logging.debug("Motor.open() starting...")

        if type(self.device_name) is str:
            open_name = self.device_name.encode()
        else:
            open_name = self.device_name

        device_id = lib.open_device(open_name)
        self.device_id = device_id
        logging.info('Motor device_id: {}'.format(self.device_id))
        if device_id == -1:
            logging.error("Motor.open(): open failed (%s)", self.device_name)
            raise RuntimeError("Motor.open(): open failed ({})".format(self.device_name))

        # Если любая из настроек ниже упадёт — освобождаем контроллер,
        # иначе libximc держит его занятым и следующая попытка открытия
        # (например, при пересоздании HWTomograph) падает с "open failed".
        try:
            self._configure()
        except Exception:
            self.close()
            raise

    def _configure(self):
        """Применить начальные настройки к открытому контроллеру (см. open())."""
        device_id = self.device_id

        # Отключить граничные флаги (без аппаратных концевых выключателей)
        edges_settings = edges_settings_t()
        self._check(lib.get_edges_settings(device_id, byref(edges_settings)),
                    'get_edges_settings')
        edges_settings.BorderFlags = 0
        self._check(lib.set_edges_settings(device_id, byref(edges_settings)),
                    'set_edges_settings')

        # Отключить удерживающий ток (мотор не греется в покое)
        power_settings = power_settings_t()
        self._check(lib.get_power_settings(device_id, byref(power_settings)),
                    'get_power_settings')
        power_settings.HoldCurrent = 0
        self._check(lib.set_power_settings(device_id, byref(power_settings)),
                    'set_power_settings')

        # Применить скорость и ускорение из конфигурации к контроллеру
        move_settings = move_settings_t()
        self._check(lib.get_move_settings(device_id, byref(move_settings)),
                    'get_move_settings')
        move_settings.Speed = self.speed
        move_settings.Accel = self.acceleration
        move_settings.Decel = self.acceleration
        self._check(lib.set_move_settings(device_id, byref(move_settings)),
                    'set_move_settings')

        self.set_microstep_mode_256()

        logging.debug("Motor.open() finished")

    def close(self):
        """
        Закрыть устройство и освободить ресурс контроллера.

        atexit оставлен как страховка: сервер железа однопоточный и может быть
        снят сигналом, а незакрытый контроллер libximc остаётся занятым, и
        следующее открытие падает с "open failed". Поэтому close() снимает
        свою регистрацию в atexit (unregister) — после явного закрытия
        интерпретатор больше не держит ссылку на объект мотора.

        :return: код результата libximc (Result.Ok = 0).
        """
        atexit.unregister(self.close)
        # Повторный вызов (atexit после явного close()) — ничего не делаем
        if self.device_id is None or self.device_id == -1:
            return Result.Ok
        result_code = lib.close_device(byref(cast(self.device_id, POINTER(c_int))))
        if result_code != Result.Ok:
            logging.error("Motor.close() error: {}".format(result_code))
        self.device_id = -1
        return result_code

    # ─── Info / status ───────────────────────────────────────────────────────────

    def get_info(self):
        """
        Получить информацию о производителе и версии прошивки контроллера.

        :return: dict с ключами Manufacturer, ManufacturerId, ProductDescription (str),
                 Major, Minor, Release (int). Значения — как есть, без repr().
                 При ошибке метод бросает исключение, а не возвращает ключ 'error'.
        :raises RuntimeError: если запрос завершился с ошибкой.
        """
        logging.debug("Get device info")
        x_device_information = device_information_t()
        self._check(lib.get_device_information(self.device_id, byref(x_device_information)),
                    'get_info')
        return {
            "Manufacturer": string_at(x_device_information.Manufacturer).decode(),
            "ManufacturerId": string_at(x_device_information.ManufacturerId).decode(),
            "ProductDescription": string_at(x_device_information.ProductDescription).decode(),
            "Major": x_device_information.Major,
            "Minor": x_device_information.Minor,
            "Release": x_device_information.Release,
        }

    def get_power_info(self):
        """
        Получить настройки питания контроллера (удерживающий ток, задержки, флаги).

        :return: dict с ключами (все значения — int):
                 Power.HoldCurrent (% от номинального тока),
                 Power.CurrReductDelay (мс), Power.PowerOffDelay (с),
                 Power.CurrentSetTime (мс), Power.PowerFlags (битовые флаги).
        :raises RuntimeError: если запрос завершился с ошибкой.
        """
        logging.debug("Get device power info")
        power_settings = power_settings_t()
        self._check(lib.get_power_settings(self.device_id, byref(power_settings)),
                    'get_power_info')
        return {
            "Power.HoldCurrent": power_settings.HoldCurrent,
            "Power.CurrReductDelay": power_settings.CurrReductDelay,
            "Power.PowerOffDelay": power_settings.PowerOffDelay,
            "Power.CurrentSetTime": power_settings.CurrentSetTime,
            "Power.PowerFlags": power_settings.PowerFlags,
        }

    def get_status(self):
        """
        Получить текущий статус контроллера (ток двигателя, напряжение питания, флаги состояния).

        :return: dict с ключами (все значения — int):
                 Status.Ipwr (ток двигателя, мА),
                 Status.Upwr (напряжение питания, мВ),
                 Status.Iusb (ток USB, мА),
                 Status.Flags (битовые флаги StateFlags),
                 Status.MoveSts (флаги движения MoveState),
                 Status.MvCmdSts (статус последней команды движения MvcmdStatus).
        :raises RuntimeError: если запрос завершился с ошибкой.
        """
        logging.debug("Get status")
        x_status = status_t()
        self._check(lib.get_status(self.device_id, byref(x_status)), 'get_status')
        return {
            "Status.Ipwr": x_status.Ipwr,
            "Status.Upwr": x_status.Upwr,
            "Status.Iusb": x_status.Iusb,
            "Status.Flags": x_status.Flags,
            "Status.MoveSts": x_status.MoveSts,
            "Status.MvCmdSts": x_status.MvCmdSts,
        }

    # ─── State ───────────────────────────────────────────────────────────────────

    #: Ключи, которые возвращает get_state(). Подклассы дополняют список своими
    #: параметрами; значение каждого ключа, кроме вычисляемых, — одноимённый атрибут.
    STATE_KEYS = ('device_name', 'speed', 'acceleration', 'position')

    def _state_value(self, option):
        """Вычислить значение одного ключа get_state().

        Подклассы переопределяют метод для ключей, которых нет среди атрибутов
        (например, 'position' в своих единицах).
        """
        if option == 'position':
            return self.get_position()
        return getattr(self, option)

    def get_state(self, options=None):
        """
        Получить состояние мотора по запрошенным параметрам.

        :param options: list[str] | str | None — список запрашиваемых параметров
                        из STATE_KEYS конкретного класса.
                        None — вернуть все параметры (по умолчанию).
        :return: dict {option: value, ...}. Для неизвестного ключа значение —
                 {'error': 'Unsupported option ...'}.
        """
        if options is None:
            options = list(self.STATE_KEYS)
        if not isinstance(options, (list, tuple)):
            options = [options]

        res = {}
        for option in options:
            if option in self.STATE_KEYS:
                res[option] = self._state_value(option)
            else:
                res[option] = {'error': 'Unsupported option {}'.format(option)}
        return res

    # ─── Waiting for the controller ──────────────────────────────────────────────

    def _check(self, result, what):
        """Проверить код возврата libximc и бросить RuntimeError при ошибке.

        :param result: int — код возврата функции libximc.
        :param what: str — имя операции для сообщения об ошибке.
        :raises RuntimeError: если result != Result.Ok.
        """
        if result != Result.Ok:
            message = "{}.{} error: {}".format(type(self).__name__, what, result)
            logging.error(message)
            raise RuntimeError(message)

    def _move_timeout(self, distance_steps):
        """Оценить таймаут ожидания остановки по длине перемещения и скорости."""
        return move_timeout_s(distance_steps, self.speed)

    def _wait_for_stop(self, timeout, what='move'):
        """Дождаться остановки мотора, опрашивая статус контроллера.

        Заменяет ``lib.command_wait_for_stop()``: у неё второй аргумент —
        интервал опроса, а не таймаут, и ждёт она бесконечно.

        Мотор считается остановившимся, когда сброшены оба признака:
        ``MoveSts & MOVE_STATE_MOVING`` и ``MvCmdSts & MVCMD_RUNNING``.

        :param timeout: float — предельное время ожидания, с.
        :param what: str — имя операции для сообщения об ошибке.
        :raises MotorTimeoutError: если мотор не остановился за timeout.
        :raises RuntimeError: если опрос статуса завершился с ошибкой.
        """
        deadline = time.monotonic() + float(timeout)
        while True:
            x_status = status_t()
            self._check(lib.get_status(self.device_id, byref(x_status)), 'get_status')

            moving = bool(x_status.MoveSts & MoveState.MOVE_STATE_MOVING)
            running = bool(x_status.MvCmdSts & MvcmdStatus.MVCMD_RUNNING)
            if not moving and not running:
                return

            if time.monotonic() >= deadline:
                message = (
                    "{}.{}: motor did not stop within {:.1f} s "
                    "(MoveSts=0x{:02X}, MvCmdSts=0x{:02X}, position={})".format(
                        type(self).__name__, what, float(timeout),
                        x_status.MoveSts, x_status.MvCmdSts, x_status.CurPosition)
                )
                logging.error(message)
                raise MotorTimeoutError(message)

            time.sleep(WAIT_FOR_STOP_POLL_INTERVAL_S)

    # ─── Position ────────────────────────────────────────────────────────────────

    def get_position(self):
        """
        Получить текущую абсолютную позицию мотора в шагах с учётом микрошага.

        :return: float — позиция = Position + uPosition / 256.
        :raises RuntimeError: если запрос завершился с ошибкой.
        """
        logging.debug("Motor.get_position() starting...")
        x_pos = get_position_t()
        self._check(lib.get_position(self.device_id, byref(x_pos)), 'get_position')
        res = from_steps(x_pos.Position, x_pos.uPosition)
        logging.debug("Motor.get_position() finished.")
        return res

    # ─── Movement ────────────────────────────────────────────────────────────────

    def move_to_position(self, position, uposition=0, blocking=True):
        """
        Переместить мотор на абсолютную позицию в шагах.

        :param position: int — целая часть позиции в шагах.
        :param uposition: int — дробная часть позиции в микрошагах [-255, 255]
                          (знак должен совпадать со знаком position).
        :param blocking: bool — если True (по умолчанию), ждать остановки мотора
                         с таймаутом, рассчитанным по расстоянию и скорости.
                         При False команда только отправляется контроллеру;
                         вызывающий сам решает, когда и как дождаться остановки.
        :raises RuntimeError: если команда отклонена контроллером.
        :raises MotorTimeoutError: при blocking=True, если мотор не остановился вовремя.
        """
        logging.debug("Motor.move_to_position() starting...")
        distance = abs(from_steps(position, uposition) - self.get_position()) if blocking else 0.
        self._check(lib.command_move(self.device_id, position, uposition), 'move_to_position')

        if blocking:
            self._wait_for_stop(self._move_timeout(distance), 'move_to_position')
        logging.debug("Motor.move_to_position() finished.")

    def move_by_delta(self, step, ustep=0, blocking=True):
        """
        Переместить мотор на относительное смещение в шагах.

        :param step: int — смещение в целых шагах (может быть отрицательным).
        :param ustep: int — дробная часть смещения в микрошагах [-255, 255]
                      (знак должен совпадать со знаком step).
        :param blocking: bool — если True (по умолчанию), ждать остановки мотора
                         с таймаутом, рассчитанным по расстоянию и скорости.
        :raises RuntimeError: если команда отклонена контроллером.
        :raises MotorTimeoutError: при blocking=True, если мотор не остановился вовремя.
        """
        logging.debug("Motor.move_by_delta() starting...")
        self._check(lib.command_movr(self.device_id, step, ustep), 'move_by_delta')

        if blocking:
            self._wait_for_stop(self._move_timeout(from_steps(step, ustep)), 'move_by_delta')
        logging.debug("Motor.move_by_delta() finished")

    # ─── Calibration / configuration ─────────────────────────────────────────────

    def set_zero(self, blocking=True):
        """
        Объявить текущую позицию нулём (home position).

        Команда не двигает мотор: она обнуляет счётчик шагов контроллера,
        то есть текущая физическая позиция начинает считаться нулевой.
        Все последующие get_position()/move_to_position() отсчитываются от неё.

        :param blocking: bool — если True (по умолчанию), дождаться, пока
                         контроллер отработает команду (COMMAND_TIMEOUT_S).
        :raises RuntimeError: если команда отклонена контроллером.
        :raises MotorTimeoutError: при blocking=True, если контроллер остался занят.
        """
        logging.debug("Motor.set_zero() starting...")
        self._check(lib.command_zero(self.device_id), 'set_zero')
        if blocking:
            self._wait_for_stop(COMMAND_TIMEOUT_S, 'set_zero')
        logging.debug("Motor.set_zero() finished")

    def set_microstep_mode_256(self):
        """
        Установить режим микрошага 1/256 для повышения точности позиционирования.
        Вызывается автоматически при открытии устройства в open().
        :raises RuntimeError: если чтение или запись настроек двигателя завершились с ошибкой.
        """
        logging.debug("\nSet microstep mode to 256")
        eng = engine_settings_t()
        result = lib.get_engine_settings(self.device_id, byref(eng))
        if not result == Result.Ok:
            logging.error("Motor.set_microstep_mode_256() error: {}".format(result))
            raise RuntimeError("Motor.set_microstep_mode_256() error: {}".format(result))
        # MICROSTEP_MODE_FRAC_256: 256 микрошагов на один полный шаг
        eng.MicrostepMode = MicrostepMode.MICROSTEP_MODE_FRAC_256
        result = lib.set_engine_settings(self.device_id, byref(eng))
        if not result == Result.Ok:
            logging.error("Motor.set_microstep_mode_256() error: {}".format(result))
            raise RuntimeError("Motor.set_microstep_mode_256() error: {}".format(result))


class HWRotaryMotor(BaseMotor):
    """
    Вращательный (угловой) мотор.

    Расширяет :class:`BaseMotor` методами работы с градусами.
    Используется для поворота образца при томографической съёмке.

    Пример::

        motor = HWRotaryMotor('xi-com:///dev/ximc/0000037A',
                              speed=500, acceleration=500,
                              steps_on_deg=90.0)   # 32400 шагов / 360° = 90 шагов/°
        motor.move_to_position_deg(90.0)
        angle = motor.get_position_deg()
    """

    def __init__(self, device_name, speed, acceleration, steps_on_deg):
        """
        :param device_name: str | bytes — имя устройства (порт).
        :param speed: int — скорость в шагах/с.
        :param acceleration: int — ускорение в шагах/с².
        :param steps_on_deg: float — число шагов на один градус поворота.
                             Например: 32400 шагов/об / 360° = 90 шагов/°.
        """
        self.steps_on_deg = float(steps_on_deg)
        super().__init__(device_name, speed, acceleration)

    # ─── Internal helpers ────────────────────────────────────────────────────────

    def _deg_to_steps(self, deg):
        """Перевести градусы в (шаги, микрошаги) — единственное место перевода."""
        return to_steps(float(deg) * self.steps_on_deg)

    # ─── Position ────────────────────────────────────────────────────────────────

    def get_position_deg(self):
        """
        Получить текущий угол, нормализованный к диапазону [0, 360).

        Счётчик шагов контроллера не ограничен: после нескольких оборотов
        он уходит далеко за 32400 шагов. Наружу отдаётся именно угол
        в [0, 360), как его ожидает UI и метаданные кадра.
        Ненормализованную позицию можно получить через get_position() (шаги).

        :return: float — угол в градусах, 0 <= angle < 360.
        :raises RuntimeError: если запрос к контроллеру завершился с ошибкой.
        """
        logging.debug("HWRotaryMotor.get_position_deg() starting...")
        res = normalize_deg(self.get_position() / self.steps_on_deg)
        logging.debug("HWRotaryMotor.get_position_deg() finished.")
        return res

    # ─── Movement ────────────────────────────────────────────────────────────────

    def move_to_position_deg(self, position, blocking=True):
        """
        Повернуть мотор к заданному углу по кратчайшему пути.

        Целевой угол трактуется как положение на окружности: смещение
        считается в (-180, 180] от текущего нормализованного угла, поэтому
        переход 359.5° → 0° — это движение на +0.5°, а не полный оборот
        назад (≈65 с, дольше таймаута RPC).

        Абсолютная позиция контроллера при этом не сбрасывается: команда
        уходит на current_steps + delta_steps, счётчик шагов продолжает расти
        (или убывать) — обнуляет его только set_zero().

        :param position: float — целевой угол в градусах (нормализуется).
        :param blocking: bool — если True (по умолчанию), ждать завершения движения.
        :raises RuntimeError: если команда отклонена контроллером.
        :raises MotorTimeoutError: при blocking=True, если мотор не остановился вовремя.
        """
        logging.debug("HWRotaryMotor.move_to_position_deg() starting...")
        current_steps = self.get_position()
        current_deg = normalize_deg(current_steps / self.steps_on_deg)
        delta_deg = shortest_delta_deg(current_deg, position)
        logging.debug("HWRotaryMotor.move_to_position_deg(): %.4f° -> %.4f° (delta %.4f°)",
                      current_deg, normalize_deg(position), delta_deg)

        steps, usteps = to_steps(current_steps + delta_deg * self.steps_on_deg)
        self.move_to_position(steps, usteps, blocking=blocking)
        logging.debug("HWRotaryMotor.move_to_position_deg() finished.")

    def move_by_delta_deg(self, position, blocking=True):
        """
        Повернуть мотор на относительное смещение в градусах.

        :param position: float — смещение в градусах (может быть отрицательным).
        :param blocking: bool — если True (по умолчанию), ждать завершения движения.
        :raises RuntimeError: если команда отклонена контроллером.
        """
        logging.debug("HWRotaryMotor.move_by_delta_deg() starting...")
        steps, usteps = self._deg_to_steps(position)
        self.move_by_delta(steps, usteps, blocking=blocking)
        logging.debug("HWRotaryMotor.move_by_delta_deg() finished.")

    # ─── State ───────────────────────────────────────────────────────────────────

    #: 'position' — угол в градусах [0, 360).
    STATE_KEYS = ('device_name', 'steps_on_deg', 'speed', 'acceleration', 'position')

    def _state_value(self, option):
        if option == 'position':
            return self.get_position_deg()
        return super()._state_value(option)


class HWLinearMotor(BaseMotor):
    """
    Линейный мотор (горизонтальный).

    Расширяет :class:`BaseMotor` методами работы с миллиметрами.
    Используется для горизонтального перемещения образца (вынос из рентгеновского пучка).

    Пример::

        motor = HWLinearMotor('xi-com:///dev/ximc/00000271',
                              speed=200, acceleration=200,
                              steps_per_mm=199.46,    # 1 шаг = 5.0136 мкм
                              move_outside_mm=-21.06) # позиция парковки
        motor.move_outside()                 # вывести объект из пучка
        motor.move_to_position(0)            # вернуть в пучок
        pos_mm = motor.get_position_mm()     # текущая позиция в мм
    """

    def __init__(self, device_name, speed, acceleration, steps_per_mm, move_outside_mm=0.0):
        """
        :param device_name: str | bytes — имя устройства (порт).
        :param speed: int — скорость в шагах/с.
        :param acceleration: int — ускорение в шагах/с².
        :param steps_per_mm: float — число шагов на миллиметр перемещения.
                             Например: 1 шаг = 5.0136 мкм → steps_per_mm = 199.46.
        :param move_outside_mm: float — расстояние (мм) для вывода объекта из рентгеновского пучка
                                (позиция парковки). Обычно отрицательное значение.
        """
        self.steps_per_mm = float(steps_per_mm)
        self.move_outside_mm = float(move_outside_mm)
        super().__init__(device_name, speed, acceleration)

    # ─── Internal helpers ────────────────────────────────────────────────────────

    def _mm_to_steps(self, mm):
        """
        Перевести миллиметры в шаги и микрошаги — единственное место перевода.

        :param mm: float — расстояние в миллиметрах.
        :return: tuple (steps: int, usteps: int) — знаки частей совпадают, |usteps| <= 255.
        """
        return to_steps(float(mm) * self.steps_per_mm)

    def _steps_to_mm(self, steps):
        """Перевести (дробные) шаги в миллиметры — обратная операция к _mm_to_steps."""
        return float(steps) / self.steps_per_mm

    # ─── Position ────────────────────────────────────────────────────────────────

    def get_position_mm(self):
        """
        Получить текущую абсолютную позицию мотора в миллиметрах.

        Тонкая обёртка над :meth:`get_position` (шаги) — основной единицей
        публичного API остаются шаги, как их использует Flask-слой.

        :return: float — позиция в мм.
        :raises RuntimeError: если запрос к контроллеру завершился с ошибкой.
        """
        logging.debug("HWLinearMotor.get_position_mm() starting...")
        res = self._steps_to_mm(self.get_position())
        logging.debug("HWLinearMotor.get_position_mm() finished.")
        return res

    # ─── Movement ────────────────────────────────────────────────────────────────

    def move_to_position_mm(self, mm, blocking=True):
        """
        Переместить мотор на абсолютную позицию в миллиметрах.

        :param mm: float — целевая позиция в мм.
        :param blocking: bool — если True (по умолчанию), ждать завершения движения.
        :raises RuntimeError: если команда отклонена контроллером.
        """
        logging.debug("HWLinearMotor.move_to_position_mm() starting...")
        steps, usteps = self._mm_to_steps(mm)
        self.move_to_position(steps, usteps, blocking=blocking)
        logging.debug("HWLinearMotor.move_to_position_mm() finished.")

    def move_by_delta_mm(self, mm, blocking=True):
        """
        Переместить мотор на относительное смещение в миллиметрах.

        :param mm: float — смещение в мм (может быть отрицательным).
        :param blocking: bool — если True (по умолчанию), ждать завершения движения.
        :raises RuntimeError: если команда отклонена контроллером.
        """
        logging.debug("HWLinearMotor.move_by_delta_mm() starting...")
        steps, usteps = self._mm_to_steps(mm)
        self.move_by_delta(steps, usteps, blocking=blocking)
        logging.debug("HWLinearMotor.move_by_delta_mm() finished.")

    def move_outside(self, blocking=True):
        """
        Переместить мотор в позицию парковки объекта (вынос из рентгеновского пучка).

        Целевая позиция задаётся в конфиге в миллиметрах (move_outside_mm) и
        переводится в шаги через тот же _mm_to_steps, что и остальной мм-слой.
        Возврат в пучок выполняет прод через move_to_position(0) — в шагах,
        то есть обе операции идут по одной шкале контроллера.

        :param blocking: bool — если True (по умолчанию), ждать завершения движения.
        :raises RuntimeError: если команда отклонена контроллером.
        """
        logging.debug("HWLinearMotor.move_outside() starting...")
        self.move_to_position_mm(self.move_outside_mm, blocking=blocking)
        logging.debug("HWLinearMotor.move_outside() finished.")

    # ─── State ───────────────────────────────────────────────────────────────────

    #: 'position' — в шагах (основная единица публичного API),
    #: 'position_mm' — та же позиция в миллиметрах.
    STATE_KEYS = ('device_name', 'steps_per_mm', 'move_outside_mm',
                  'speed', 'acceleration', 'position', 'position_mm')

    def _state_value(self, option):
        if option == 'position_mm':
            return self.get_position_mm()
        return super()._state_value(option)
