# XRayShutter — драйвер рентгеновской заслонки

Драйвер для управления рентгеновской заслонкой на базе реле-модуля **Ke-USB24R**. Модуль подключается через USB (определяется как виртуальный COM-порт) и управляет одним из четырёх электромагнитных реле.

## Файлы

| Файл | Описание |
|---|---|
| [`XRayShutter.py`](XRayShutter.py) | Класс `HWShutter` — основной драйвер заслонки |

## Аппаратное обеспечение

**Ke-USB24R** — USB-модуль с 4 реле, 24 линиями ввода/вывода и 4-канальным 10-битным АЦП (0–5 В).

Протокол связи:
- Команды в формате `$KE,...\r\n`
- Ответы начинаются с `#`, заканчиваются `\r\n`
- При синтаксической ошибке возвращается `#ERR`
- Таймаут ответа: **5 секунд**

Состояние заслонки:

| Состояние реле | `is_open()` | Описание |
|---|---|---|
| 1 (включено) | `True` | Заслонка **открыта** |
| 0 (выключено) | `False` | Заслонка **закрыта** |

## Конфигурация

Параметры задаются в [`../config/devices.cfg`](../config/devices.cfg):

```ini
[shutter]
port  = /dev/ttyACM2   ; COM-порт модуля
relay = 4              ; номер реле (1–4)
```

Конфиг читается через [`utils.get_shutter_config()`](../utils.py:14).

## Класс `HWShutter`

```python
from drivers.XRayShutter.XRayShutter import HWShutter
from drivers.utils import get_shutter_config

config = get_shutter_config()
shutter = HWShutter(config['port'], config['relay_number'])
```

При инициализации выполняется проверка связи с модулем (`check_module`). На первый вызов после подачи питания модуль всегда возвращает `#ERR`, поэтому команда отправляется дважды.

### Методы

#### Диагностика модуля

| Метод | Возвращает | Описание |
|---|---|---|
| `check_module()` | — | Проверить связь (вызывается в `__init__`) |
| `get_serial_number()` | `str` | Уникальный серийный номер модуля |
| `get_firmware_version()` | `str` | Версия прошивки (только v2+ аппаратная версия) |
| `get_all_relay_states()` | `dict` | Состояния всех 4 реле: `{1: bool, 2: bool, 3: bool, 4: bool}` |
| `read_adc(channel)` | `dict` | АЦП-канал: `{'raw': int, 'voltage_v': float}` |
| `reset()` | — | Сброс модуля в начальное состояние (закрывает заслонку!) |

> `get_firmware_version()` доступен начиная со 2-й аппаратной версии Ke-USB24R. На старых модулях выбрасывает `RuntimeError`.

#### Управление заслонкой

| Метод | Описание |
|---|---|
| `open()` | Открыть заслонку (включить реле) |
| `close()` | Закрыть заслонку (выключить реле) |
| `is_open()` | `True` если заслонка открыта |

#### Интерфейс get_state / set_state

```python
# Чтение состояния
shutter.get_state()                        # {'is_open': True}
shutter.get_state('is_closed')             # {'is_closed': False}
shutter.get_state(['is_open', 'is_closed']) # {'is_open': True, 'is_closed': False}

# Запись состояния
result = shutter.set_state({'is_open': True})
# → {'requested_state': {'is_open': True}, 'result': {'is_open': None}}
```

Допустимые ключи `get_state()`: `is_open`, `is_closed`.  
Допустимые ключи `set_state()`: `is_open` (значение `bool`).

### Пример полного цикла

```python
shutter.close()
assert not shutter.is_open()

shutter.open()
assert shutter.is_open()

from time import sleep
sleep(0.5)

shutter.close()
assert not shutter.is_open()
```

### Чтение АЦП

```python
adc = shutter.read_adc(channel=1)  # channel: 1–4
# → {'raw': 645, 'voltage_v': 3.1506}
```

Формула перевода: `voltage_v = raw * 5.0 / 1023.0`

## Зависимости

- `pyserial`
