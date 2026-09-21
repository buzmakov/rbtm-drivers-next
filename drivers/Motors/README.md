# Motors — драйвер шаговых двигателей

Драйвер для управления шаговыми двигателями на базе контроллеров **XIMC** (Standa). Использует библиотеку `libximc` через биндинг [`pyximc.py`](pyximc.py).

## Файлы

| Файл | Описание |
|---|---|
| [`Motor.py`](Motor.py) | Классы `BaseMotor`, `HWRotaryMotor`, `HWLinearMotor`, исключение `MotorTimeoutError` |
| [`motor_math.py`](motor_math.py) | Чистая арифметика: шаги ↔ микрошаги, нормализация угла, таймаут движения (без libximc) |
| [`pyximc.py`](pyximc.py) | Python-биндинги библиотеки libximc (Standa XIMC) |

## Типы моторов

В томографе используются два мотора разных типов:

| Мотор | Класс | Параметры | Назначение |
|---|---|---|---|
| **Угловой** | `HWRotaryMotor` | `steps_on_deg: float` | Поворот образца при съёмке |
| **Горизонтальный** | `HWLinearMotor` | `steps_per_mm: float`, `move_outside_mm: float` | Вынос образца из пучка |

## Иерархия классов

```
BaseMotor
├── HWRotaryMotor   — вращательный (угловой) мотор
└── HWLinearMotor   — линейный (горизонтальный) мотор
```

## Конфигурация

Параметры задаются в [`../config/devices.cfg`](../config/devices.cfg):

```ini
[angle motor]
port         = xi-com:///dev/ximc/0000037A
step_in_360  = 32400        ; полных шагов на 360°
speed        = 500           ; шагов/с
acceleration = 500           ; шагов/с²

[horizontal motor]
port                   = xi-com:///dev/ximc/00000271
speed                  = 200
acceleration           = 200
steps_per_mm           = 199.46      ; 1 шаг = 5.0136 мкм
move_object_outside_mm = -21.06      ; позиция парковки в мм (≈ -4200 шагов)
```

Конфиг читается через [`utils.get_angle_motor_config()`](../utils.py) и [`utils.get_horizontal_motor_config()`](../utils.py).

| Ключ в `devices.cfg` | Ключ словаря конфига | Параметр конструктора |
|---|---|---|
| `step_in_360` | `steps_per_deg` (= `step_in_360 / 360`) | `steps_on_deg` |
| `steps_per_mm` | `steps_per_mm` | `steps_per_mm` |
| `move_object_outside_mm` | `move_outside_mm` | `move_outside_mm` |

---

## Класс `BaseMotor`

Базовый класс — не создаётся напрямую. Инкапсулирует открытие/закрытие устройства, применение начальных настроек контроллера и низкоуровневые команды позиционирования (в шагах).

При открытии устройства автоматически применяются настройки контроллера:
- граничные флаги отключены (`BorderFlags = 0`);
- удерживающий ток после остановки = 0 (мотор не греется в покое);
- скорость и ускорение из конфигурации;
- режим микрошага **1/256**.

Устройство освобождается методом `close()`. Он же зарегистрирован в `atexit`
как страховка: незакрытый контроллер libximc остаётся занятым, и следующее
открытие падает с `open failed`. Явный `close()` снимает свою регистрацию
в `atexit`, так что интерпретатор не держит ссылку на объект мотора.

Перевод дробных шагов в пару `(Position, uPosition)` выполняет единственный
helper `motor_math.to_steps()`; знаки обеих частей совпадают, как того требует
libximc (`uPosition` в диапазоне -255..255).

---

## Класс `HWRotaryMotor`

Вращательный (угловой) мотор.

```python
from drivers.Motors.Motor import HWRotaryMotor
from drivers.utils import get_angle_motor_config

config = get_angle_motor_config()
motor = HWRotaryMotor(config['port'],
                      config['speed'],
                      config['acceleration'],
                      steps_on_deg=config['steps_per_deg'])  # 32400 / 360 = 90 шагов/°
```

