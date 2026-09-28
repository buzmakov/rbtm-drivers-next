# Detector — драйвер рентгеновского детектора

Драйвер для работы с камерами XIMEA серии xiRAY (монохромный CMOS-детектор с рентгеновским сцинтиллятором). Использует официальный Python API XIMEA (`xiapi`).

Рабочая камера томографа — **MH110XC-KK-FA, подключение по FireWire (IEEE 1394)**, xiAPI V4.27.21.

## Поддерживаемые модели

| Модель | Размер пикселя |
|---|---|
| `MH110XC-KK-FA` | 9.0 мкм |
| `MJ150XR-GP-FA-GO` | 4.25 мкм |
| *(прочие)* | 4.25 мкм (по умолчанию, с записью WARNING в лог) |

Список задаётся в константе `PIXEL_SIZES` в [`Detector.py`](Detector.py).

## Файлы

| Файл | Описание |
|---|---|
| [`Detector.py`](Detector.py) | Класс `HWDetector` — основной драйвер |
| [`ximea/`](ximea/) | Символьная ссылка на биндинги XIMEA API (`vendor/ximea/api/Python/v3/ximea`) |

## Класс `HWDetector`

```python
from drivers.Detector.Detector import HWDetector

d = HWDetector()
```

При инициализации:
- открывает первое найденное устройство XIMEA;
- отключает авто-гейн (`disable_aeag`), устанавливает усиление 0 дБ;
- включает охлаждение в режим AUTO с целевой температурой **15 °C**;
- устанавливает формат пикселей **XI_MONO16** (16-бит, uint16);
- один раз читает имя модели в `self.model` (от него зависит размер пикселя);
- если конфигурация не удалась, устройство закрывается (`close_device`) до проброса ошибки — иначе камера остаётся занятой и повторная инициализация невозможна.

Соединение закрывается автоматически через `atexit`; `close()` идемпотентен и сам снимает себя с `atexit`.

### Режим захвата

Режим **один**: постоянный захват (`xiStartAcquisition` один раз) + программный триггер `XI_TRG_SOFTWARE` на каждый кадр. Прежний «legacy»-режим (start/stop на каждый кадр) удалён — см. раздел про segfault ниже.

```python
# Вариант 1 — ленивый: захват поднимается сам на первом кадре
frame = d.get_frame(exposure=0.5)        # numpy.ndarray uint16, (H, W)
frame = d.get_frame(exposure=1.0)        # экспозиция меняется на лету

# Вариант 2 — явный (так делает Flask-слой на эксперимент)
d.start_acquisition(exposure_s)          # один раз в начале
frame = d.get_frame(exposure_s)          # software trigger на кадр
d.stop_acquisition()                     # один раз в конце (finally)
```

Захват остаётся активным между кадрами и останавливается только в `stop_acquisition()` или `close()`. При любой ошибке посреди серии состояние сбрасывается (`_reset_trigger()`: захват остановлен, триггер `XI_TRG_OFF`), и следующий вызов поднимает захват заново.

### Методы

| Метод | Возвращает | Описание |
|---|---|---|
| `start_acquisition(exposure, use_trigger=True)` | — | Запустить постоянный захват. Идемпотентен; повторный вызов только меняет экспозицию. `use_trigger` устарел и игнорируется |
| `stop_acquisition()` | — | Остановить постоянный захват. Идемпотентен |
| `get_frame(exposure)` | `numpy.ndarray` | Снять один кадр (uint16, H×W). Экспозиция в секундах |
| `get_frames(exposure)` | `numpy.ndarray` | Синоним `get_frame()` (совместимость со старым API) |
| `expected_frame_timeout_s(exposure)` | `float` | Верхняя граница длительности кадра — RPC-слой берёт свой таймаут отсюда |
| `close()` | — | Остановить захват, закрыть устройство, погасить поток захвата |
| `get_model()` | `str` | Имя модели (кэш из `__init__`) |
| `get_pixel_size()` | `float` | Физический размер пикселя, мм |
| `get_sensor_temp()` | `float` | Температура CMOS-сенсора, °C |
| `get_hous_temp()` | `float` | Температура корпуса камеры, °C |
| `get_exposure()` | `float` | Текущая экспозиция в секундах (с камеры) |
| `get_state(options=None)` | `dict` | Состояние по ключам `exposure`, `sensor_temp`, `hous_temp`, `model` |

### Состояние

```python
state = d.get_state()
# → {'exposure': 0.5, 'sensor_temp': 14.8, 'hous_temp': 22.1}

state = d.get_state(['model', 'exposure'])
# → {'model': 'MH110XC-KK-FA', 'exposure': 0.5}
```

### Таймауты и зависание захвата

Одна формула на весь драйвер (константы в начале модуля):

```
sdk_timeout_ms = exposure_ms * SDK_TIMEOUT_FACTOR(1.5) + SDK_TIMEOUT_MARGIN_MS(500)
hard_timeout_s = sdk_timeout_s + HARD_TIMEOUT_MARGIN_S(15)
```

