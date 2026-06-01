# Motors — драйвер шаговых двигателей

Драйвер для управления шаговыми двигателями на базе контроллеров **XIMC** (Standa). Использует библиотеку `libximc` через биндинг [`pyximc.py`](pyximc.py).

## Файлы

| Файл | Описание |
|---|---|
| [`Motor.py`](Motor.py) | Классы `BaseMotor`, `HWRotaryMotor`, `HWLinearMotor` |
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

HWMotor = HWRotaryMotor   # alias для обратной совместимости
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

---

## Класс `BaseMotor`

Базовый класс — не создаётся напрямую. Инкапсулирует открытие/закрытие устройства, применение начальных настроек контроллера и низкоуровневые команды позиционирования (в шагах).

При открытии устройства автоматически применяются настройки контроллера:
- граничные флаги отключены (`BorderFlags = 0`);
- удерживающий ток после остановки = 0 (мотор не греется в покое);
- скорость и ускорение из конфигурации;
- режим микрошага **1/256**.

При завершении программы соединение закрывается через `atexit`.

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
                      steps_on_deg=config['step_360'])  # 32400 / 360 = 90 шагов/°
```

### Методы `HWRotaryMotor`

#### Информация и статус (наследуются от `BaseMotor`)

| Метод | Возвращает | Описание |
|---|---|---|
| `get_info()` | `dict` | Производитель, описание продукта, версия прошивки |
| `get_status()` | `dict` | Ток двигателя (мА), напряжение питания (мВ), флаги состояния |
| `get_power_info()` | `dict` | Настройки питания: HoldCurrent, задержки, флаги |

#### Позиция

| Метод | Возвращает | Описание |
|---|---|---|
| `get_position()` | `float` | Абсолютная позиция в шагах (с учётом микрошага) |
| `get_position_deg()` | `float` | Абсолютная позиция в градусах |

#### Движение

| Метод | Описание |
|---|---|
| `move_to_position(position, uposition, blocking)` | Абсолютное перемещение в шагах |
| `move_to_position_deg(position, blocking)` | Абсолютное перемещение в градусах |
| `move_by_delta(step, ustep, blocking)` | Относительное смещение в шагах |
| `move_by_delta_deg(position, blocking)` | Относительное смещение в градусах |

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
`position` возвращается в градусах.

### Пример: угловой мотор

```python
from drivers.Motors.Motor import HWRotaryMotor
from drivers.utils import get_angle_motor_config

config = get_angle_motor_config()
motor = HWRotaryMotor(config['port'], config['speed'], config['acceleration'],
                      steps_on_deg=config['step_360'])

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
| `get_position()` | `float` | Абсолютная позиция в шагах (с учётом микрошага) |
| `get_position_mm()` | `float` | Абсолютная позиция в миллиметрах |

#### Движение

| Метод | Описание |
|---|---|
| `move_to_position(position, uposition, blocking)` | Абсолютное перемещение в шагах |
| `move_to_position_mm(mm, blocking)` | Абсолютное перемещение в мм |
| `move_by_delta(step, ustep, blocking)` | Относительное смещение в шагах |
| `move_by_delta_mm(mm, blocking)` | Относительное смещение в мм |
| `move_outside(blocking)` | Переместить в позицию парковки (`move_outside_mm`) |

#### Состояние

```python
state = motor.get_state()
# → {'device_name': 'xi-com:///dev/ximc/00000271', 'steps_per_mm': 199.46,
#    'move_outside_mm': -21.06, 'speed': 200, 'acceleration': 200, 'position': 0.0}

state = motor.get_state(['speed', 'position'])
```

Допустимые ключи: `device_name`, `steps_per_mm`, `move_outside_mm`, `speed`, `acceleration`, `position`.
`position` возвращается в миллиметрах.

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

## Обратная совместимость

Для кода, использующего старый `HWMotor`, доступен alias:

```python
from drivers.Motors.Motor import HWMotor  # = HWRotaryMotor
```

Новый код должен явно использовать `HWRotaryMotor` или `HWLinearMotor`.

---

## Параметр `blocking`

Параметр `blocking=True` (по умолчанию) блокирует поток до завершения движения. При `blocking=False` команда отправляется без ожидания — используется в режиме ручной юстировки для сохранения отзывчивости сервера.

---

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
