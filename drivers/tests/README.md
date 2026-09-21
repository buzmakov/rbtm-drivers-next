# drivers/tests — тесты оборудования томографа

Быстрые интеграционные тесты для проверки реального оборудования. Тесты не покрывают все граничные случаи — они предназначены для быстрой диагностики работоспособности каждого устройства при подключении или обслуживании.

## Файлы тестов

| Файл | Устройство | Что проверяет |
|---|---|---|
| [`test_detector_offline.py`](test_detector_offline.py) | — (заглушка камеры) | Логика драйвера детектора **без железа**: ленивый старт захвата, триггер на кадр, сброс состояния при ошибке, зависание, close() |
| [`test_detector.py`](test_detector.py) | Детектор XIMEA | Подключение, метаданные, температуры, захват кадров, цикл start/stop acquisition |
| [`test_detector_perf.py`](test_detector_perf.py) | Детектор XIMEA | Бенчмарк: накладные расходы на кадр (время кадра − экспозиция) при 0.1 / 1 / 10 с |
| [`test_motor_math.py`](test_motor_math.py) | — (чистая математика) | Перевод шагов/микрошагов, мм, кратчайший путь по углу, расчёт таймаута движения **без железа** |
| [`test_motors.py`](test_motors.py) | Угловой и горизонтальный моторы | Подключение, движение туда-обратно с assert точности |
| [`test_shutter.py`](test_shutter.py) | Заслонка Ke-USB24R | Серийный номер, реле, АЦП, цикл открытия/закрытия |
| [`test_source.py`](test_source.py) | Рентгеновский источник ISOVOLT | Идентификация, статус, блокировки — **без включения ВН** |
| [`test_tomograh.py`](test_tomograh.py) | Томограф целиком | Структура ответа `get_state()` и `capture_frame()` для всех устройств |

## Запуск

> **Остановите `tomograph_server` перед запуском тестов оборудования.**
> Пока сервер работает, устройства заняты им: камера XIMEA не открывается,
> моторы отдают `Motor.open(): open failed`, а на tty источника в контейнере
> оказывается два файловых дескриптора.
> ```bash
> ./stop.sh                 # остановить сервер
> pytest -m hardware ...    # прогнать тесты
> ./restart.sh              # поднять сервер обратно
> ```

```bash
# Из корня проекта rbtm-drivers-next/

# Тесты без железа (заглушки) — можно гонять где угодно
pytest -v drivers/tests/test_detector_offline.py

# Все тесты оборудования
pytest --log-cli-level=INFO -s -v -m hardware drivers/tests/

# Один конкретный файл
pytest --log-cli-level=INFO -s -v drivers/tests/test_shutter.py

# Один тест
pytest --log-cli-level=INFO -s -v drivers/tests/test_detector.py::test_detector_connection
```

> Флаг `-s` обязателен для вывода `logging.info()` в консоль.  
> Флаг `--log-cli-level=INFO` выводит логи в реальном времени.

### Маркер `hardware`

Тесты, которым нужно физически подключённое оборудование, помечены
`@pytest.mark.hardware` (маркер зарегистрирован в [`pytest.ini`](../../pytest.ini)
в корне проекта):

```bash
pytest -m hardware drivers/tests/       # только железные
pytest -m "not hardware" drivers/tests/ # только те, что работают без железа
```

Модули `test_detector.py` / `test_detector_perf.py` дополнительно
пропускаются целиком, если XIMEA SDK не установлен.

## Тесты по устройствам

### `test_detector_offline.py` — драйвер детектора без железа

Камера подменяется заглушкой (`monkeypatch` модуля `xiapi` внутри драйвера),
XIMEA SDK не нужен. Проверяется:
- кэш модели и размер пикселя, одиночный WARNING при откате на значение по умолчанию;
- `close_device()` при ошибке конфигурации в `__init__`;
- ленивый старт захвата и один программный триггер на кадр;
- смена экспозиции без stop/start;
- идемпотентность `start_acquisition()` / `stop_acquisition()`;
- ошибка посреди серии (`Xi_error` и `MemoryError`) → сброс состояния и
  перезапуск захвата на следующем кадре;
- зависание `xiGetImage` → `DetectorHangError` + колбэк `on_hang`,
  зависшая камера больше не трогается;
- идемпотентный `close()`;
- формула таймаутов (`sdk_timeout_ms` / `expected_frame_timeout_s`).

---

### `test_detector.py` — детектор XIMEA (маркер `hardware`)

#### `test_detector_connection`
Быстрая проверка без захвата кадра (~2 с):
- модель камеры — непустая строка;
- размер пикселя > 0;
- `get_state()` содержит ключи `exposure`, `sensor_temp`, `hous_temp`;
- температуры сенсора и корпуса в диапазоне −50…+50 °C.

