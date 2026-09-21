# rbtm-drivers-next

Flask-сервис управления рентгеновским томографом. Принимает команды от `rbtm-web`, управляет оборудованием (двигатели, детектор, рентгеновская трубка, затвор) и отправляет кадры в `rbtm-storage`.

## Структура проекта

```
rbtm-drivers-next/
├── drivers/                     # Низкоуровневые драйверы оборудования
│   ├── Detector/                # Детектор XIMEA xiRAY
│   ├── Motors/                  # Шаговые моторы XIMC (Standa)
│   ├── XRayShutter/             # Заслонка Ke-USB24R
│   ├── XRaySource/              # Рентгеновский источник ISOVOLT 3003
│   ├── Tomograph/               # Агрегирующий класс HWTomograph
│   ├── config/devices.cfg       # Конфигурация портов и параметров
│   └── tests/                   # Тесты оборудования
├── experiment/                  # Flask API и логика эксперимента
├── tomograph_server.py          # Отдельный процесс работы с железом
└── redis_proxy.py               # Redis-прокси для межпроцессного взаимодействия
```

## Запуск

```bash
# Разработка
FLASK_DEBUG=1 FLASK_APP=experiment flask run --port=5001 --host=0.0.0.0 --no-reload

# Production (Docker)
docker compose up -d
```

## Архитектура

```
rbtm-web (Django) ──HTTP──► rbtm-drivers-next (Flask :5001)
                                      │
                          ┌───────────┴───────────┐
                          │                       │
                    Tomograph (Flask)   tomograph_server.py
                          │                       │
                    RedisProxy ◄──Redis──► HWTomograph (реальное железо)
```

- **`experiment/routes.py`** — Flask Blueprint, HTTP API
- **`experiment/tomograph.py`** — `Tomograph` класс, проксирует команды через Redis
- **`experiment/experiment.py`** — логика проведения эксперимента (`Experiment`, `AdvancedExperiment`)
- **`tomograph_server.py`** — отдельный процесс, работает напрямую с `HWTomograph` через `RedisProxyServer`

---

## Драйверы оборудования

Низкоуровневые драйверы находятся в пакете [`drivers/`](drivers/). Каждый драйвер реализует интерфейс `get_state()` / `set_state()` для унифицированного доступа к устройству.

| Устройство | Класс | Документация |
|---|---|---|
| Детектор XIMEA xiRAY | [`HWDetector`](drivers/Detector/Detector.py) | [drivers/Detector/README.md](drivers/Detector/README.md) |
| Шаговые моторы XIMC | [`HWRotaryMotor`, `HWLinearMotor`](drivers/Motors/Motor.py) | [drivers/Motors/README.md](drivers/Motors/README.md) |
| Заслонка Ke-USB24R | [`HWShutter`](drivers/XRayShutter/XRayShutter.py) | [drivers/XRayShutter/README.md](drivers/XRayShutter/README.md) |
| Источник ISOVOLT 3003 | [`HWSource`](drivers/XRaySource/XRaySource.py) | [drivers/XRaySource/README.md](drivers/XRaySource/README.md) |
| Томограф (агрегатор) | [`HWTomograph`](drivers/Tomograph/Tomograph.py) | — |

### Конфигурация оборудования

Параметры всех устройств (COM-порты, скорости, идентификаторы) задаются в [`drivers/config/devices.cfg`](drivers/config/devices.cfg):

```ini
[angle motor]
port         = xi-com:///dev/ximc/0000037A
step_in_360  = 32400
speed        = 500
acceleration = 500

[horizontal motor]
port                   = xi-com:///dev/ximc/00000271
speed                  = 200
acceleration           = 200
steps_per_mm           = 199.46
move_object_outside_mm = -21.06

[shutter]
port  = /dev/ttyACM2
relay = 4

[x-ray source]
port = /dev/ttyUSB0
mock = false
```

### Тесты оборудования

Интеграционные тесты для быстрой диагностики работоспособности устройств:

