"""
Конфигурация pytest для тестов оборудования.

Автоматически пропускает тесты источника, если serial-порт недоступен
(нет прав или устройство не подключено).

Решение проблемы доступа к serial-порту:
  Вариант A (рекомендуется):
    sudo usermod -a -G dialout $USER
    # перелогиниться, затем:
    pytest --log-cli-level=INFO -s -v drivers/tests/test_source.py

  Вариант B (запуск внутри контейнера с доступом к устройству):
    docker exec -it rbtm-tomograph-server \
      python -m pytest /xtomo/drivers/tests/test_source.py -v -s

  Вариант C (если уже сделан usermod, но тест не находит модуль):
    PYTHONPATH=/xtomo pytest --log-cli-level=INFO -s -v drivers/tests/test_source.py
"""
import pytest
import serial
from ..utils import get_source_config


def _source_port_accessible():
    """Проверить, доступен ли serial-порт источника."""
    try:
        config = get_source_config()
        port = config.get('port', '/dev/ttyUSB0')
        s = serial.Serial(port, baudrate=9600, timeout=1)
        s.close()
        return True, port
    except serial.SerialException as e:
        return False, str(e)
    except Exception as e:
        return False, str(e)


def pytest_collection_modifyitems(config, items):
    """Добавляет маркер skip к тестам источника если порт недоступен."""
    accessible, reason = _source_port_accessible()
    if accessible:
        return

    skip_mark = pytest.mark.skip(
        reason=(
            "Serial port not accessible: {}. "
            "Fix: sudo usermod -a -G dialout $USER (then re-login). "
            "Or run inside Docker: docker exec -it rbtm-tomograph-server "
            "python -m pytest /xtomo/drivers/tests/test_source.py -v -s"
        ).format(reason)
    )

    for item in items:
        if "test_source" in item.nodeid:
            item.add_marker(skip_mark)
