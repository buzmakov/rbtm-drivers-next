# XRaySource — драйвер рентгеновского источника

Драйвер для управления рентгеновским генератором **ISOVOLT 3003** (Seifert/GE). Связь через интерфейс RS-232 (9600 8N1).

## Файлы

| Файл | Описание |
|---|---|
| [`XRaySource.py`](XRaySource.py) | Класс `HWSource` — основной драйвер источника |

## Аппаратное обеспечение

**ISOVOLT 3003** (Seifert/GE) — высоковольтный рентгеновский генератор для промышленной и научной дефектоскопии.

Протокол RS-232:
- Скорость: **9600 бод**, 8N1
- Команды: ASCII-строка + `\n`
- Ответы начинаются с `*`, заканчиваются `\r`
- Ошибки читаются командой `SR:12`

## Конфигурация

```ini
[x-ray source]
port = /dev/ttyUSB0   ; путь к RS-232 адаптеру
```

Конфиг читается через [`utils.get_source_config()`](../utils.py:20).

## Класс `HWSource`

```python
from drivers.XRaySource.XRaySource import HWSource
from drivers.utils import get_source_config

config = get_source_config()
source = HWSource(config['port'])

# Режим без реального устройства (для разработки)
source = HWSource(config['port'], mock=True)
```

Параметр `mock=True` позволяет работать без физического подключения — все команды управления игнорируются, методы чтения возвращают фиксированные значения (40 кВ, 20 мА, 800 Вт).

При завершении программы serial-порт закрывается через `atexit`.

### Методы

#### Идентификация

| Метод | Возвращает | Описание |
|---|---|---|
| `get_id()` | `str` | Идентификатор генератора (команда `ID`), результат кэшируется |
| `get_tube_name()` | `str` | Наименование рентгеновской трубки (команда `XT`), кэшируется |

#### Статус устройства

```python
status = source.get_status()
```

Возвращаемая структура:

```python
{
    'power status': {
        'external pc control': bool,  # управление с ПК включено
        'high voltage on':     bool,  # ВН включено
        'cooling system ok':   bool,  # система охлаждения в норме
        'buffer battery ok':   bool,  # аккумулятор в норме
        'current ma norm':     bool,  # ток стабилизирован
        'voltage kv norm':     bool,  # напряжение стабилизировано
    },
    'warming status': {
        'in progress':         bool,  # прогрев выполняется
        'warming interrupted': bool,  # прогрев прерван
        'warming from pc':     bool,  # прогрев инициирован с ПК
        'warming from kb':     bool,  # прогрев инициирован с клавиатуры
    },
    'interlock status': {
        'door 1 ok':           bool,  # дверь 1 закрыта
        'door 2 ok':           bool,  # дверь 2 закрыта
        'extern stop ok':      bool,  # внешний стоп не активен
        'emergency stop ok':   bool,  # аварийный стоп не активен
    }
}
```

#### Управление высоким напряжением

| Метод | Описание |
|---|---|
| `on_high_voltage()` | Включить ВН (при необходимости выполняет прогрев `warmup()`) |
| `off_high_voltage()` | Выключить ВН |
| `is_on_high_voltage()` | `True` если ВН включено |

При включении `on_high_voltage()` автоматически ждёт стабилизации напряжения и тока (до 10 с каждый). Если устройство требует прогрева (код ошибки 106), выполняет `warmup()` и повторяет попытку (не более 3 раз).

#### Прогрев трубки

| Метод | Описание |
|---|---|
| `warmup()` | Запустить программу прогрева (команда `WU:4,NNN`) |

#### Чтение параметров

| Метод | Возвращает | Команда | Описание |
|---|---|---|---|
| `get_nominal_voltage()` | `float` (кВ) | `VN` | Установленное напряжение |
| `get_actual_voltage()` | `float` (кВ) | `VA` | Фактическое напряжение |
| `get_nominal_current()` | `float` (мА) | `CN` | Установленный ток |
| `get_actual_current()` | `float` (мА) | `CA` | Фактический ток |
| `get_nominal_power()` | `float` (Вт) | `PN` | Установленная мощность |
| `get_actual_power()` | `float` (Вт) | `PA` | Фактическая мощность |

