import logging


try:
    from .pyximc import lib, get_position_t, byref, Result, cast, POINTER, c_int, create_string_buffer, EnumerateFlags, \
        controller_name_t, device_information_t, string_at, edges_settings_t
except ImportError as err:
    logging.error("Can't import pyximc module. The most probable reason is that you haven't copied pyximc.py to the working directory. See developers' documentation for details.")
    exit()
except OSError as err:
    logging.error("Can't load libximc library. Please add all shared libraries to the appropriate places (next to pyximc.py on Windows). It is decribed in detail in developers' documentation. On Linux make sure you installed libximc-dev package.")
    exit()


class HWMotor(object):
    def __init__(self, device_name, steps_on_deg, speed, acceleration):
        self.device_name = device_name
        self.steps_on_deg = steps_on_deg
        self.speed = speed
        self.acceleration = acceleration

    def open(self):
        if type(self.device_name) is str:
            open_name = self.device_name.encode()
        else:
            open_name = self.device_name

        device_id = lib.open_device(open_name)
        if device_id == -1: # lib.device_undefined: #TODO: checkit
            logging.error("Motor.open(): open failed")

        edges_settings = edges_settings_t()
        result = lib.get_edges_settings(device_id, byref(edges_settings))
        if not result == Result.Ok:
            logging.error("Motor.get_edges_settings() error: {}".format(result))
            #TODO: exit from here
        edges_settings.BorderFlags = 0
        result = lib.set_edges_settings(device_id, byref(edges_settings))
        if not result == Result.Ok:
            logging.error("Motor.set_edges_settings() error: {}".format(result))
            #TODO: exit from here
        self.device_id = device_id

    def test_info(self):
        print("\nGet device info")
        x_device_information = device_information_t()
        result = lib.get_device_information(self.device_id, byref(x_device_information))
        print("Result: " + repr(result))
        if result == Result.Ok:
            print("Device information:")
            print(" Manufacturer: " +
                  repr(string_at(x_device_information.Manufacturer).decode()))
            print(" ManufacturerId: " +
                  repr(string_at(x_device_information.ManufacturerId).decode()))
            print(" ProductDescription: " +
                  repr(string_at(x_device_information.ProductDescription).decode()))
            print(" Major: " + repr(x_device_information.Major))
            print(" Minor: " + repr(x_device_information.Minor))
            print(" Release: " + repr(x_device_information.Release))

    def close(self):
        result_code = lib.close_device(byref(cast(self.device_id, POINTER(c_int))))
        return result_code

    def get_position(self):
        logging.debug("Motor.get_position() starting...")
        x_pos = get_position_t()
        result = lib.get_position(self.device_id, byref(x_pos))
        res = {}
        if result == Result.Ok:
            res['position'] = x_pos.Position
            res['error'] = None
        else:
            res['error'] = result
            logging.error("Motor.get_position() error: {}".format(result))

        logging.debug("Motor.get_position() finished.")
        return res

    def move_to_position(self, position, uposition=0):
        logging.debug("Motor.move_to_position() starting...")
        result = lib.command_move(self.device_id, position, uposition)
        res = {}
        if result == Result.Ok:
            res['error'] = None
        else:
            res['error'] = result
            logging.error("Motor.move_to_position() error: {}".format(result))
        lib.command_wait_for_stop(self.device_id, 10)
        logging.debug("Motor.move_to_position() finished.")
        return res

    def move_by_delta(self, step, ustep=0):
        logging.debug("Motormove_by_delta() starting...")
        result = lib.command_movr(self.device_id, step, ustep)
        res = {}
        if result == Result.Ok:
            res['error'] = None
        else:
            res['error'] = result
            logging.error("Motor.move_by_delta() error: {}".format(result))
        lib.command_wait_for_stop(self.device_id, 10)
        logging.debug("Motor.move_by_delta() finished")
        return res

    def set_zero(self):
        logging.debug("Motor.set_zero() starting...")
        result = lib.command_zero(self.device_id)
        res = {}
        if result == Result.Ok:
            res['error'] = None
        else:
            res['error'] = result
            logging.error("Motor.set_zero() error: {}".format(result))
        lib.command_wait_for_stop(self.device_id, 10)
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
