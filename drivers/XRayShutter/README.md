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
- Таймаут ответа: **5 секунд** (`SERIAL_TIMEOUT`), таймаут записи — **5 секунд** (`SERIAL_WRITE_TIMEOUT`)

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

Порт открывается **один раз** в `__init__` и живёт вместе с объектом: каждое
открытие CDC-ACM дёргает линию DTR модуля, а раньше порт открывался и закрывался
на каждую команду (2-4 раза за одно переключение состояния). Освобождается порт
явным вызовом `release()` (синоним `close_port()`); `HWTomograph._release_devices()`
делает это сам. Доступ к порту сериализован внутренним локом.

При инициализации выполняется проверка связи с модулем (`check_module`). На
первый вызов после подачи питания модуль возвращает `#ERR`, поэтому `$KE`
отправляется дважды — этот приём изолирован в методе `_handshake()` и выполняется
один раз за время жизни объекта. Если модуль не ответил `#OK`, `__init__`
закрывает порт и бросает `RuntimeError`.

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
| `release()` / `close_port()` | — | Освободить serial-порт (положение заслонки не меняется) |
| `is_port_open()` | `bool` | Открыт ли ещё порт модуля |

> `get_firmware_version()` доступен начиная со 2-й аппаратной версии Ke-USB24R. На старых модулях выбрасывает `RuntimeError`.

#### Управление заслонкой

| Метод | Описание |
|---|---|
| `open_shutter()` | Открыть заслонку (включить реле) |
| `close_shutter()` | Закрыть заслонку (выключить реле) |
| `is_open()` | `True` если заслонка открыта |

> **Переименование.** Раньше эти методы назывались `open()` и `close()`, из-за
> чего `close()` у заслонки закрывал заслонку, а у всех остальных драйверов —
> освобождал ресурс, и `HWTomograph._release_devices()` молча обходил заслонку.
> Старые имена оставлены устаревшими синонимами: они работают, но один раз за
> процесс выдают `DeprecationWarning` (и строку `WARNING` в лог, так как
> `DeprecationWarning` по умолчанию скрыт). После их удаления `close()` станет
> освобождать порт, как сейчас `release()`.

#### Интерфейс get_state

```python
shutter.get_state()                         # {'is_open': True}
shutter.get_state('is_closed')              # {'is_closed': False}
shutter.get_state(['is_open', 'is_closed']) # {'is_open': True, 'is_closed': False}
```

Допустимые ключи (`HWShutter.STATE_KEYS`): `is_open`, `is_closed`.
Для неизвестного ключа значение — `{'error': 'Unsupported option'}`.

`set_state()` удалён: в проде он не вызывался (`HWTomograph.set_state` —
заглушка `pass`), использовался только тестом. Заслонкой управляют напрямую
через `open_shutter()` / `close_shutter()`.

### Пример полного цикла

```python
from time import sleep

shutter.close_shutter()
assert not shutter.is_open()

shutter.open_shutter()
assert shutter.is_open()

sleep(0.5)

shutter.close_shutter()
assert not shutter.is_open()

shutter.release()           # порт свободен, заслонка осталась закрытой
```

### Чтение АЦП

```python
adc = shutter.read_adc(channel=1)  # channel: 1–4
# → {'raw': 645, 'voltage_v': 3.1506}
```

Формула перевода: `voltage_v = raw * 5.0 / 1023.0`

## Зависимости

- `pyserial`