Значения кэшируются на **3 секунды** (параметр `CACHE_TTL`) для снижения нагрузки на RS-232.

#### Установка параметров

| Метод | Параметр | Команда | Описание |
|---|---|---|---|
| `set_voltage(voltage)` | кВ | `SV:NNNNNN` | Установить напряжение |
| `set_current(current)` | мА | `SC:NNNNNN` | Установить ток |
| `set_power(power)` | Вт | `SP:NNNNNN` | Установить мощность |

#### Ошибки

| Метод | Возвращает | Описание |
|---|---|---|
| `get_error()` | `dict` или `None` | Текущий код ошибки: `{'code': int, 'message': str}` |
| `reset_error(code)` | — | Сбросить ошибку по коду |

#### Интерфейс get_state / set_state

```python
# Чтение всех параметров
state = source.get_state()

# Чтение выборочно
state = source.get_state(['is_on_high_voltage', 'actual_voltage', 'actual_current'])

# Установка параметров
result = source.set_state({
    'set_voltage': 40.0,
    'set_current': 20.0,
    'high_voltage': True,
})
```

Допустимые ключи `get_state()`:  
`is_on_high_voltage`, `id`, `tube_name`, `actual_voltage`, `nominal_voltage`,  
`actual_current`, `nominal_current`, `actual_power`, `nominal_power`, `status`, `last_error`.

Допустимые ключи `set_state()`:  
`set_voltage` (кВ), `set_current` (мА), `set_power` (Вт), `high_voltage` (bool).

### Пример работы

```python
source = HWSource('/dev/ttyUSB0')

print(source.get_id())          # "ISOVOLT 3003 ..."
print(source.get_tube_name())   # "Mo 40kV 20mA"
print(source.get_status())      # полный статус

# Включение ВН и съёмка
source.on_high_voltage()
source.set_voltage(40.0)
source.set_current(20.0)
# ... съёмка ...
source.off_high_voltage()
```

## Коды ошибок

Коды возвращаются регистром ошибок `SR:12`. Полный список — в словаре `HWSource.STATUS_STRINGS` ([`XRaySource.py`](XRaySource.py)).

Наиболее важные:

| Код | Сообщение | Действие |
|---|---|---|
| 6 | Generator not initialised / not ready | Подождать инициализации генератора |
| 35 | Interlock open | Проверить interlock-цепь |
| 46 | EMERGENCY-STOP | Снять аварийный стоп |
| 63 | Door contact 1 and 2 open | Закрыть защитные двери |
| 64 | Door contact 1 open | Закрыть дверь 1 |
| 65 | Door contact 2 open | Закрыть дверь 2 |
| 76 | Stand-By | Генератор в режиме ожидания — нормально |
| 106 | Warm-up necessary | Требуется прогрев (автоматически выполняется в `on_high_voltage()`) |
| 116 | Warm-up terminated after 3 attempts | Не удалось прогреться — проверить оборудование |

## Запуск тестов

```bash
# Рекомендуемый способ — добавить пользователя в группу dialout:
sudo usermod -a -G dialout $USER
# перелогиниться, затем:

# Все тесты источника
pytest --log-cli-level=INFO -s -v drivers/tests/test_source.py

# Только диагностика (не включает ВН)
pytest --log-cli-level=INFO -s -v drivers/tests/test_source.py::TestSourceDiagnostics

# Mock-тесты (не требуют реального устройства)
pytest --log-cli-level=INFO -s -v drivers/tests/test_source.py::TestSourceMock
```

Альтернатива — запуск внутри Docker-контейнера с доступом к устройству:

```bash
docker exec -it rbtm-tomograph-server \
    python -m pytest /xtomo/drivers/tests/test_source.py -v -s
```

Тесты `TestSourceHighVoltage` автоматически пропускаются если interlock открыт.

## Зависимости

- `pyserial`