`sdk_timeout_ms` уходит в `xiGetImage`, `hard_timeout_s` — внешнему watchdog'у: при обрыве шины SDK уходит в бесконечный цикл сброса эндпоинтов и не возвращается даже со своим таймаутом. Значение `hard_timeout_s` доступно снаружи как `expected_frame_timeout_s(exposure)` (и модульная функция, и метод) — **таймаут RPC-слоя обязан быть больше него**, иначе прокси отвалится раньше, чем драйвер сообщит о зависании.

При превышении `hard_timeout_s` драйвер:

1. помечает детектор как зависший — камера больше не трогается вообще (ни `stop_acquisition`, ни `close_device`: поток захвата сидит внутри `xiGetImage`, и любое обращение из главного потока воспроизводит гонку, роняющую процесс);
2. вызывает колбэк `on_hang(exc)`;
3. бросает `DetectorHangError(RuntimeError)`.

Решение «завершить процесс» принимает владелец процесса, а не драйвер устройства:

```python
from drivers.Detector import Detector

def _die(exc):           # в tomograph_server.py
    logging.critical('detector hang: %s', exc)
    os._exit(1)          # Docker с restart: unless-stopped поднимет контейнер

Detector.set_on_hang(_die)          # процессный колбэк
# либо HWDetector(on_hang=_die)     # для конкретного экземпляра
```

## Конфигурация

Детектор не имеет отдельной секции в [`devices.cfg`](../config/devices.cfg) — камера открывается как первое найденное устройство XIMEA.

## Зависимости

- **ximea xiapi** — биндинги вендорятся в `vendor/ximea/api/Python/v3/ximea`, каталог `drivers/Detector/ximea` — символьная ссылка на них. Альтернатива: установленный в систему XIMEA Software Package (`libximea`), тогда работает запасной импорт `from ximea import xiapi`.
- `numpy`
- `autologging`

## Тесты

- `drivers/tests/test_detector_offline.py` — логика драйвера на заглушке камеры, железо не нужно;
- `drivers/tests/test_detector.py`, `drivers/tests/test_detector_perf.py` — маркер `hardware`, нужна камера и **остановленный `tomograph_server`**.

## Известные ограничения и TODO

- Нет поддержки ROI (Region of Interest).
- Нет параметра rot90 для поворота изображения.
- Нет явного ожидания достижения целевой температуры охлаждения при инициализации.
- Поддержка только первого подключённого устройства (нет выбора по индексу или серийному номеру).
- Верхняя граница экспозиции нигде не проверяется.
- `_current_exposure_us` хранит запрошенное значение, а не фактическое (сравнение с фактическим заставляло бы вызывать `set_exposure_direct` на каждый кадр из-за квантования).

## Segfault в libm3api.so.2 и постоянный режим захвата

С 01.2025 по 09.2026 процесс `tomograph_server` 37 раз падал с одинаковым
`segfault at 77 ... in libm3api.so.2` (xiAPI V4.27.21). Разбор дизассемблера
библиотеки (14.09.2026): инструкция падения — `cmp byte [rdi+0x78], 0` при
`rdi = -1`. Поле контекста камеры `+0x28b8` (объект таймаута) записывается
значением `-1` в `mmStopAcquisition` и в путях ошибки `mmStartAcquisition`,
а `mm_WorkerThread` читает его без проверки на `-1` (у `mu_WorkerThread`,
`md_`, `mq_` проверка есть). Это гонка внутри SDK между остановкой захвата и
его рабочим потоком.

В «legacy»-режиме `get_frames()` делал `xiStartAcquisition` +
`xiStopAcquisition` на **каждый** кадр — сотни шансов на гонку за
эксперимент. Этот режим удалён целиком: остался один постоянный захват
(`start_acquisition` один раз на эксперимент, программный триггер на кадр,
`stop_acquisition` в конце). Автоматического отката в legacy при ошибке
больше нет — при ошибке захват перезапускается в том же режиме.

Сопутствующее:

- Захват выполняется в одном долгоживущем потоке (`ThreadPoolExecutor(max_workers=1)`):
  `xiGetImage` всегда вызывается из одного и того же OS-потока.
- При зависании SDK драйвер бросает `DetectorHangError` и не трогает камеру;
  процесс завершает владелец процесса через колбэк `on_hang` (см. выше).
  Раньше драйвер сам делал `os._exit(1)`: это убивало идущий эксперимент,
  если таймаут ловился на превью из UI. `sys.exit(1)` использовать нельзя —
  он запускает `atexit` → `close()` → `xiStopAcquisition`/`xiCloseDevice`
  из главного потока под зависшим `xiGetImage`, т.е. ровно ту же гонку,
  и вдобавок блокируется в `ThreadPoolExecutor.shutdown(wait=True)`.
- `docker-compose.yml`: `ulimits.rtprio=99` + `cap_add: SYS_NICE`, чтобы xiAPI мог
  поднять приоритет рабочих потоков (иначе в логе `Failed to change thread scheduler`).
- Актуальная LTS xiAPI — V4.32.00 (10.2025); обновление пакета в `vendor/ximea`
  остаётся отдельной задачей, публичный changelog про этот segfault молчит.
