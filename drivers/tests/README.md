# drivers/tests — тесты оборудования томографа

Быстрые интеграционные тесты для проверки реального оборудования. Тесты не покрывают все граничные случаи — они предназначены для быстрой диагностики работоспособности каждого устройства при подключении или обслуживании.

## Файлы тестов

| Файл | Устройство | Что проверяет |
|---|---|---|
| [`test_detector.py`](test_detector.py) | Детектор XIMEA | Подключение, метаданные, температуры, захват кадра |
| [`test_motors.py`](test_motors.py) | Угловой и горизонтальный моторы | Подключение, движение туда-обратно с assert точности |
| [`test_shutter.py`](test_shutter.py) | Заслонка Ke-USB24R | Серийный номер, реле, АЦП, цикл открытия/закрытия |
| [`test_source.py`](test_source.py) | Рентгеновский источник ISOVOLT | Идентификация, статус, блокировки — **без включения ВН** |
| [`test_tomograh.py`](test_tomograh.py) | Томограф целиком | Структура ответа `get_state()` для всех устройств |

## Запуск

```bash
# Из корня проекта rbtm-drivers-next/

# Все тесты оборудования
pytest --log-cli-level=INFO -s -v drivers/tests/

# Один конкретный файл
pytest --log-cli-level=INFO -s -v drivers/tests/test_shutter.py

# Один тест
pytest --log-cli-level=INFO -s -v drivers/tests/test_detector.py::test_detector_connection
```

> Флаг `-s` обязателен для вывода `logging.info()` в консоль.  
> Флаг `--log-cli-level=INFO` выводит логи в реальном времени.

## Тесты по устройствам

### `test_detector.py` — детектор XIMEA

#### `test_detector_connection`
Быстрая проверка без захвата кадра (~2 с):
- модель камеры — непустая строка;
- размер пикселя > 0;
- `get_state()` содержит ключи `exposure`, `sensor_temp`, `hous_temp`;
- температуры сенсора и корпуса в диапазоне −50…+50 °C.

#### `test_detector_capture`
Захват одного кадра с экспозицией 0.1 с:
- результат — `numpy.ndarray`, dtype `uint16`, 2D (H×W);
- логируется среднее и максимальное значение пикселей.

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
- `close()` → assert закрыта;
- `open()` → assert открыта;
- `close()` → assert закрыта;
- `set_state({'is_open': True/False})` — проверка интерфейса.

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

## Допуски точности

| Параметр | Допуск |
|---|---|
| Угловой мотор | ±0.1° |
| Горизонтальный мотор | ±5 шагов |
| Температуры детектора | −50…+50 °C |
| АЦП заслонки raw | 0–1023 |
| АЦП заслонки voltage | 0.0–5.0 В |

## Требования

- Оборудование должно быть физически подключено (кроме `test_tomograph_state` с `mock=True` для source).
- Для моторов: объект должен находиться в безопасной позиции для небольшого движения (+2° / +100 шагов).
- pytest, установленные зависимости проекта (см. [`../../requirements.txt`](../../requirements.txt)).
