# XRaySource — драйвер рентгеновского источника

Драйвер для управления рентгеновским генератором **ISOVOLT 3003** (Seifert/GE). Связь через интерфейс RS-232 (9600 8N1).

## Файлы

| Файл | Описание |
|---|---|
| [`XRaySource.py`](XRaySource.py) | Класс `HWSource` — основной драйвер источника |

## Аппаратное обеспечение

**ISOVOLT 3003** (Seifert/GE) — высоковольтный рентгеновский генератор для промышленной и научной дефектоскопии.

### Протокол RS-232

- Скорость: **9600 бод**, 8N1
- Команды: ASCII-строка + `\r\n`
- Ответы начинаются с `*`, заканчиваются `\r`
- Ошибки читаются командой `SR:12`
- Протокол XON/XOFF для квитирования

> ⚠️ **Важно:** ISOVOLT 3003 требует `DTR=True` для активации RS-232 интерфейса.  
> В коде это задаётся параметром `dsrdtr=True` в `serial.Serial()`.  
> **Не устанавливайте `rts=False`** — это ломает связь с устройством.

### Команды RS-232

| Команда | Параметр | Описание |
|---|---|---|
| `SV:NNNNNN` | напряжение × 1000 | Установка напряжения (кВ) |
| `VN` | — | Чтение установленного напряжения |
| `VA` | — | Чтение фактического напряжения |
| `SC:NNNNNN` | ток × 1000 | Установка тока (мА) |
| `CN` | — | Чтение установленного тока |
| `CA` | — | Чтение фактического тока |
| `HV:0` / `HV:1` | 0/1 | Выкл/вкл высокого напряжения |
| `WU:x,yyy` | x=режим, yyy=кВ | Запуск прогрева (x=4 — от PC) |
| `CL` | — | **Подтверждение/сброс ошибки** (критично!) |
| `ER` | — | Чтение сообщения об ошибке |
| `SR:nn` | 01/06/12/30 | Чтение статусного слова |
| `ID` | — | Идентификатор устройства |
| `XT` | — | Наименование трубки |

> **Ошибка 119 (`Warm-up program completed. ENTER`):** после прогрева устройство выдаёт эту ошибку. **Команда `CL`** её сбрасывает. Без сброса все последующие команды (`VA`, `CA`, `SV`) возвращают ошибку, и драйвер переходит в режим работы с кэшем.

### Статусные слова

| Слово | Биты | Описание |
|---|---|---|
| `SR:01` | 6 | Высокое напряжение (1=вкл) |
| `SR:01` | 4/8 | Напряжение/ток стабилизированы (0=норм) |
| `SR:06` | 1/2/4/8 | Статус прогрева (вкл с клавиатуры/PC, прерван, в процессе) |
| `SR:12` | — | Код ошибки (0=ошибок нет) |
| `SR:30` | 4 | Аварийный стоп (1=активен) |

### Коды ошибок (выборка)

| Код | Сообщение | Действие |
|---|---|---|
| 6 | Generator not initialised / not ready | Подождать инициализации |
| 35 | Interlock open | Проверить interlock-цепь |
| 46 | EMERGENCY-STOP | Снять аварийный стоп |
| 63-65 | Door contact open | Закрыть защитные двери |
| 76 | Stand-By | Нормальное состояние ожидания |
| 106 | Warm-up necessary | Требуется прогрев |
| 109 | Warm-up! 0=No | Прогрев требуется / не запущен |
| 116 | Warm-up terminated after 3 attempts | Не удалось прогреться — проверить оборудование |
| 119 | Warm-up program completed. ENTER | **Сбросить командой `CL`** |

Полный список кодов — в словаре `HWSource.STATUS_STRINGS` ([`XRaySource.py`](XRaySource.py)).

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

Параметр `mock=True` позволяет работать без физического подключения — все
команды управления игнорируются, методы чтения возвращают фиксированные
значения (40 кВ, 20 мА, 800 Вт). Полностью поддерживаются `get_status()`,
`is_on_high_voltage()`, `get_error()` и `get_state()`.

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
        'emergency stop ok':   bool,  # аварийный стоп (SR:30 bit 2)
    }
```

> **Примечание про `emergency_stop_ok`:**  
> Бит `emergency stop` в слове состояния `SR:30` может быть активен
> (`emergency_stop_ok=False`) даже когда генератор работает нормально
> и включается с физического пульта. Это статус interlock-цепи,
> а не аппаратная ошибка (код `SR:12` при этом равен 0).

#### Управление высоким напряжением

| Метод | Описание |
|---|---|
| `on_high_voltage()` | Включить ВН (при необходимости выполняет прогрев `warmup()`) |
| `off_high_voltage()` | Выключить ВН |
| `is_on_high_voltage()` | `True` если ВН включено |

При включении `on_high_voltage()` автоматически ждёт стабилизации напряжения и тока (до 10 с каждый). Если устройство требует прогрева (код ошибки **106** или **109**), выполняет `warmup()` и повторяет попытку (не более 3 раз).

#### Прогрев трубки

| Метод | Описание |
|---|---|
| `warmup(voltage=None)` | Запустить программу прогрева (команда `WU:4,NNN`) |

**Важные нюансы прогрева из документации:**

- Перед прогревом **высокое напряжение должно быть выключено** (`HV:0`).
- Команда `WU:4,NNN` (режим 4 = от PC, NNN = тестовое напряжение в кВ).
- После `WU` нужно отправить `HV:1` — это аналог нажатия кнопки **START**.
- По окончании прогрева устройство выдаёт ошибку **119**: `"Warm-up program completed. ENTER"`.
- **Ошибку 119 нужно сбросить командой `CL`**, иначе все последующие команды вернут ошибку.
- Если прогрев прерван клавишей STOP, даётся ещё 3 попытки (код **116** после 3 неудач).

#### Чтение параметров

| Метод | Возвращает | Команда | Описание |
|---|---|---|---|
| `get_nominal_voltage()` | `float` (кВ) | `VN` | Установленное напряжение |
| `get_actual_voltage()` | `float` (кВ) | `VA` | Фактическое напряжение |
| `get_nominal_current()` | `float` (мА) | `CN` | Установленный ток |
| `get_actual_current()` | `float` (мА) | `CA` | Фактический ток |
| `get_nominal_power()` | `float` (Вт) | `PN`¹ | Установленная мощность |
| `get_actual_power()` | `float` (Вт) | `PA` | Фактическая мощность |

¹ **ISOVOLT 3003 не поддерживает команду `PN`.** В этом случае мощность
рассчитывается как `nominal_voltage × nominal_current` (В × А = Вт).

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

**Сброс ошибки:** команда `CL` отправляется автоматически в `set_voltage()`, `warmup()` и `on_high_voltage()` при необходимости. Явного метода `reset_error()` нет — вместо него используется `get_error()` для чтения и внутренняя логика для сброса.

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

**Команда сброса ошибки:** **`CL`** (Clear) — единственный способ очистить состояние ошибки 119 ("Warm-up program completed. ENTER"). Не путать с несуществующей командой `RE:19` — она игнорируется устройством!

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

Тесты `TestSourceHighVoltage` автоматически пропускаются если открыты
двери или активен внешний стоп. Проверка `emergency_stop_ok` отключена
— генератор может работать с активным сигналом E-STOP (см. раздел
«Статус устройства» выше).

## Зависимости

- `pyserial`
