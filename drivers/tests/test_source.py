# Запуск тестов:
#
#   pytest --log-cli-level=INFO -s -v drivers/tests/test_source.py
#
# Если ошибка "Permission denied" для /dev/ttyUSB0:
#   sudo usermod -a -G dialout $USER   # добавить пользователя в группу dialout
#   # перелогиниться, затем повторить
#
# Или запустить внутри Docker-контейнера с доступом к устройству:
#   docker exec -it rbtm-tomograph-server \
#       python -m pytest /xtomo/drivers/tests/test_source.py -v -s
#
import logging
import pytest
from ..XRaySource.XRaySource import HWSource, INTERLOCK_ERROR_CODES
from ..utils import get_source_config


# ── Общая фикстура ────────────────────────────────────────────────────────────

@pytest.fixture(scope='module')
def source():
    """Открыть соединение с реальным источником; закрыть после тестов."""
    config = get_source_config()
    logging.info("Source config: %s", config)
    s = HWSource(config['port'])
    yield s
    # Закрытие через atexit, но явно тоже можно
    try:
        s.close()
    except Exception:
        pass


@pytest.fixture(scope='module')
def source_mock():
    """Источник в mock-режиме — не требует устройства."""
    config = get_source_config()
    return HWSource(config['port'], mock=True)


# ── Mock-тесты (всегда выполняются, без реального порта) ────────────────────

class TestSourceMock:
    """Тесты mock-режима — проверяют что все методы работают без устройства."""

    def test_mock_get_actual_voltage(self, source_mock):
        v = source_mock.get_actual_voltage()
        assert v == 40.0, "mock: get_actual_voltage() должен вернуть 40.0"

    def test_mock_get_actual_current(self, source_mock):
        c = source_mock.get_actual_current()
        assert c == 20.0, "mock: get_actual_current() должен вернуть 20.0"

    def test_mock_get_nominal_voltage(self, source_mock):
        v = source_mock.get_nominal_voltage()
        assert isinstance(v, float)

    def test_mock_is_on_high_voltage(self, source_mock):
        result = source_mock.is_on_high_voltage()
        assert isinstance(result, bool)

    def test_mock_on_off_high_voltage_no_error(self, source_mock):
        """Mock: включение/выключение ВН не должно бросать исключений."""
        source_mock.on_high_voltage()
        source_mock.off_high_voltage()

    def test_mock_warmup_no_error(self, source_mock):
        """Mock: прогрев не должен бросать исключений."""
        source_mock.warmup()

    def test_mock_get_state(self, source_mock):
        state = source_mock.get_state(['actual_voltage', 'actual_current'])
        assert 'actual_voltage' in state
        assert 'actual_current' in state


# ── Интеграционные тесты (требуют реального устройства) ─────────────────────

class TestSourceConnection:
    """Базовая проверка подключения и идентификации."""

    def test_get_id(self, source):
        """get_id() возвращает непустую строку."""
        device_id = source.get_id()
        logging.info("Generator ID: %s", device_id)
        assert isinstance(device_id, str) and len(device_id) > 0, \
            "get_id() должен вернуть непустую строку"

    def test_get_tube_name(self, source):
        """get_tube_name() возвращает непустую строку."""
        tube_name = source.get_tube_name()
        logging.info("Tube name: %s", tube_name)
        assert isinstance(tube_name, str) and len(tube_name) > 0, \
            "get_tube_name() должен вернуть непустую строку"

    def test_get_status_structure(self, source):
        """get_status() возвращает словарь правильной структуры."""
        status = source.get_status()
        logging.info("Full status: %s", status)

        expected_sections = ('power status', 'warming status')
        for section in expected_sections:
            assert section in status, \
                "get_status() должен содержать раздел '{}'".format(section)
            assert isinstance(status[section], dict), \
                "Раздел '{}' должен быть dict".format(section)

        for section, fields in status.items():
            for field, value in fields.items():
                assert isinstance(value, bool), \
                    "status['{}']['{}'] должен быть bool, получено: {} ({})".format(
                        section, field, value, type(value))

    def test_is_on_high_voltage(self, source):
        """is_on_high_voltage() возвращает bool."""
        hv_on = source.is_on_high_voltage()
        logging.info("High voltage on: %s", hv_on)
        assert isinstance(hv_on, bool)

    def test_get_error_format(self, source):
        """get_error() возвращает None или dict с code/message."""
        last_error = source.get_error()
        logging.info("Last error: %s", last_error)
        if last_error is not None:
            assert 'code' in last_error and 'message' in last_error, \
                "get_error() должен вернуть dict с ключами 'code' и 'message'"
            logging.warning("Source reports error code %d: %s",
                            last_error['code'], last_error['message'])


