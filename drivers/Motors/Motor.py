import logging
import atexit
import numpy as np
try:
    from .pyximc import lib, get_position_t, byref, Result, cast, POINTER, c_int, create_string_buffer, \
        EnumerateFlags, controller_name_t, device_information_t, string_at, edges_settings_t, engine_settings_t, \
        MicrostepMode, status_t, power_settings_t, move_settings_t
except ImportError as err:
    logging.error("Can't import pyximc module. The most probable reason is that you haven't copied pyximc.py to the "
                  "working directory. See developers' documentation for details.")
    exit()
except OSError as err:
    logging.error("Can't load libximc library. Please add all shared libraries to the appropriate places (next to "
                  "pyximc.py on Windows). It is decribed in detail in developers' documentation. On Linux make sure "
                  "you installed libximc-dev package.")
    exit()


class HWMotor(object):
    # TODO: архитектурная проблема — HWMotor используется и для вращательных (угловых),
    #       и для линейных (горизонтальных) моторов, что приводит к путанице в параметрах.
    #       steps_on_deg имеет смысл только для вращательных моторов.
    #       Требуется рефакторинг на отдельные классы HWRotaryMotor / HWLinearMotor.

    def __init__(self, device_name, speed, acceleration, steps_on_deg=None):
        """
        Инициализация и открытие устройства мотора.

        :param device_name: str | bytes — имя устройства (порт), например 'xi-com:///dev/ximc/0000037A'.
        :param speed: int — скорость движения в шагах/с (записывается в контроллер при открытии).
        :param acceleration: int — ускорение/торможение в шагах/с² (записывается в контроллер при открытии).
        :param steps_on_deg: float | None — число шагов на один градус поворота.
                             Только для вращательных моторов.
                             None — для линейных моторов; вызов deg-методов при None вызовет RuntimeError.
        """
        self.device_name = device_name
        # steps_on_deg имеет смысл только для вращательных моторов; для линейных — None
        self.steps_on_deg = float(steps_on_deg) if steps_on_deg is not None else None
        self.speed = int(speed)
        self.acceleration = int(acceleration)
        self.open()
        atexit.register(self.close)

    # ─── Internal helpers ────────────────────────────────────────────────────────

    def _check_rotary(self, method_name):
        """
        Проверить, что мотор вращательный (steps_on_deg не None).
        :raises RuntimeError: если мотор линейный и метод не применим.
        """
        if self.steps_on_deg is None:
            raise RuntimeError(
                "Motor.{}() is only valid for rotary motors (steps_on_deg is None). "
                "See TODO in HWMotor class about HWRotaryMotor / HWLinearMotor refactoring.".format(method_name)
            )

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
        if device_id == -1:  # lib.device_undefined: #TODO: checkit
            logging.error("Motor.open(): open failed")
            raise RuntimeError("Motor.open(): open failed")

        # Отключить граничные флаги (без аппаратных концевых выключателей)
        edges_settings = edges_settings_t()
        result = lib.get_edges_settings(device_id, byref(edges_settings))
        if not result == Result.Ok:
            logging.error("Motor.get_edges_settings() error: {}".format(result))
            logging.debug("Motor.open() failed")
            raise RuntimeError("Motor.get_edges_settings() error: {}".format(result))

        edges_settings.BorderFlags = 0
        result = lib.set_edges_settings(device_id, byref(edges_settings))
        if not result == Result.Ok:
            logging.error("Motor.set_edges_settings() error: {}".format(result))
            logging.debug("Motor.open() failed")
            raise RuntimeError("Motor.set_edges_settings() error: {}".format(result))

        # Отключить удерживающий ток (мотор не греется в покое)
        power_settings = power_settings_t()
        result = lib.get_power_settings(device_id, byref(power_settings))
        if not result == Result.Ok:
            logging.error("Motor.get_power_settings() error: {}".format(result))
            logging.debug("Motor.open() failed")
            raise RuntimeError("Motor.get_power_settings() error: {}".format(result))

        power_settings.HoldCurrent = 0
        result = lib.set_power_settings(device_id, byref(power_settings))
        if not result == Result.Ok:
            logging.error("Motor.set_power_settings() error: {}".format(result))
            logging.debug("Motor.open() failed")
            raise RuntimeError("Motor.set_power_settings() error: {}".format(result))

        # Применить скорость и ускорение из конфигурации к контроллеру
        move_settings = move_settings_t()
        result = lib.get_move_settings(device_id, byref(move_settings))
        if not result == Result.Ok:
            logging.error("Motor.get_move_settings() error: {}".format(result))
            logging.debug("Motor.open() failed")
            raise RuntimeError("Motor.get_move_settings() error: {}".format(result))

        move_settings.Speed = self.speed
        move_settings.Accel = self.acceleration
        move_settings.Decel = self.acceleration
        result = lib.set_move_settings(device_id, byref(move_settings))
        if not result == Result.Ok:
            logging.error("Motor.set_move_settings() error: {}".format(result))
            logging.debug("Motor.open() failed")
            raise RuntimeError("Motor.set_move_settings() error: {}".format(result))

        self.set_microstep_mode_256()

        logging.debug("Motor.open() finished")

    def close(self):
        """
        Закрыть устройство и освободить ресурс контроллера.
        Вызывается автоматически при завершении программы через atexit.
        :return: код результата libximc (Result.Ok = 0).
        """
        result_code = lib.close_device(byref(cast(self.device_id, POINTER(c_int))))
        if result_code != Result.Ok:
            logging.error("Motor.close() error: {}".format(result_code))
        return result_code

    # ─── Info / status ───────────────────────────────────────────────────────────

    def get_info(self):
        """
        Получить информацию о производителе и версии прошивки контроллера.

        :return: dict с ключами:
                 Manufacturer, ManufacturerId, ProductDescription, Major, Minor, Release, error.
        :raises RuntimeError: если запрос завершился с ошибкой.
        """
        logging.debug("Get device info")
        x_device_information = device_information_t()
        result = lib.get_device_information(self.device_id, byref(x_device_information))
        logging.debug("Motor.get_info() result: " + repr(result))
        res = {}
        if result == Result.Ok:
            res["Manufacturer"] = repr(string_at(x_device_information.Manufacturer).decode())
            res["ManufacturerId"] = repr(string_at(x_device_information.ManufacturerId).decode())
            res["ProductDescription"] = repr(string_at(x_device_information.ProductDescription).decode())
            res["Major"] = repr(x_device_information.Major)
            res["Minor"] = repr(x_device_information.Minor)
            res["Release"] = repr(x_device_information.Release)
            res["error"] = None
        else:
            logging.error("Motor.get_info() error: {}".format(result))
            raise RuntimeError("Motor.get_info() error: {}".format(result))
        return res

    def get_power_info(self):
        """
        Получить настройки питания контроллера (удерживающий ток, задержки, флаги).

        :return: dict с ключами:
                 Power.HoldCurrent, Power.CurrReductDelay, Power.PowerOffDelay,
                 Power.CurrentSetTime, Power.PowerFlags.
        :raises RuntimeError: если запрос завершился с ошибкой.
        """
        logging.debug("Get device power info")
        power_settings = power_settings_t()
        result = lib.get_power_settings(self.device_id, byref(power_settings))
        logging.debug("Motor.get_power_info() result: " + repr(result))
        res = {}
        if result == Result.Ok:
            res["Power.HoldCurrent"] = repr(power_settings.HoldCurrent)
            res["Power.CurrReductDelay"] = repr(power_settings.CurrReductDelay)
            res["Power.PowerOffDelay"] = repr(power_settings.PowerOffDelay)
            res["Power.CurrentSetTime"] = repr(power_settings.CurrentSetTime)
            res["Power.PowerFlags"] = repr(bin(power_settings.PowerFlags))
        else:
            logging.error("Motor.get_power_info() error: {}".format(result))
            raise RuntimeError("Motor.get_power_info() error: {}".format(result))
        return res

    def get_status(self):
        """
        Получить текущий статус контроллера (ток двигателя, напряжение питания, флаги состояния).

        :return: dict с ключами:
                 Status.Ipwr (ток двигателя, мА),
                 Status.Upwr (напряжение питания, мВ),
                 Status.Iusb (ток USB, мА),
                 Status.Flags (битовые флаги StateFlags).
        :raises RuntimeError: если запрос завершился с ошибкой.
        """
        logging.debug("Get status")
        x_status = status_t()
        result = lib.get_status(self.device_id, byref(x_status))
        res = {}
        if result == Result.Ok:
            res["Status.Ipwr"] = repr(x_status.Ipwr)
            res["Status.Upwr"] = repr(x_status.Upwr)
            res["Status.Iusb"] = repr(x_status.Iusb)
            res["Status.Flags"] = repr(bin(x_status.Flags))
        else:
            logging.error("Motor.get_status() error: {}".format(result))
            raise RuntimeError("Motor.get_status() error: {}".format(result))
        return res

    # ─── Position ────────────────────────────────────────────────────────────────

    def get_position(self):
        """
        Получить текущую абсолютную позицию мотора в шагах с учётом микрошага.

        :return: float — позиция = Position + uPosition / 256.
        :raises RuntimeError: если запрос завершился с ошибкой.
        """
        logging.debug("Motor.get_position() starting...")
        x_pos = get_position_t()
        result = lib.get_position(self.device_id, byref(x_pos))
        if result == Result.Ok:
            res = x_pos.Position + x_pos.uPosition / 256.
        else:
            logging.error("Motor.get_position() error: {}".format(result))
            raise RuntimeError("Motor.get_position() error: {}".format(result))
        logging.debug("Motor.get_position() finished.")
        return res

    def get_position_deg(self):
        """
        Получить текущую абсолютную позицию вращательного мотора в градусах.
        Только для вращательных моторов (steps_on_deg is not None).

        :return: float — угол в градусах.
        :raises RuntimeError: если вызван для линейного мотора (steps_on_deg is None).
        """
        logging.debug("Motor.get_position_deg() starting...")
        self._check_rotary("get_position_deg")
        res = self.get_position() / self.steps_on_deg
        logging.debug("Motor.get_position_deg() finished.")
        return res

    # ─── Movement ────────────────────────────────────────────────────────────────

    def move_to_position(self, position, uposition=0, blocking=True):
        """
        Переместить мотор на абсолютную позицию в шагах.

        :param position: int — целая часть позиции в шагах.
        :param uposition: int — дробная часть позиции в микрошагах [0, 255].
        :param blocking: bool — если True (по умолчанию), блокировать поток до завершения движения
                         (command_wait_for_stop). Передавайте False для ручного управления со
                         страницы юстировки, чтобы Redis-сервер оставался отзывчивым.
        :raises RuntimeError: если команда отклонена контроллером.
        """
        logging.debug("Motor.move_to_position() starting...")
        result = lib.command_move(self.device_id, position, uposition)
        if not result == Result.Ok:
            logging.error("Motor.move_to_position() error: {}".format(result))
            raise RuntimeError("Motor.move_to_position() error: {}".format(result))

        if blocking:
            lib.command_wait_for_stop(self.device_id, 10)
        logging.debug("Motor.move_to_position() finished.")

    def move_to_position_deg(self, position, blocking=True):
        """
        Переместить вращательный мотор на абсолютную позицию в градусах.
        Только для вращательных моторов (steps_on_deg is not None).

        Дробная часть угла корректно конвертируется в микрошаги uPosition ∈ [0, 255].

        :param position: float — угловая позиция в градусах.
        :param blocking: bool — если True (по умолчанию), ждать завершения движения.
        :raises RuntimeError: если вызван для линейного мотора или команда отклонена.
        """
        logging.debug("Motor.move_to_position_grad() starting...")
        self._check_rotary("move_to_position_deg")
        total = position * self.steps_on_deg
        steps = int(np.floor(total))
        usteps = int((total - steps) * 256)  # [0, 255]
        self.move_to_position(steps, usteps, blocking=blocking)
        logging.debug("Motor.move_to_position_grad() finished...")

    def move_by_delta(self, step, ustep=0, blocking=True):
        """
        Переместить мотор на относительное смещение в шагах.

        :param step: int — смещение в целых шагах (может быть отрицательным).
        :param ustep: int — дробная часть смещения в микрошагах [0, 255].
        :param blocking: bool — если True (по умолчанию), ждать завершения движения.
        :raises RuntimeError: если команда отклонена контроллером.
        """
        logging.debug("Motor.move_by_delta() starting...")
        result = lib.command_movr(self.device_id, step, ustep)
        if not result == Result.Ok:
            logging.error("Motor.move_by_delta() error: {}".format(result))
            raise RuntimeError("Motor.move_by_delta() error: {}".format(result))

        if blocking:
            lib.command_wait_for_stop(self.device_id, 10)
        logging.debug("Motor.move_by_delta() finished")

    def move_by_delta_deg(self, position, blocking=True):
        """
        Повернуть вращательный мотор на относительное смещение в градусах.
        Только для вращательных моторов (steps_on_deg is not None).

        :param position: float — смещение в градусах (может быть отрицательным).
        :param blocking: bool — если True (по умолчанию), ждать завершения движения.
        :raises RuntimeError: если вызван для линейного мотора или команда отклонена.
        """
        logging.debug("Motor.move_by_delta_grad() starting...")
        self._check_rotary("move_by_delta_deg")
        total = position * self.steps_on_deg
        steps = int(np.floor(total))
        usteps = int((total - steps) * 256)  # [0, 255]
        self.move_by_delta(steps, usteps, blocking=blocking)
        logging.debug("Motor.move_by_delta_grad() finished...")

    # ─── Calibration / configuration ─────────────────────────────────────────────

    def set_zero(self, blocking=True):
        """
        Объявить текущую позицию нулём (home position).

        :param blocking: bool — если True (по умолчанию), ждать завершения команды.
        :raises RuntimeError: если команда отклонена контроллером.
        """
        logging.debug("Motor.set_zero() starting...")
        result = lib.command_zero(self.device_id)
        if not result == Result.Ok:
            logging.error("Motor.set_zero() error: {}".format(result))
            raise RuntimeError("Motor.set_zero() error: {}".format(result))
        if blocking:
            lib.command_wait_for_stop(self.device_id, 10)
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

    # ─── State ───────────────────────────────────────────────────────────────────

    def get_state(self, options=None):
        """
        Получить состояние мотора по запрошенным параметрам.

        :param options: list[str] | str | None — список запрашиваемых параметров.
                        Допустимые значения: 'device_name', 'steps_on_deg', 'speed',
                        'acceleration', 'position'.
                        None — вернуть все параметры (по умолчанию).
                        Для линейных моторов (steps_on_deg is None) 'position'
                        возвращает значение в шагах, а не в градусах.
        :return: dict {option: value, ...}. Неизвестные опции возвращают {'error': ...}.
        """
        if options is None:
            options = ['device_name', 'steps_on_deg',
                       'speed', 'acceleration', 'position']
        res = {}
        if not isinstance(options, (list, tuple)):
            options = [options, ]

        for option in options:
            if option == 'device_name':
                s = self.device_name
            elif option == 'steps_on_deg':
                s = self.steps_on_deg
            elif option == 'speed':
                s = self.speed
            elif option == 'acceleration':
                s = self.acceleration
            elif option == 'position':
                # Для вращательного мотора — в градусах, для линейного — в шагах
                s = self.get_position_deg() if self.steps_on_deg is not None else self.get_position()
            else:
                s = {'error': 'Unsupported option {}'.format(option)}
            res[option] = s
        return res


# TODO: add get/set status

def print_test_info():
    print("Library loaded")
    sbuf = create_string_buffer(64)
    lib.ximc_version(sbuf)
    print("Library version: " + sbuf.raw.decode())

    # This is device search and enumeration with probing. It gives more information about devices.
    devenum = lib.enumerate_devices(EnumerateFlags.ENUMERATE_PROBE, None)
    print("Device enum handle: " + repr(devenum))
    print("Device enum handle type: " + repr(type(devenum)))

    dev_count = lib.get_device_count(devenum)
    print("Device count: " + repr(dev_count))

    controller_name = controller_name_t()
    for dev_ind in range(0, dev_count):
        enum_name = lib.get_device_name(devenum, dev_ind)
        result = lib.get_enumerate_device_controller_name(
            devenum, dev_ind, byref(controller_name))
        if result == Result.Ok:
            print("Enumerated device #{} name (port name): ".format(
                dev_ind) + repr(enum_name) + ". Friendly name: " + repr(controller_name.ControllerName) + ".")
