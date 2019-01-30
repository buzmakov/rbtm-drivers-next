import logging


try:
    from pyximc import lib, get_position_t, byref, Result, cast, POINTER, c_int, create_string_buffer, EnumerateFlags, controller_name_t
except ImportError as err:
    logging.error("Can't import pyximc module. The most probable reason is that you haven't copied pyximc.py to the working directory. See developers' documentation for details.")
    exit()
except OSError as err:
    logging.error("Can't load libximc library. Please add all shared libraries to the appropriate places (next to pyximc.py on Windows). It is decribed in detail in developers' documentation. On Linux make sure you installed libximc-dev package.")
    exit()


class Motor(object):
    def __init__(self, device_name, steps_on_deg, speed, acceleration):
        self.device_name = device_name
        self.steps_on_deg = steps_on_deg
        self.speed = speed
        self.acceleration = acceleration

    def open(self):
        device_id = lib.open_device(self.device_name)

        if device_id == lib.device_undefined:
            logging.error("Motor.open(): open failed")

        edges_settings = lib.get_edges_settings(device_id)
        edges_settings.BorderFlags = 0
        lib.set_edges_settings(device_id, edges_settings)

        return device_id

    def close(self, device_id):
        result_code = lib.close_device(byref(cast(device_id, POINTER(c_int))))
        return result_code

    def get_position(self):
        logging.debug("Motor.get_position() starting...")
        device_id = self.open()
        x_pos = get_position_t()
        result = lib.get_position(device_id, byref(x_pos))
        res = {}
        if result == Result.Ok:
            res['position'] = x_pos.Position
            res['error'] = None
        else:
            res['error'] = result
            logging.error("Motor.get_position() error: {}".format(result))

        self.close(device_id)
        logging.debug("Motor.get_position() finished.")
        return res

    def move_to_position(self, position, uposition=0):
        logging.debug("Motor.move_to_position() starting...")
        device_id = self.open()
        result = lib.command_move(device_id, position, uposition)
        res = {}
        if result == Result.Ok:
            res['error'] = None
        else:
            res['error'] = result
            logging.error("Motor.move_to_position() error: {}".format(result))
        lib.command_wait_for_stop(device_id, 10)
        self.close(device_id)
        logging.debug("Motor.move_to_position() finished.")
        return res

    def move_by_delta(self, step, ustep=0):
        logging.debug("Motormove_by_delta() starting...")
        device_id = self.open()
        result = lib.command_movr(device_id, step, ustep)
        res = {}
        if result == Result.Ok:
            res['error'] = None
        else:
            res['error'] = result
            logging.error("Motor.move_by_delta() error: {}".format(result))
        lib.command_wait_for_stop(device_id, 10)
        self.close(device_id)
        logging.debug("Motor.move_by_delta() finished")
        return res

    def set_zero(self):
        logging.debug("Motor.set_zero() starting...")
        device_id = self.open()
        result = lib.command_zero(device_id)
        res = {}
        if result == Result.Ok:
            res['error'] = None
        else:
            res['error'] = result
            logging.error("Motor.set_zero() error: {}".format(result))
        lib.command_wait_for_stop(device_id, 10)
        self.close(device_id)
        logging.debug("Motor.set_zero() finished")
        return res


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