class TestSourceDiagnostics:
    """Диагностика состояния источника: interlock, ошибки, параметры."""

    def test_interlock_status(self, source):
        """Логирование состояния питания/прогрева и цепи блокировок.

        Двери и аварийный останов приходят кодами ошибки SR:12
        (``INTERLOCK_ERROR_CODES``), а не битами SR:30 — см. руководство §8.5.
        """
        status = source.get_status()
        power = status['power status']
        warming = status['warming status']

        logging.info(
            "Power: hv_on=%s cooling_ok=%s battery_ok=%s voltage_norm=%s current_norm=%s",
            power['high voltage on'], power['cooling system ok'],
            power['buffer battery ok'], power['voltage kv norm'],
            power['current ma norm'],
        )
        logging.info(
            "Warming: in_progress=%s interrupted=%s from_pc=%s from_kb=%s",
            warming['in progress'], warming['warming interrupted'],
            warming['warming from pc'], warming['warming from kb'],
        )

        # Если цепь блокировок разомкнута — логируем, но не падаем (это диагностика)
        error = source.get_error()
        if error is not None and error['code'] in INTERLOCK_ERROR_CODES:
            logging.warning("INTERLOCK: code=%d (%s) — HV on will be rejected",
                            error['code'], error['message'])
        else:
            logging.info("Interlock chain: no interlock error code (SR:12 = %s)", error)

    def test_error_code_diagnostics(self, source):
        """Читает текущий код ошибки SR:12 и выводит расшифровку."""
        error = source.get_error()
        if error is None:
            logging.info("No error reported by source (SR:12 = 0)")
        else:
            known = error['code'] in HWSource.STATUS_STRINGS
            logging.warning(
                "Source error: code=%d message='%s' known_in_dict=%s",
                error['code'], error['message'], known,
            )
            if not known:
                logging.warning(
                    "Error code %d not in STATUS_STRINGS — may need to add to driver",
                    error['code'])

    def test_read_all_status_words(self, source):
        """Читает слова состояния SR:01, SR:06, SR:12, SR:30 и логирует."""
        for word in (1, 6, 12, 30):
            val = source.read_status_word(word)
            logging.info("SR:%02d = %d (0x%02x, bin=%s)", word, val, val, bin(val))
            assert isinstance(val, int), "read_status_word({}) должен вернуть int".format(word)


class TestSourceReadings:
    """Чтение параметров источника."""

    def test_get_nominal_voltage(self, source):
        v = source.get_nominal_voltage()
        logging.info("Nominal voltage: %.3f kV", v)
        assert isinstance(v, float)
        assert 0.0 <= v <= 60.0, \
            "Номинальное напряжение должно быть в диапазоне 0-60 кВ, получено: {}".format(v)

    def test_get_nominal_current(self, source):
        c = source.get_nominal_current()
        logging.info("Nominal current: %.3f mA", c)
        assert isinstance(c, float)
        assert 0.0 <= c <= 80.0, \
            "Номинальный ток должен быть в диапазоне 0-80 мА, получено: {}".format(c)

    def test_get_actual_voltage(self, source):
        """get_actual_voltage() не бросает исключений (soft-fail)."""
        v = source.get_actual_voltage()
        logging.info("Actual voltage: %.3f kV", v)
        assert isinstance(v, float), "get_actual_voltage() должен вернуть float"

    def test_get_actual_current(self, source):
        """get_actual_current() не бросает исключений (soft-fail)."""
        c = source.get_actual_current()
        logging.info("Actual current: %.3f mA", c)
        assert isinstance(c, float), "get_actual_current() должен вернуть float"

    def test_get_state_full(self, source):
        """get_state() без аргументов возвращает полный набор параметров."""
        state = source.get_state()
        logging.info("Full state: %s", state)
        expected_keys = [
            'is_on_high_voltage', 'id', 'tube_name',
            'actual_voltage', 'nominal_voltage',
            'actual_current', 'nominal_current',
            'status', 'last_error',
        ]
        for key in expected_keys:
            assert key in state, "get_state() должен содержать ключ '{}'".format(key)