```bash
# Все тесты оборудования
pytest --log-cli-level=INFO -s -v drivers/tests/

# Отдельные устройства
pytest --log-cli-level=INFO -s -v drivers/tests/test_detector.py
pytest --log-cli-level=INFO -s -v drivers/tests/test_motors.py
pytest --log-cli-level=INFO -s -v drivers/tests/test_shutter.py
pytest --log-cli-level=INFO -s -v drivers/tests/test_source.py
```

Подробнее: [drivers/tests/README.md](drivers/tests/README.md)

---

## Форматы эксперимента

### Простой режим (`advanced: false`)

Классическая схема: заданное количество dark и empty кадров, затем все data кадры подряд.

**JSON параметры:**
```json
{
  "exp_id": "uuid-string",
  "advanced": false,
  "DARK":  { "count": 10,  "exposure": 3000.0 },
  "EMPTY": { "count": 10,  "exposure": 3000.0 },
  "DATA":  {
    "step count":    500,
    "exposure":      3000.0,
    "angle step":    0.36,
    "count per step": 1
  }
}
```

**Последовательность съёмки:**
```
[dark × N] → [empty × N] → [data × step_count × count_per_step]
```

**Диаграмма:**
```
┌──────────┬──────────┬────────────────────────────────────────────┐
│ dark × N │ empty × N│           data × (step_count × cps)        │
└──────────┴──────────┴────────────────────────────────────────────┘
```

---

### Продвинутый режим (`advanced: true`)

Периодическая вставка серий empty-кадров во время съёмки data. После каждой вставки снимается один контрольный кадр (`data_check`) при том же угле, что и последний data-кадр — для проверки дрейфа образца.

**JSON параметры:**
```json
{
  "exp_id":            "uuid-string",
  "advanced":          true,
  "exposure":          3000.0,
  "series_length":     10,
  "data_total":        500,
  "data_angle_step":   0.36,
  "data_count_per_step": 1,
  "empty_period":      50
}
```

| Параметр | Описание | По умолчанию |
|---|---|---|
| `exposure` | Единая экспозиция для всех типов кадров (мс) | — |
| `series_length` | Количество dark и empty кадров в серии | 10 |
| `data_total` | Общее число угловых позиций DATA | — |
| `data_angle_step` | Угловой шаг между позициями (°) | — |
| `data_count_per_step` | Кадров на одну угловую позицию | 1 |
| `empty_period` | Вставлять empty-серию каждые N угловых **позиций** | 50 |

**Последовательность съёмки:**

```
1. dark × series_length          (затвор закрыт)
2. empty × series_length         (образец убран, затвор открыт)
3. Основной цикл (pos = 0 .. data_total-1):
   a. set_angle(pos × angle_step)
   b. data × data_count_per_step
   c. Если (pos+1) % empty_period == 0 И pos < data_total-1:
      - empty × series_length    (образец убран)
      - data_check × data_count_per_step  (тот же угол, образец возвращён)
4. close_shutter, source_power_off
```

**Диаграмма (пример: data_total=150, empty_period=50, series_length=5):**

```
┌─────────┬─────────┬─────────────────────┬───────┬───┬─────────────────────┬───────┬───┬──────────────────────┐
│dark × 5 │empty × 5│    data × 50 pos    │empty×5│chk│    data × 50 pos    │empty×5│chk│    data × 50 pos     │
└─────────┴─────────┴─────────────────────┴───────┴───┴─────────────────────┴───────┴───┴──────────────────────┘
                                           ↑ угол не меняется                ↑ угол не меняется
```

**Подсчёт кадров:**
```python
num_empty_inserts = (data_total - 1) // empty_period

total_frames = (
    series_length                               # dark
    + series_length                             # начальная empty
    + data_total * data_count_per_step          # data
    + num_empty_inserts * series_length         # периодические empty
    + num_empty_inserts * data_count_per_step   # data_check
)
```

---

## Типы кадров