#### `test_detector_capture`
Захват кадров с экспозицией 0.1 с:
- в `__init__` захват не стартует, его поднимает первый `get_frame()`;
- результат — `numpy.ndarray`, dtype `uint16`, 2D (H×W);
- второй кадр снимается без повторного старта захвата.

#### `test_detector_explicit_acquisition_cycle`
Явный цикл `start_acquisition()` → кадры → `stop_acquisition()` (так работает
Flask-слой в эксперименте): идемпотентность start/stop, смена экспозиции на
лету, ленивый перезапуск захвата после остановки.

---

### `test_detector_perf.py` — накладные расходы на кадр (маркер `hardware`)

#### `test_detector_frame_overhead[exp=0.1s|1.0s|10.0s]`
Меряется **overhead = время кадра − экспозиция** (триггер, чтение матрицы,
передача по FireWire), абсолютные времена не сравниваются:
- средний overhead ≤ `OVERHEAD_BUDGET_S` (0.75 с);
- overhead не отрицательный;
- таблица mean/min/max выводится через `logging.info()`.

Исторический ориентир: удалённый legacy-режим добавлял 100–250 мс на кадр.

---

### `test_motors.py` — шаговые двигатели

#### `test_angle_motor`
Угловой (вращательный) мотор:
1. чтение `get_info()`, `get_status()`, `get_power_info()`;
2. запомнить `pos_0 = get_position_deg()`;
3. `move_to_position_deg(pos_0 + 2°)`;
4. assert: `|position - target| < 0.1°`;
5. вернуться: `move_to_position_deg(pos_0)`;
6. assert: `|position - pos_0| < 0.1°`.

#### `test_horizontal_motor`
Горизонтальный (линейный) мотор — **только шаговые методы** (`steps_on_deg=None`):
1. чтение `get_info()`, `get_status()`, `get_power_info()`;
2. запомнить `pos_0 = get_position()` (шаги);
3. `move_by_delta(+100 шагов)`;
4. assert: `|position - (pos_0 + 100)| < 5 шагов`;
5. вернуться: `move_by_delta(-100 шагов)`;
6. assert: `|position - pos_0| < 5 шагов`.

---

### `test_shutter.py` — заслонка Ke-USB24R

#### `test_shutter_info`
- серийный номер — непустая строка;
- версия прошивки (с graceful fallback если модуль не поддерживает);
- `get_all_relay_states()` — dict с ключами 1, 2, 3, 4 и bool-значениями;
- `read_adc(1)` — `raw` в диапазоне 0–1023, `voltage_v` в 0.0–5.0 В.

#### `test_shutter_open_close`
- `close_shutter()` → assert закрыта;
- `open_shutter()` → assert открыта;
- `close_shutter()` → assert закрыта.

---

### `test_source.py` — рентгеновский источник

#### `test_source_connection`
Только чтение, **без включения высокого напряжения**:
- `get_id()` — непустая строка;
- `get_tube_name()` — непустая строка;
- `get_status()` — три раздела: `power status`, `warming status`, `interlock status`;
- все значения в статусе — `bool`;
- `is_on_high_voltage()` — возвращает `bool`;
- `get_error()` — логируется с предупреждением если не `None`.

> ⚠️ Тест логирует состояние блокировок (`interlock status`) — это позволяет быстро проверить, закрыты ли двери защитного кожуха.

---

### `test_tomograh.py` — томограф

#### `test_tomograph_state`
Создаёт `HWTomograph(mock=True)` (источник в режиме mock — ВН не включается):
- `get_state()` возвращает dict;
- присутствуют все 5 ключей: `shutter`, `source`, `horizontal_motor`, `angle_motor`, `detector`;
- каждое значение — непустой dict;
- для каждого устройства присутствуют ожидаемые ключи состояния.

#### `test_tomograph_capture_frame`
`capture_frame(exposure_s)` — кадр и метаданные одним серверным вызовом:
- кадр — `numpy.ndarray` uint16, 2D;
- метаданные содержат разделы `image_data`, `object`, `shutter`, `X-ray source`
  ровно с теми ключами, что раньше собирал Flask-слой;
- `object` содержит только `angle position` и `horizontal position` —
  `present` и `vertical position` добавляет Flask-слой.

## Допуски точности

| Параметр | Допуск |
|---|---|
| Угловой мотор | ±0.1° |
| Горизонтальный мотор | ±5 шагов |
| Температуры детектора | −50…+50 °C |
| АЦП заслонки raw | 0–1023 |
| АЦП заслонки voltage | 0.0–5.0 В |

## Требования

- `tomograph_server` остановлен (см. «Запуск») — иначе устройства заняты сервером.
- Оборудование должно быть физически подключено (кроме `test_detector_offline.py`
  и `test_tomograph_state` с `mock=True` для source).
- Для моторов: объект должен находиться в безопасной позиции для небольшого движения (+2° / +100 шагов).
- pytest, установленные зависимости проекта (см. [`../../requirements.txt`](../../requirements.txt)).
