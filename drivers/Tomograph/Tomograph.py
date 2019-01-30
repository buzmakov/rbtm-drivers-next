from ..XRayShutter import XRayShutter
from ..XRaySource import XRaySource
from ..utils import get_shutter_config, get_source_config


class Tomograph(object):
    def __init__(self):
        self.devices = self.init_devices()

    def init_devices(self):
        shutter_config = get_shutter_config()
        shutter = XRayShutter.HWShutter(
            shutter_config["port"],
            shutter_config["relay_number"]
        )

        source_config = get_source_config()
        source = XRaySource.HWSource(
            source_config["port"]
        )
        # TODO: add motors and detector

        return {'shutter': shutter,
                'source': source}

    def get_state(self, devices=None):
        if devices is None:
            devices = {k: None for k in self.devices}
        res = {}

        for device in devices:
            if device in self.devices:
                tomo_device = self.devices[device]
                state = tomo_device.get_state(devices[device])
                res[device] = state

        return res

    def set_state(self, options):
        pass
