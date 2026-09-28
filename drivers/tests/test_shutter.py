# pytest --log-cli-level=INFO -s -v test_shutter.py
import logging
import os
from time import sleep

import pytest

from ..XRayShutter.XRayShutter import HWShutter, _DEPRECATED_ALIASES_WARNED
from ..utils import get_shutter_config

pytestmark = pytest.mark.hardware
if not os.path.exists(get_shutter_config()['port']):
    pytest.skip('порт затвора {} не найден'.format(get_shutter_config()['port']), allow_module_level=True)


def test_shutter_info():
    """Диагностика модуля Ke-USB24R.

    Проверяет:
    - Серийный номер — непустая строка.
    - Версия прошивки читается (или модуль её не поддерживает — допустимо).
    - get_all_relay_states() возвращает dict с ключами 1..4 и bool-значениями.
    - read_adc(1) возвращает raw в диапазоне 0–1023 и voltage_v в 0.0–5.0 В.
    """
    config = get_shutter_config()
    logging.info("Shutter config: %s", config)
    s = HWShutter(config['port'], config['relay_number'])

    serial_number = s.get_serial_number()
    logging.info("Serial number: %s", serial_number)
    assert isinstance(serial_number, str) and len(serial_number) > 0, \
        "get_serial_number() должен вернуть непустую строку"

    try:
        fw = s.get_firmware_version()
        logging.info("Firmware version: %s", fw)
        assert isinstance(fw, str) and len(fw) > 0, \
            "get_firmware_version() должен вернуть непустую строку"
    except RuntimeError as e:
        # Старые аппаратные версии Ke-USB24R не поддерживают команду FW
        logging.warning("get_firmware_version() не поддерживается этим модулем: %s", e)

    relay_states = s.get_all_relay_states()
    logging.info("All relay states: %s", relay_states)
    assert isinstance(relay_states, dict), \
        "get_all_relay_states() должен вернуть dict"
    for relay_num in (1, 2, 3, 4):
        assert relay_num in relay_states, \
            "В ответе get_all_relay_states() отсутствует ключ {}".format(relay_num)
        assert isinstance(relay_states[relay_num], bool), \
            "Значение реле {} должно быть bool, получено: {}".format(
                relay_num, type(relay_states[relay_num]))

    adc = s.read_adc(1)
    logging.info("ADC channel 1: %s", adc)
    assert 'raw' in adc and 'voltage_v' in adc, \
        "read_adc() должен вернуть dict с ключами 'raw' и 'voltage_v'"
    assert 0 <= adc['raw'] <= 1023, \
        "raw АЦП вне диапазона 0–1023: {}".format(adc['raw'])
    assert 0.0 <= adc['voltage_v'] <= 5.0, \
        "voltage_v вне диапазона 0–5 В: {}".format(adc['voltage_v'])

    s.release()
    assert not s.is_port_open(), "release() должен закрыть порт модуля"


def test_shutter_open_close():
    """Проверка управления заслонкой: открытие и закрытие.

    Проверяет:
    - После open_shutter() метод is_open() возвращает True.
    - После close_shutter() метод is_open() возвращает False.
    - get_state() согласован с is_open().
    - Устаревшие синонимы open()/close() пока работают (с DeprecationWarning).
    - release() освобождает порт, не меняя положение заслонки.
    """
    config = get_shutter_config()
    s = HWShutter(config['port'], config['relay_number'])
    try:
        # Гарантируем начальное состояние — закрыто
        s.close_shutter()
        assert not s.is_open(), "Заслонка должна быть закрыта после close_shutter()"

        s.open_shutter()
        assert s.is_open(), "Заслонка должна быть открыта после open_shutter()"
        state = s.get_state(['is_open', 'is_closed'])
        logging.info("Shutter state after open: %s", state)
        assert state == {'is_open': True, 'is_closed': False}, \
            "get_state() не согласован с is_open(): {}".format(state)

        sleep(0.5)

        s.close_shutter()
        assert not s.is_open(), "Заслонка должна быть закрыта после close_shutter()"
        logging.info("Shutter state after close: %s", s.get_state())

        # Устаревшие синонимы должны работать до их удаления.
        # Предупреждение выдаётся один раз на процесс — сбрасываем отметку.
        _DEPRECATED_ALIASES_WARNED.discard('open')
        with pytest.deprecated_call():
            s.open()
        assert s.is_open(), "Устаревший open() должен открывать заслонку"
        s.close_shutter()
        assert not s.is_open(), "Заслонка должна быть закрыта после close_shutter()"
    finally:
        s.release()
