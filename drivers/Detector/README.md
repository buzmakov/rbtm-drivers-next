# Detector — драйвер рентгеновского детектора

Драйвер для работы с камерами XIMEA серии xiRAY (монохромный CMOS-детектор с рентгеновским сцинтиллятором). Использует официальный Python API XIMEA (`xiapi`).

## Поддерживаемые модели

| Модель | Размер пикселя |
|---|---|
| `MH110XC-KK-FA` | 9.0 мкм |
| `MJ150XR-GP-FA-GO` | 4.25 мкм |
| *(прочие)* | 4.25 мкм (по умолчанию) |

Список задаётся в константе [`PIXEL_SIZES`](Detector.py:25).

## Файлы

| Файл | Описание |
|---|---|
| [`Detector.py`](Detector.py) | Класс `HWDetector` — основной драйвер |
| [`ximea/`](ximea/) | Python-биндинги XIMEA API (xiapi) |

## Класс `HWDetector`

```python
from drivers.Detector.Detector import HWDetector

d = HWDetector()
```

При инициализации:
- открывает первое найденное USB-устройство XIMEA;
- отключает авто-гейн (`disable_aeag`);
- устанавливает усиление 0 дБ;
- включает охлаждение в режим AUTO с целевой температурой **15 °C**;
- устанавливает формат пикселей **XI_MONO16** (16-бит, uint16).

При завершении программы соединение закрывается автоматически через `atexit`.

### Методы

#### Информация об устройстве

| Метод | Возвращает | Описание |
|---|---|---|
| `get_model()` | `str` | Имя модели из прошивки камеры |
| `get_pixel_size()` | `float` | Физический размер пикселя, мм |

#### Температуры

| Метод | Возвращает | Описание |
|---|---|---|
| `get_sensor_temp()` | `float` | Температура CMOS-сенсора, °C |
| `get_hous_temp()` | `float` | Температура корпуса камеры, °C |

#### Параметры экспозиции и усиления

| Метод | Возвращает | Описание |
|---|---|---|
| `get_exposure()` | `float` | Текущая экспозиция в секундах |
| `get_gain()` | `float` | Текущий цифровой гейн, дБ |
| `set_gain(gain)` | — | Установить цифровой гейн, дБ |

#### Захват кадров

```python
frame = d.get_frames(exposure=0.5, number_frames=3)
# → numpy.ndarray, dtype=uint16, shape=(H, W)
```

| Параметр | Тип | Описание |
|---|---|---|
| `exposure` | `float` | Экспозиция в секундах |
| `number_frames` | `int` | Количество кадров для накопления (суммирование) |

Возвращает `numpy.ndarray` dtype `uint16`. При `number_frames > 1` кадры суммируются в `uint32` и обрезаются до 65535.

#### Состояние

```python
state = d.get_state()
# → {'exposure': 0.5, 'sensor_temp': 14.8, 'hous_temp': 22.1}

state = d.get_state(['model', 'exposure'])
# → {'model': 'MJ150XR-GP-FA-GO', 'exposure': 0.5}
```

Допустимые ключи `get_state()`: `exposure`, `sensor_temp`, `hous_temp`, `model`.

## Конфигурация

Детектор не имеет отдельной секции в [`devices.cfg`](../config/devices.cfg) — камера открывается как первое найденное USB-устройство XIMEA.

## Зависимости

- **ximea xiapi** — устанавливается через пакет XIMEA Software Package.  
  На Linux: `sudo apt-get install libximea`. Путь к биндингам настраивается в [`Detector.py:9`](Detector.py:9).
- `numpy`
- `autologging`

## Известные ограничения и TODO

- Нет поддержки ROI (Region of Interest).
- Нет параметра rot90 для поворота изображения.
- Нет явного ожидания достижения целевой температуры охлаждения при инициализации.
- Поддержка только первого подключённого устройства (нет выбора по индексу или серийному номеру).

## Segfault в libm3api.so.2 и постоянный режим захвата

С 01.2025 по 09.2026 процесс `tomograph_server` 37 раз падал с одинаковым
`segfault at 77 ... in libm3api.so.2` (xiAPI V4.27.21). Разбор дизассемблера
библиотеки (14.09.2026): инструкция падения — `cmp byte [rdi+0x78], 0` при
`rdi = -1`. Поле контекста камеры `+0x28b8` (объект таймаута) записывается
значением `-1` в `mmStopAcquisition` и в путях ошибки `mmStartAcquisition`,
а `mm_WorkerThread` читает его без проверки на `-1` (у `mu_WorkerThread`,
`md_`, `mq_` проверка есть). Это гонка внутри SDK между остановкой захвата и
его рабочим потоком.

В «legacy»-режиме `get_frames()` делает `xiStartAcquisition` +
`xiStopAcquisition` на **каждый** кадр — сотни шансов на гонку за
эксперимент. Поэтому эксперимент теперь включает постоянный режим:

```python
detector.start_acquisition(exposure_s, use_trigger=True)   # один раз на эксперимент
detector.get_frames(exposure_s)                             # software trigger на кадр
detector.stop_acquisition()                                 # один раз в конце (finally)
```

См. `Tomograph.detector_start_acquisition()` / `detector_stop_acquisition()`
в `experiment/tomograph.py`; при ошибке включения режима драйвер остаётся в
legacy-режиме и пишет предупреждение в лог. Превью из UI вне эксперимента
по-прежнему идут через legacy-режим.

Сопутствующее:

- Захват выполняется в одном долгоживущем потоке; при зависании SDK (USB/FireWire
  обрыв) процесс завершается через `os._exit(1)` **без** `atexit` — раньше
  `sys.exit(1)` закрывал камеру из-под зависшего `xiGetImage`, что само по себе
  воспроизводит ту же гонку, и к тому же блокировался в `ThreadPoolExecutor.shutdown`.
- `docker-compose.yml`: `ulimits.rtprio=99` + `cap_add: SYS_NICE`, чтобы xiAPI мог
  поднять приоритет рабочих потоков (иначе в логе `Failed to change thread scheduler`).
- Актуальная LTS xiAPI — V4.32.00 (10.2025); обновление пакета в `vendor/ximea`
  остаётся отдельной задачей, публичный changelog про этот segfault молчит.
