# pytest --log-cli-level=INFO -s -v test_source.py
import logging
from ..XRaySource.XRaySource import HWSource
from ..utils import get_source_config


def test_source_connection():
    """Проверка подключения к рентгеновскому источнику без включения ВН.

    Проверяет:
    - get_id() возвращает непустую строку идентификатора генератора.
    - get_tube_name() возвращает непустую строку наименования трубки.
    - get_status() возвращает словарь с ожидаемой структурой:
        'power status', 'warming status', 'interlock status'.
    - Значения в каждом подсловаре — bool.
    - Логируются состояние блокировок (двери, аварийный стоп) и ВН.
    """
    config = get_source_config()
    logging.info("Source config: %s", config)

    s = HWSource(config['port'])

    device_id = s.get_id()
    logging.info("Generator ID: %s", device_id)
    assert isinstance(device_id, str) and len(device_id) > 0, \
        "get_id() должен вернуть непустую строку"

    tube_name = s.get_tube_name()
    logging.info("Tube name: %s", tube_name)
    assert isinstance(tube_name, str) and len(tube_name) > 0, \
        "get_tube_name() должен вернуть непустую строку"

    status = s.get_status()
    logging.info("Full status: %s", status)

    expected_sections = ('power status', 'warming status', 'interlock status')
    for section in expected_sections:
        assert section in status, \
            "get_status() должен содержать раздел '{}'".format(section)
        assert isinstance(status[section], dict), \
            "Раздел '{}' должен быть dict".format(section)

    # Все значения в статусе должны быть bool
    for section, fields in status.items():
        for field, value in fields.items():
            assert isinstance(value, bool), \
                "status['{}']['{}'] должен быть bool, получено: {} ({})".format(
                    section, field, value, type(value))

    interlock = status['interlock status']
    logging.info(
        "Interlock: door1=%s, door2=%s, extern_stop=%s, emergency_stop=%s",
        interlock['door 1 ok'], interlock['door 2 ok'],
        interlock['extern stop ok'], interlock['emergency stop ok'],
    )

    hv_on = s.is_on_high_voltage()
    logging.info("High voltage on: %s", hv_on)
    assert isinstance(hv_on, bool), \
        "is_on_high_voltage() должен вернуть bool"

    last_error = s.get_error()
    logging.info("Last error: %s", last_error)
    # last_error может быть None (нет ошибок) или dict с кодом и сообщением
    if last_error is not None:
        assert 'code' in last_error and 'message' in last_error, \
            "get_error() должен вернуть dict с ключами 'code' и 'message'"
        logging.warning("Source reports error: %s", last_error)