| mode | Описание | Затвор | Образец |
|---|---|---|---|
| `dark` | Тёмный кадр (фон детектора) | Закрыт | В пучке |
| `empty` | Пустой кадр (без образца) | Открыт | Убран |
| `data` | Проекция образца | Открыт | В пучке |
| `data_check` | Контрольный кадр (тот же угол что предыдущий data) | Открыт | В пучке |

---

## HTTP API

### Состояние томографа
| Метод | URL | Описание |
|---|---|---|
| GET | `/tomograph/<n>/state` | Состояние: `ready` / `experiment` / `unavailable` |

### Эксперимент
| Метод | URL | Описание |
|---|---|---|
| POST | `/tomograph/<n>/experiment/start` | Запуск эксперимента |
| GET | `/tomograph/<n>/experiment/stop` | Остановка эксперимента |
| GET | `/tomograph/<n>/experiment/status` | Статус выполнения (progress, timeline, exp_id) |
| GET | `/tomograph/<n>/experiment/last-frame` | Последний снятый кадр (npz) |

### Детектор
| Метод | URL | Описание |
|---|---|---|
| POST | `/tomograph/<n>/detector/get-frame-preview` | Превью кадра (npz, downsampled) |
| GET | `/tomograph/<n>/detector/model` | Модель детектора |
| POST | `/tomograph/<n>/detector/get-frame` | Кадр с открытым затвором (png) |
| POST | `/tomograph/<n>/detector/get-frame-with-closed-shutter` | Кадр с закрытым затвором (png) |
| GET | `/tomograph/<n>/detector/chip_temp` | Температура сенсора |
| GET | `/tomograph/<n>/detector/hous_temp` | Температура корпуса |

### Двигатели, затвор, источник
| Метод | URL | Описание |
|---|---|---|
| POST | `/tomograph/<n>/motor/set-angle-position` | Установить угол |
| GET | `/tomograph/<n>/motor/get-angle-position` | Текущий угол |
| POST | `/tomograph/<n>/motor/set-horizontal-position` | Горизонтальная позиция (шаги) |
| GET | `/tomograph/<n>/motor/get-horizontal-position` | Текущая горизонтальная позиция |
| POST | `/tomograph/<n>/motor/set-vertical-position` | Вертикальная позиция (заглушка, мотора нет) |
| GET | `/tomograph/<n>/motor/get-vertical-position` | Вертикальная позиция (заглушка) |
| GET | `/tomograph/<n>/motor/reset-angle-position` | Сбросить угол в 0 |
| GET | `/tomograph/<n>/motor/move-away` | Убрать образец из пучка |
| GET | `/tomograph/<n>/motor/move-back` | Вернуть образец в пучок |
| GET | `/tomograph/<n>/shutter/open/0` | Открыть затвор |
| GET | `/tomograph/<n>/shutter/close/0` | Закрыть затвор |
| GET | `/tomograph/<n>/shutter/state` | Состояние затвора |
| GET | `/tomograph/<n>/source/power-on` | Включить рентген (async, запускает прогрев при необходимости) |
| GET | `/tomograph/<n>/source/power-off` | Выключить рентген |
| GET | `/tomograph/<n>/source/state` | Состояние источника: `on`, `busy`, `mocked`, `warming_status` |
| POST | `/tomograph/<n>/source/set-voltage` | Установить напряжение (кВ) |
| POST | `/tomograph/<n>/source/set-current` | Установить ток (мА) |
| GET | `/tomograph/<n>/source/get-voltage` | Текущее напряжение (кВ) |
| GET | `/tomograph/<n>/source/get-current` | Текущий ток (мА) |

### Ответ `/experiment/status`
```json
{
  "success": true,
  "result": {
    "running":       true,
    "exp_id":        "uuid-string",
    "frame_num":     145,
    "total_frames":  620,
    "progress_pct":  23.4,
    "current_mode":  "data",
    "current_angle": 51.84,
    "elapsed_sec":   320.5,
    "timeline": [
      {"mode": "dark",       "count": 10},
      {"mode": "empty",      "count": 10},
      {"mode": "data",       "count": 125}
    ]
  }
}
```
