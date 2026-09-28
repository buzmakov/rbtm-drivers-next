"""
Конфигурация pytest для тестов оборудования.

Тесты, которым нужен реальный ISOVOLT, запрашивают фикстуру
``source_port``: она лениво проверяет доступность serial-порта и делает
``skip``, если порта нет или нет прав. Проверка НЕ открывает порт —
каждое открытие дёргает линии DTR/RTS генератора — и не выполняется
на этапе сбора тестов, поэтому offline- и mock-тесты идут везде.

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
import os

import pytest

from ..utils import get_source_config

_FIX_HINT = (
    "Fix: sudo usermod -a -G dialout $USER (then re-login). "
    "Or run inside Docker: docker exec -it rbtm-tomograph-server "
    "python -m pytest /xtomo/drivers/tests/test_source.py -v -s"
)


@pytest.fixture(scope='session')
def source_port():
    """Путь к порту источника; ``skip``, если порта нет или нет прав.

    Порт не открывается: проверяются только наличие файла устройства и
    права на чтение/запись. Открытие оставлено драйверу
    (``HWSource.get_shared()``), чтобы не дёргать DTR лишний раз.
    """
    try:
        port = get_source_config()['port']
    except Exception as e:
        pytest.skip("Cannot read source config: {}".format(e))

    if not os.path.exists(port):
        pytest.skip("Serial port {} does not exist. {}".format(port, _FIX_HINT))
    if not os.access(port, os.R_OK | os.W_OK):
        pytest.skip("No read/write access to {}. {}".format(port, _FIX_HINT))
    return port
