# Motors — драйвер шаговых двигателей

Драйвер для управления шаговыми двигателями на базе контроллеров **XIMC** (Standa). Использует библиотеку `libximc` через биндинг [`pyximc.py`](pyximc.py).

## Файлы

| Файл | Описание |
|---|---|
| [`Motor.py`](Motor.py) | Класс `HWMotor` — основной драйвер мотора |
| [`pyximc.py`](pyximc.py) | Python-биндинги библиотеки libximc (Standa XIMC) |

## Типы моторов

В томографе используются два мотора одного класса `HWMotor`:

| Мотор | Тип | `steps_on_deg` | Назначение |
|---|---|---|---|
| **Угловой** | Вращательный | `float` (шагов/°) | Поворот образца при съёмке |
| **Горизонтальный** | Линейный | `None` | Вынос образца из пучка |

> **TODO:** Архитектурная проблема — оба мотора используют один класс `HWMotor`. Планируется рефакторинг на отдельные классы `HWRotaryMotor` / `HWLinearMotor`.

## Конфигурация

Параметры задаются в [`../config/devices.cfg`](../config/devices.cfg):

```ini
[angle motor]
port         = xi-com:///dev/ximc/0000037A
step_in_360  = 32400        ; полных шагов на 360°
speed        = 500           ; шагов/с
acceleration = 500           ; шагов/с²

[horizontal motor]
port               = xi-com:///dev/ximc/00000271
speed              = 200
acceleration       = 200
move_object_outside = -4200  ; шагов от нуля до позиции парковки
```

Конфиг читается через [`utils.get_angle_motor_config()`](../utils.py:25) и [`utils.get_horizontal_motor_config()`](../utils.py:34).

## Класс `HWMotor`

```python
from drivers.Motors.Motor import HWMotor

# Вращательный мотор (угловой)
motor = HWMotor(port='xi-com:///dev/ximc/0000037A',
                speed=500,
                acceleration=500,
                steps_on_deg=90.0)  # 32400 шагов / 360° = 90 шагов/°

# Линейный мотор (горизонтальный)
motor = HWMotor(port='xi-com:///dev/ximc/00000271',
                speed=200,
                acceleration=200,
                steps_on_deg=None)  # None → линейный, deg-методы недоступны
```

При открытии устройства автоматически применяются настройки контроллера:
- граничные флаги отключены (`BorderFlags = 0`);
- удерживающий ток после остановки = 0 (мотор не греется в покое);
- скорость и ускорение из конфигурации;
- режим микрошага **1/256**.

При завершении программы соединение закрывается через `atexit`.

### Методы

#### Информация и статус

| Метод | Возвращает | Описание |
|---|---|---|
| `get_info()` | `dict` | Производитель, описание продукта, версия прошивки |
| `get_status()` | `dict` | Ток двигателя (мА), напряжение питания (мВ), флаги состояния |
| `get_power_info()` | `dict` | Настройки питания: HoldCurrent, задержки, флаги |

#### Позиция

| Метод | Применим | Возвращает | Описание |
|---|---|---|---|
| `get_position()` | Оба типа | `float` | Абсолютная позиция в шагах (с учётом микрошага) |
| `get_position_deg()` | Только вращательный | `float` | Абсолютная позиция в градусах |

#### Движение

| Метод | Применим | Описание |
|---|---|---|
| `move_to_position(position, uposition, blocking)` | Оба | Абсолютное перемещение в шагах |
| `move_to_position_deg(position, blocking)` | Только вращательный | Абсолютное перемещение в градусах |
| `move_by_delta(step, ustep, blocking)` | Оба | Относительное смещение в шагах |
| `move_by_delta_deg(position, blocking)` | Только вращательный | Относительное смещение в градусах |

Параметр `blocking=True` (по умолчанию) блокирует поток до завершения движения. При `blocking=False` команда отправляется без ожидания — используется в режиме ручной юстировки для сохранения отзывчивости сервера.

#### Калибровка

| Метод | Описание |
|---|---|
| `set_zero(blocking)` | Объявить текущую позицию нулём (home position) |
| `set_microstep_mode_256()` | Установить режим 1/256 микрошага (вызывается автоматически) |

#### Состояние

```python
state = motor.get_state()
# → {'device_name': 'xi-com:///dev/ximc/0000037A', 'steps_on_deg': 90.0,
#    'speed': 500, 'acceleration': 500, 'position': 45.0}

state = motor.get_state(['speed', 'position'])
```

Допустимые ключи: `device_name`, `steps_on_deg`, `speed`, `acceleration`, `position`.  
Для вращательного мотора `position` возвращается в градусах, для линейного — в шагах.

### Пример: угловой мотор

```python
from drivers.Motors.Motor import HWMotor, print_test_info
from drivers.utils import get_angle_motor_config

config = get_angle_motor_config()
motor = HWMotor(config['port'], config['speed'], config['acceleration'], config['step_360'])

pos = motor.get_position_deg()       # текущий угол
motor.move_to_position_deg(90.0)     # повернуть на 90°
motor.set_zero()                     # объявить текущую позицию нулём
```

### Пример: горизонтальный мотор

```python
from drivers.Motors.Motor import HWMotor
from drivers.utils import get_horizontal_motor_config

config = get_horizontal_motor_config()
motor = HWMotor(config['port'], config['speed'], config['acceleration'], steps_on_deg=None)

pos = motor.get_position()           # текущая позиция в шагах
motor.move_by_delta(-4200)           # вынести образец из пучка
motor.move_to_position(0)            # вернуть образец в пучок
```

## Утилита `print_test_info()`

Выводит версию библиотеки libximc и список обнаруженных XIMC-устройств:

```python
from drivers.Motors.Motor import print_test_info
print_test_info()
```

## Зависимости

- **libximc** — библиотека Standa для XIMC-контроллеров (устанавливается отдельно).  
  Биндинг [`pyximc.py`](pyximc.py) должен находиться рядом с разделяемыми библиотеками (`.so` / `.dll`).
- `numpy`