### Методы `HWRotaryMotor`

#### Информация и статус (наследуются от `BaseMotor`)

| Метод | Возвращает | Описание |
|---|---|---|
| `get_info()` | `dict` | Производитель, описание продукта, версия прошивки |
| `get_status()` | `dict` | Ток двигателя (мА), напряжение питания (мВ), флаги состояния, `MoveSts`/`MvCmdSts` |
| `get_power_info()` | `dict` | Настройки питания: HoldCurrent, задержки, флаги |

Все три возвращают нативные значения (`int` / `str`), а при ошибке бросают
`RuntimeError`; ключа `'error'` в ответе нет.

#### Позиция

| Метод | Возвращает | Описание |
|---|---|---|
| `get_position()` | `float` | Абсолютная позиция в шагах (с учётом микрошага), без нормализации |
| `get_position_deg()` | `float` | Текущий угол, нормализованный к **[0, 360)** |

#### Движение

| Метод | Описание |
|---|---|
| `move_to_position(position, uposition, blocking)` | Абсолютное перемещение в шагах |
| `move_to_position_deg(position, blocking)` | Поворот к углу **по кратчайшему пути** |
| `move_by_delta(step, ustep, blocking)` | Относительное смещение в шагах |
| `move_by_delta_deg(position, blocking)` | Относительное смещение в градусах |

`move_to_position_deg()` трактует цель как положение на окружности: смещение
считается в `(-180, 180]` от текущего угла, поэтому `359.5° -> 0°` — это движение
на `+0.5°`, а не полный оборот назад (~65 с при `speed=500`). Ровно `180°` —
поворот вперёд. Счётчик шагов контроллера при этом не сбрасывается.

#### Калибровка

| Метод | Описание |
|---|---|
| `set_zero(blocking)` | Обнулить счётчик шагов контроллера: мотор не двигается, текущая физическая позиция становится нулевой |
| `set_microstep_mode_256()` | Установить режим 1/256 микрошага (вызывается автоматически) |

#### Состояние

```python
state = motor.get_state()
# → {'device_name': 'xi-com:///dev/ximc/0000037A', 'steps_on_deg': 90.0,
#    'speed': 500, 'acceleration': 500, 'position': 45.0}

state = motor.get_state(['speed', 'position'])
```

Допустимые ключи (`HWRotaryMotor.STATE_KEYS`): `device_name`, `steps_on_deg`,
`speed`, `acceleration`, `position`. `position` возвращается в градусах `[0, 360)`.

### Пример: угловой мотор

```python
from drivers.Motors.Motor import HWRotaryMotor
from drivers.utils import get_angle_motor_config

config = get_angle_motor_config()
motor = HWRotaryMotor(config['port'], config['speed'], config['acceleration'],
                      steps_on_deg=config['steps_per_deg'])

pos = motor.get_position_deg()       # текущий угол
motor.move_to_position_deg(90.0)     # повернуть на 90°
motor.move_by_delta_deg(2.0)         # повернуть ещё на 2°
motor.set_zero()                     # объявить текущую позицию нулём
```

---

## Класс `HWLinearMotor`

Линейный (горизонтальный) мотор.

```python
from drivers.Motors.Motor import HWLinearMotor
from drivers.utils import get_horizontal_motor_config

config = get_horizontal_motor_config()
motor = HWLinearMotor(config['port'],
                      config['speed'],
                      config['acceleration'],
                      steps_per_mm=config['steps_per_mm'],      # 199.46 шагов/мм
                      move_outside_mm=config['move_outside_mm']) # -21.06 мм
```

### Методы `HWLinearMotor`

#### Позиция

| Метод | Возвращает | Описание |
|---|---|---|
| `get_position()` | `float` | Абсолютная позиция в шагах — **основная единица API** |
| `get_position_mm()` | `float` | Та же позиция в миллиметрах (обёртка) |