class TestSourceHighVoltage:
    """Тесты включения/выключения ВН.

    Пропускаются автоматически если interlock открыт.
    """

    @pytest.fixture(autouse=True)
    def check_interlock(self, source):
        """Пропустить тест, если цепь блокировок не даст включить ВН.

        Состояние дверей и аварийного останова читается кодом ошибки SR:12
        (руководство §8.5.1), в SR:30 таких битов нет.
        """
        error = source.get_error()
        if error is not None and error['code'] in INTERLOCK_ERROR_CODES:
            pytest.skip(
                "Interlock open: SR:12 = {} ({}). "
                "Ensure all doors are closed and emergency stop is released.".format(
                    error['code'], error['message'])
            )

    def test_on_high_voltage(self, source):
        """Включить ВН и проверить что оно включилось."""
        logging.info("Turning on high voltage...")
        source.on_high_voltage()
        hv_on = source.is_on_high_voltage()
        logging.info("HV on after on_high_voltage(): %s", hv_on)
        assert hv_on, "После on_high_voltage() ВН должно быть включено"

        v = source.get_actual_voltage()
        c = source.get_actual_current()
        logging.info("After HV on: voltage=%.3f kV, current=%.3f mA", v, c)

    def test_off_high_voltage(self, source):
        """Выключить ВН (если включено) и проверить что оно выключилось."""
        hv_on = source.is_on_high_voltage()
        if not hv_on:
            logging.info("HV already off, skipping off test")
            return

        logging.info("Turning off high voltage...")
        source.off_high_voltage()
        hv_on = source.is_on_high_voltage()
        logging.info("HV on after off_high_voltage(): %s", hv_on)
        assert not hv_on, "После off_high_voltage() ВН должно быть выключено"

    def test_warmup_sequence_20kv_then_30kv(self, source):
        """
        Сценарий воспроизведения ошибки 109:
        1. Установить 20 кВ / 10 мА (обычно не требует прогрева).
        2. Включить ВН, убедиться что включилось.
        3. Выключить ВН.
        4. Установить 30 кВ / 10 мА (обычно требует прогрева).
        5. Включить ВН — здесь должен автоматически запуститься прогрев.
        6. Убедиться что ВН включилось.
        """
        # Шаг 1-2: 20 кВ
        logging.info("=== Step 1: set 20 kV / 10 mA ===")
        source.set_voltage(20.0)
        source.set_current(10.0)
        source.on_high_voltage()
        assert source.is_on_high_voltage(), "HV should be ON at 20 kV"
        v = source.get_actual_voltage()
        logging.info("HV ON at 20 kV, actual voltage=%.3f kV", v)

        # Шаг 3: выключить
        logging.info("=== Step 2: turn HV OFF ===")
        source.off_high_voltage()
        assert not source.is_on_high_voltage(), "HV should be OFF"

        # Шаг 4-5: 30 кВ — здесь может потребоваться прогрев
        logging.info("=== Step 3: set 30 kV / 10 mA and turn HV ON ===")
        source.set_voltage(30.0)
        source.set_current(10.0)
        source.on_high_voltage()
        assert source.is_on_high_voltage(), "HV should be ON at 30 kV after warmup"
        v = source.get_actual_voltage()
        logging.info("HV ON at 30 kV, actual voltage=%.3f kV", v)