#### Движение

| Метод | Описание |
|---|---|
| `move_to_position(position, uposition, blocking)` | Абсолютное перемещение в шагах |
| `move_to_position_mm(mm, blocking)` | Абсолютное перемещение в мм (обёртка над `_mm_to_steps`) |
| `move_by_delta(step, ustep, blocking)` | Относительное смещение в шагах |
| `move_by_delta_mm(mm, blocking)` | Относительное смещение в мм (обёртка) |
| `move_outside(blocking)` | Переместить в позицию парковки (`move_outside_mm` из конфига, в мм) |

Flask-слой работает с горизонтальным мотором **в шагах** (`get_position()`,
`move_to_position()`); миллиметры нужны только позиции парковки из конфига.
Перевод мм в шаги выполняет единственный метод `_mm_to_steps()`.

#### Состояние

```python
state = motor.get_state()
# → {'device_name': 'xi-com:///dev/ximc/00000271', 'steps_per_mm': 199.46,
#    'move_outside_mm': -21.06, 'speed': 200, 'acceleration': 200,
#    'position': 0.0, 'position_mm': 0.0}

state = motor.get_state(['speed', 'position'])
```

Допустимые ключи (`HWLinearMotor.STATE_KEYS`): `device_name`, `steps_per_mm`,
`move_outside_mm`, `speed`, `acceleration`, `position`, `position_mm`.
`position` возвращается **в шагах**, `position_mm` — в миллиметрах.

### Пример: горизонтальный мотор

```python
from drivers.Motors.Motor import HWLinearMotor
from drivers.utils import get_horizontal_motor_config

config = get_horizontal_motor_config()
motor = HWLinearMotor(config['port'], config['speed'], config['acceleration'],
                      steps_per_mm=config['steps_per_mm'],
                      move_outside_mm=config['move_outside_mm'])

pos_mm = motor.get_position_mm()    # текущая позиция в мм
motor.move_outside()                # вынести образец из пучка (→ move_outside_mm)
motor.move_to_position(0)           # вернуть образец в пучок (позиция 0)
motor.move_by_delta_mm(-5.0)        # сдвинуть на 5 мм назад
```

---

## Ожидание остановки и таймаут

При `blocking=True` (по умолчанию) драйвер ждёт остановки сам: опрашивает
`get_status()` каждые `WAIT_FOR_STOP_POLL_INTERVAL_S` (50 мс) и считает движение
законченным, когда сброшены оба признака — `MoveSts & MOVE_STATE_MOVING` и
`MvCmdSts & MVCMD_RUNNING`.

Таймаут считается по расстоянию и скорости:

```
motor_math.move_timeout_s(distance, speed) = distance / speed * 1.5 + 5 с
```

Полный оборот углового мотора (32400 шагов при 500 шагах/с, ~64.8 с) даёт
таймаут ~102 с. При его превышении бросается `MotorTimeoutError` — подкласс
`RuntimeError`, так что существующие обработчики продолжают работать.

Раньше тут вызывался `lib.command_wait_for_stop(id, 10)`, у которого второй
аргумент — интервал опроса, а не таймаут: ожидание было бесконечным.

При `blocking=False` команда только отправляется контроллеру, а вызывающий сам
решает, когда и как дождаться остановки (`get_position()` / `get_status()`).
Сервер железа однопоточный, поэтому неблокирующие движения нужны для юстировки.

---

## Тесты

| Файл | Нужно железо |
|---|---|
| [`../tests/test_motor_math.py`](../tests/test_motor_math.py) | нет — чистая арифметика |
| [`../tests/test_motors.py`](../tests/test_motors.py) | да — реальные моторы |

## Зависимости

- **libximc** — библиотека Standa для XIMC-контроллеров (устанавливается отдельно).
  Биндинг [`pyximc.py`](pyximc.py) должен находиться рядом с разделяемыми библиотеками (`.so` / `.dll`).
