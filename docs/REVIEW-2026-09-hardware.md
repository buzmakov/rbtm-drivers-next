# Ревью аппаратной части rbtm-drivers-next (сентябрь 2026)

Ветка: `review/hardware-cleanup`. База: `develop` @ `122701d`.

Что смотрели: всё, кроме `vendor/` — драйверы (`drivers/`), агрегатор `HWTomograph`,
Redis-прокси, `tomograph_server.py`, Flask-слой (`experiment/`), Docker/скрипты, README, тесты.
Код писали разные агенты в разное время; ниже — то, что накопилось, и план чистки.
Ссылки вида `file:line` даны по состоянию базы.

---

## 1. Главное

| # | Проблема | Где | Риск |
|---|---|---|---|
| 1 | **Redis-прокси — универсальный RPC «любой класс, любой экземпляр»** с `create/delete/auto-create`, pickle и `LazyProxy`. Нужен был только чтобы Flask переживал падение `tomograph_server`. Сейчас это 745 строк × 2 копии, из которых работает ~150. Побочные эффекты: утечка `HWTomograph` на сервере при рестарте Flask (моторы заняты → `Motor.open(): open failed`), потеря типа исключения, крэш-луп Flask при недоступном железе (см. §2.1). | `redis_proxy.py`, `experiment/redis_proxy.py`, `experiment/tomograph.py:14-32` | высокий |
| 2 | **Однопоточный сервер железа** → костыли по всему коду: `source_power_on_async` (поток внутри `HWTomograph`), `blocking=False` у моторов, флаг `_warming_up` и ранние выходы в 4 методах источника, «превью из UI ломает эксперимент». | `Tomograph.py:185-206`, `Motor.py:250-269`, `XRaySource.py:202,394,658,804,867` | высокий |
| 3 | **Таймауты не согласованы**: прокси 60 с × 1 попытка; полный оборот 32400/500 ≈ 65 с; hard-timeout детектора `2·exp + 15 с` > 60 с при экспозиции ≥ 22.5 с; `command_wait_for_stop(id, 10)` — это интервал опроса, а не таймаут (ждёт вечно). | `experiment/tomograph.py:26-31`, `Motor.py:268,287,305`, `Detector.py:225` | высокий |
| 4 | **Драйвер источника расходится с руководством ISOVOLT**: `PA` — номер программы, а не мощность (мощность — `RP`); `PN` не существует; блок `interlock status` читает не те биты SR:30 (двери/E-STOP там нет — это коды SR:12 35/43/46/63-65); коды 1–32 в `STATUS_STRINGS` выдуманы. | `XRaySource.py:43-74, 701-707, 907, 942` | средний (в проде не используется, но `get_state` ломается) |
| 5 | **Ошибки глотаются**: `get_error()` возвращает `None` и «нет ошибки», и «нет связи» → `on_high_voltage()` при мёртвом порте «успешен»; `set_voltage()` не проверяет остаточный `error`; `get_model()` при ошибке подставляет 4.25 мкм вместо 9 мкм; `check_request` ловит только `TypeError`. | `XRaySource.py:1202, 1059`, `Detector.py:191-202`, `routes.py:429-438` | средний |
| 6 | **`atexit.register(self.close)` в каждом драйвере** держит сильные ссылки; объекты никогда не собираются; при ленивой переинициализации детектора копятся executor-потоки. | `Motor.py:42`, `Detector.py:46`, `XRaySource.py:220` | низкий |
| 7 | **Гонка в `warmup()`**: хвост (`HV:1` + `SR:12`) выполняется вне `_port_lock`, а `get_error`/`read_status_word`/`set_current` флаг `_warming_up` не проверяют. | `XRaySource.py:547-561` | средний |
| 8 | **Дублирование**: `redis_proxy.py` ×2 (побайтно), `tomologger.py`/`hwtomologger.py`, `Experiment`/`AdvancedExperiment` (~150 общих строк), persistent/legacy пути в `get_frames`, `get_state` двух моторов, 4× `wait_for_*` в источнике, `carry_out_*_experiment` ×2. | см. §3 | низкий, но мешает править |

---

## 2. Архитектура и Redis-прокси

### 2.1 Что делает прокси сейчас

```
routes.py (import time) → Tomograph() → RedisProxy.create(HWTomograph-заглушка) → 'create' → сервер: HWTomograph()
self.hwtomo.source.off_high_voltage()  → LazyProxy('source') → LazyProxy('source.off_high_voltage') → 'call'
```

Что в этом плохо:

- **`create` на импорте `routes.py`** (`routes.py:18` → `experiment/tomograph.py:32`). Если железо не инициализируется, `create` падает через 60 с, Flask не стартует, Docker перезапускает контейнер, и так каждую минуту (07.09.2026 — 35 попыток). При каждой попытке сервер создаёт новый `HWTomograph`: раньше это переоткрывало порт источника (исправлено в `04310be`), а моторы уходили в `open failed`.
- **Экземпляры на сервере никогда не удаляются**: `__del__` прокси (`redis_proxy.py:530-538`) вызывается только при штатном выходе Python. После рестарта Flask старый `HWTomograph` остаётся в `server.instances` с открытыми хендлами моторов; новый `create` получает занятые контроллеры.
- **`auto_create_instances`** (`redis_proxy.py:466-472`): после рестарта сервера любой вызов молча создаёт новый `HWTomograph` без аргументов. Это и есть «возобновление после падения». Работает, но равносильно синглтону, — только неявному.
- **Исключения теряют тип**: сервер шлёт `{'type','message','traceback'}`, клиент бросает `Exception("RuntimeError: ...")` (`redis_proxy.py:624`). Flask ловит только `ModExpError` → любой отказ железа = HTTP 500 с трейсбеком (в проде `FLASK_DEBUG=1`).
- **Повтор при таймауте перекладывает запрос в очередь заново** (`redis_proxy.py:597-607`): при `max_retries>1` сервер выполнит команду дважды (сейчас спасает `max_retries=1`). Запрос, не дождавшийся ответа, всё равно будет выполнен сервером позже; ключ `response_<uuid>` без TTL остаётся в Redis навсегда.
- **`RedisProxyServer.__init__` вызывает `self.run()`** — блокирующий цикл в конструкторе (`redis_proxy.py:433`); `server.start()` в `tomograph_server.py:22` недостижим. Плюс `while True` вокруг `main()` (`tomograph_server.py:33-39`) при том, что `main()` сам ловит всё и делает `sys.exit(1)`.
- **Мёртвое внутри**: `SafeSerializer` — numpy пиклится штатно, ветка base64 недостижима; `UnpicklableObject`; арифметические `__add__`… у `LazyProxy`; `setattr`; `multiprocessing`; демо в `__main__`; хак `init_func.__globals__[...]` (`redis_proxy.py:641-646`) — функции и так в глобалах модуля; `global logger` с подменой root-логгера.
- **`class HWTomograph: pass`** в `experiment/tomograph.py:14` — заглушка, чтобы прокси узнал имя класса.

### 2.2 Нужен ли Redis вообще

Отдельный процесс нужен: xiAPI роняет процесс segfault'ом, и Flask должен это пережить. Redis как транспорт — нормально (уже развёрнут, даёт очередь и переживает рестарт любой стороны). Плохой не транспорт, а протокол.

**Предложение** (ветка `refactor/redis-rpc`): переписать `redis_proxy.py` в ~150 строк:

- Сервер владеет **одним** `HWTomograph`, создаёт его сам при старте (и пересоздаёт при ошибке по таймеру); клиент ничего не «создаёт».
- Протокол: `{'id', 'method': 'source.off_high_voltage', 'args', 'kwargs'}` → `{'id', 'result'}` или `{'id', 'error': {'type', 'message', 'traceback'}}`. Сериализация: pickle (кадры numpy) — оставить, но без `SafeSerializer`.
- Клиент: `HardwareClient(redis).call('angle_motor.get_position_deg')` + тонкие обёртки; исключение `HardwareError(type, message)` с сохранённым типом; `HardwareUnavailable` при таймауте. Без `LazyProxy`, `__getattr__`-магии и `HWTomograph`-заглушки.
- Один `request_queue`, ответы с `expire`. Таймаут запроса — параметр вызова (кадр: `exp·2+30`, оборот: 120 с, остальное: 10 с), а не один глобальный.
- Flask не должен падать, если сервер железа недоступен: `Tomograph()` ничего не шлёт в Redis; `/state` отдаёт `unavailable`.

### 2.3 Однопоточность сервера

Пока сервер обрабатывает один запрос за раз, любое длинное действие (прогрев до 30 мин, оборот 65 с, кадр 10 с) блокирует опросы UI. Отсюда потоки внутри драйверов и `blocking=False`. Варианты:

- (минимальный) оставить один поток, но **длинные операции делать асинхронными на сервере единообразно**: `start_job(name)` / `job_status(name)`, как уже сделано для `source_power_on_async`. Убрать `blocking=False` из драйверов моторов (`move_to_position` всегда ждёт с таймаутом), а неблокирующее движение для юстировки делать через тот же job-механизм.
- (лучше) два воркера на сервере: «быстрые» запросы (get_position, is_open, temperatures, source status) и «медленные» (кадр, движение, прогрев), с локом на устройство. Тогда UI живёт во время эксперимента, а превью/затвор блокируются явно при активном эксперименте (см. §3.4).

---

## 3. По компонентам

### 3.1 Источник ISOVOLT 3003 (`drivers/XRaySource/`)

Используется из прода: `get_shared`, `on_high_voltage`, `off_high_voltage`, `is_on_high_voltage`, `get_status`,
`set_voltage`, `set_current`, `get_actual_voltage`, `get_actual_current`, атрибуты `mock`, `last_*_nominal`.

Мёртвое: `_transact` (`:1249`, при этом его логика размазана руками по `set_voltage`/`warmup` — использовать, а не удалять),
`is_on_high_volatge` (`:406`), `set_state` (`:1343`, вместе с `HWTomograph.set_state = pass`), `set_power` (`:1089`, команды `SP` в протоколе нет),
`get_nominal_power`/`get_actual_power` (`:889-960`, оба на несуществующих/неверных командах), `sw_30` в цикле прогрева (`:507-509`),
`error_answer` (`:992, :1024`), `get_id`/`get_tube_name`/`get_state` — только тесты.

Ошибки:
- `PA` ≠ мощность, `PN` не существует (§1.4). `get_state()` падает `RuntimeError` при таймауте `PN` — обработчик без try/except (`:1336-1340`).
- Блок `interlock status` из битов SR:30 — ложные `door*/emergency stop`. Отсюда «аномалия» в `README.md:154-158` и skip в `test_source.py:253-272`.
- Хвост `warmup()` вне лока (`:547-561`); `get_error`/`read_status_word`/`get_nominal_*`/`set_*` не смотрят `_warming_up` → UI виснет на локе до 30 мин.
- `get_error()` → `None` при сбое связи (`:1202`); `on_high_voltage()` считает это успехом.
- `set_voltage()`: ветки 106/109/119 переприсваивают `error`, но после блока он не проверяется (`:1059`) — метод рапортует успех и обновляет кэш.
- Три разных белых списка «неошибок»: `(106,109,118,119)` `:456`, `(106,109,118,120)` `:476,:557`; при этом 76 (Stand-By) везде считается ошибкой (`:1198`).
- `CL` «на всякий случай» с `bare except` в начале `set_voltage` (`:977-982`) гасит реальные ошибки до того, как их прочитали; `bare except` также `:1010`.
- `get_status()` при любом сбое возвращает `in progress: True` (`:710-735`) — смерть порта выглядит как прогрев.
- `warmup()` может завершиться мгновенно: первый опрос через 5 с до того, как генератор поднял биты SW6 (`:482, :520`).
- `SV`/`SC` шлются `zfill(6)`, в руководстве формат 5 разрядов (`:984, :1078`) — проверить на железе.
- `xonxoff` не включён, хотя README обещает XON/XOFF (`README.md:21`).

Документация: `README.md:38,179` «WU:4 = прогрев от PC» (по руководству 4 = по часам генератора); `README.md:193-202` про `PN/PA` и «В × А»; `README.md:218` «CL в on_high_voltage()» — нет; docstring `_write_command` «захватывает лок» — нет (`:1236`); docstring `warmup` «~90 с» (`:415`); «кэшируется до следующего вызова» (`:1118,:1148`) — навсегда.

### 3.2 Моторы XIMC и затвор Ke-USB24R (`drivers/Motors/`, `drivers/XRayShutter/`)

Мёртвое: `HWMotor = HWRotaryMotor` (`Motor.py:584`), `print_test_info` (`:587-608`, не освобождает `devenum`), `move_by_delta*` (только тесты),
мм-слой `get_position_mm/move_to_position_mm` (`:488-513`; прод работает с горизонтальным мотором **в шагах**: `experiment/tomograph.py:229,273,312`, кроме `move_away()` — в мм),
`HWShutter.set_state/reset/get_firmware_version/get_serial_number/get_all_relay_states/read_adc` — только тесты; весь `get_state`-слой — только `test_tomograh.py`.

Ошибки:
- `command_wait_for_stop(id, 10)` — 10 мс это интервал опроса; таймаута нет, результат не проверяется, docstring обещает `RuntimeError`.
- `get_position_deg()` без нормализации в [0,360); `set_angle` делает `%= 360` → возврат 359.5→0 идёт длинным путём ~65 с > таймаут прокси 60 с (комментарий `experiment/tomograph.py:26` утверждает обратное).
- `move_away()` в мм, `move_back()` в шагах — совпадает только потому, что 0 == 0.
- `HWShutter.close()` закрывает заслонку, у всех остальных `close()` освобождает ресурс; `_release_devices` обходит это молча (`Tomograph.py:106-117`).
- `get_info/get_power_info/get_status` возвращают `repr()` (строки `"'XIMC'"` вместо значений).
- `exit()` при ошибке импорта pyximc (`Motor.py:11,16`) — библиотека убивает процесс.
- Затвор: порт открывается/закрывается на каждую команду (2–4 раза за `set_state`), каждое открытие CDC-ACM дёргает DTR; `$KE` шлётся дважды при каждом создании объекта (`XRayShutter.py:88-91`); `serial.Serial(timeout=5)` без `write_timeout`.
- `conftest.py:25-36` открывает порт ISOVOLT при любом запуске pytest (даже тестов моторов).

Дублирование: `get_state` двух моторов (`:405-437` vs `:544-578`), перевод в шаги/микрошаги ×3, четыре одинаковых блока get/set в `_configure` с сообщениями «Motor.open() failed», `open()/close()` затвора отличаются одним символом.

### 3.3 Детектор XIMEA (`drivers/Detector/`)

Обход segfault (`122701d`) реализован аккуратно, но:
- **Legacy-путь (start/stop на кадр) остался** и включается автоматически при любой `Xi_error` посреди серии (`Detector.py:341-358`) — т.е. драйвер сам возвращается в режим, который роняет процесс. Предложение: постоянный захват стартует один раз (в `__init__` или лениво), останавливается только в `close()`; `use_trigger=False`, `number_frames` (всегда 1 в проде) и legacy-цикл удалить.
- `os._exit(1)` внутри драйвера устройства (`:238-272`): политика «убить процесс» должна быть в `tomograph_server.py`, драйвер бросает `DetectorHangError`. Сейчас hard-timeout, пойманный на превью из UI, убивает идущий эксперимент.
- `atexit.register` до второго `try` в `__init__` (`:46-60`): при ошибке `set_cooling`/`set_imgdataformat` устройство остаётся открытым, а ленивая переинициализация в `HWTomograph.detector` получит занятое устройство. `close()` не делает `executor.shutdown()`.
- `get_model()` глотает ошибку → `'Ximea xiRAY'` → пиксель 4.25 мкм вместо 9 мкм для MH110XC без записи в лог (`:191-202`; дубль в `experiment/tomograph.py:321-331`).
- Ловится только `Xi_error` (`:341`); `MemoryError`/`RuntimeError` оставляют `_acquisition_active=True`.
- Три `except Exception: pass` вокруг `XI_TRG_OFF` (`:136-139, :161-165, :351-358`).
- Таймауты: `+15 с`, `exp·2`, `exp·1.5+500 мс` — три разных формулы без связи между собой и с таймаутом прокси.
- Верхняя граница экспозиции не проверяется нигде (`experiment/tomograph.py:350-351` закомментировано).
- `_current_exposure_us` хранит запрошенное, а не фактическое значение.

Docstring `get_frames` (`:280-284`) противоречит `:68-70` про потоки; README ссылается на неверные строки, «USB-устройство» (камера FireWire), в таблице методов нет `start/stop_acquisition`.

### 3.4 Flask-слой и эксперимент (`experiment/`)

- **~10 RPC на каждый кадр**: `get_detector_frame_metadata` (`experiment/tomograph.py:372-405`) дёргает модель (дважды), пиксель, экспозицию, две температуры, угол, позицию, затвор (открывает serial-порт!), напряжение, ток — каждый через Redis и через реальное устройство. Предложение: один серверный метод `HWTomograph.capture_frame(exposure_s) -> (image, metadata)`; модель/пиксель кэшируются при инициализации.
- **Детекторные роуты не заблокированы во время эксперимента**: `/detector/get-frame-preview` (`routes.py:206-261`) откроет/закроет затвор посреди data-серии и сменит экспозицию. Нужен 409 при `current_experiment is not None` (превью уже есть в `/experiment/last-frame`).
- `check_request` ловит только `TypeError`; невалидный JSON → голый 500 с трейсбеком на всех POST (`routes.py:429-438`).
- `call_method_create_response` ловит только `ModExpError` (`:409-426`); ошибки железа → 500.
- TOCTOU на `/experiment/start` (`:265-313`): проверка `tomo_state()` и старт потока не атомарны; поток не отслеживается.
- `create_response` возвращает строку → `Content-Type: text/html` для всего API (`:399-406`).
- `Experiment` и `AdvancedExperiment` дублируют `__init__`-статус, `_update_status`, `get_status`, `get_and_send_frame`; `carry_out_simple/advanced_experiment` — копии. Нужен базовый класс.
- Мёртвое: `check_source()` с `print` и `sleep(5)` (`experiment.py:258-273`, вызовы закомментированы), `send_to_webpage` параметр, `HWTomograph`-заглушка, `y_position`/`set_y` (вертикального мотора нет — оставить как явную заглушку или убрать из API вместе с rbtm-web).
- `STORAGE_URI` захардкожен (`constants.py:2`).
- `source_wait_for_ready` до 30 мин с 3 RPC каждые 5 с — нормально, но при мёртвом порте это 30 минут ожидания «прогрева» (см. §3.1 `get_status`).
- `time.sleep(0.5)` перед dark-серией без проверки состояния затвора (`experiment.py:252, :427`).

Роуты, которых нет в readme: `/`, `/shutter/state`, `/motor/set|get-horizontal-position`, `/motor/set|get-vertical-position`, `/detector/get-frame`, `/detector/get-frame-with-closed-shutter`, `/detector/chip_temp`, `/detector/hous_temp`.
Роуты, которые не вызывает `rbtm-web`: `/detector/get-frame-with-closed-shutter`, `/detector/chip_temp`, `/detector/hous_temp`, `/motor/move-away`, `/motor/move-back` — кандидаты на удаление.

### 3.5 Инфраструктура, скрипты, документация

- `experiment/redis_proxy.py` == `redis_proxy.py` (побайтно). `tomologger.py`/`hwtomologger.py` отличаются двумя строками; в обоих неиспользуемый импорт `traced`.
- `restart_fw.sh`, `restart_usb.sh` дублируют `restart.sh fw|usb`; `restart_usb.sh` хардкодит `/dev/bus/usb/004/003`.
- `requirements.txt`: `cachetools`, `ipython` не импортируются; `waitress` только в закомментированном `CMD`; версии не запинены. `matplotlib` нужен только `make_png` (роут `/detector/get-frame`, который rbtm-web использует), `scipy` — `median_filter`.
- `docker-compose.yml`: пробрасываются `/dev/ttyACM0..3` поимённо — если одного нет, контейнер не стартует (`d59be68` убрал `ttyACM4` именно поэтому); `docker-entrypoint.sh` восстанавливает `/dev/ximc/<SERIAL>` через sysfs. Проще: udev-правила на хосте (как уже сделано для `/dev/isovolt`) + проброс `/dev/isovolt`, `/dev/ximc/*`, `/dev/shutter` симлинками. Источник до сих пор пробрасывается как `/dev/ttyUSB0`, хотя `/dev/isovolt` есть с 14.09.
- `redisinsight` в compose — dev-инструмент с `restart: always`; `restart.sh` его не поднимает — убрать в профиль `debug`.
- `Dockerfile`: `FLASK_DEBUG=1` в проде; `waitress` закомментирован.
- readme.md: класс `HWMotor`, ключ `move_object_outside = -4200`, нет `steps_per_mm`/`move_object_outside_mm`/`mock`; таблица API неполная.
- `drivers/tests/README.md` не упоминает `test_detector_perf.py`; `Motors/README.md` рекламирует `print_test_info` и «обратную совместимость» `HWMotor`.
- Тесты открывают устройства напрямую (`test_detector.py:11`, `test_source.py:26`, `test_tomograh.py:35`) — при работающем `tomograph_server` устройства заняты; в контейнере два FD на одном tty источника. Нужен маркер `hardware` и запуск только при остановленном сервере, либо тесты через RPC.

---

## 4. План работ

Ветки-worktree от `review/hardware-cleanup`; каждая — отдельный PR в `develop`, порядок слияния сверху вниз.
Всё, что трогает железо, проверяется на robotom (`restart.sh` + короткий эксперимент + `pytest drivers/tests` при остановленном сервере).

| Ветка | Содержание | Проверка |
|---|---|---|
| `review/hardware-cleanup` (эта) | документ ревью; безопасная чистка: удалить дубль `experiment/redis_proxy.py`, `restart_fw.sh`/`restart_usb.sh`, `redisinsight` → профиль; один `TomoLogger`; `requirements.txt`; readme/README по факту; мёртвый код (`HWMotor`, `print_test_info`, `set_state`-заглушки, `check_source`, `make_png`, `set_power`, `get_*_power`, `PN/PA`, коды 1–32, `is_on_high_volatge`, `_shared_sources` cleanup) | `python -m pyflakes`, импорт модулей, mock-источник |
| `refactor/redis-rpc` | новый прокси (§2.2): синглтон на сервере, явный протокол, типизированные ошибки, таймаут на вызов; `tomograph_server.py` без `while True`; Flask стартует без железа; `call_method_create_response` ловит `HardwareError`; `check_request` ловит `ValueError` | robotom: рестарт сервера во время UI-опроса; `/state` при выключенном сервере |
| `fix/xray-source` | `get_error` различает «нет ошибки»/«нет связи»; проверка остаточного `error` в `set_voltage`; единый белый список кодов (76/106/109/118–121); хвост `warmup` под лок и `_warming_up` во всех методах; убрать `CL`+`bare except`; `interlock status` из SR:12; `_transact` вместо ручных повторов; 4× `wait_for_*` → `_wait_until`; тесты через `get_shared`, `conftest` лениво | robotom, mock-режим локально |
| `fix/motors-shutter` | `wait_for_stop` с таймаутом по `MoveSts`; нормализация угла и короткий путь; единые единицы горизонтального мотора (шаги — как в UI; мм-слой убрать или довести до конца); `HWShutter.close()` → `close_shutter()`; один `serial.Serial` с `write_timeout`; `_units_to_steps`, общий `get_state` в `BaseMotor`; `exit()` → исключение | robotom: оборот, юстировка |
| `fix/detector` | убрать legacy-путь и `number_frames`/`use_trigger=False`; захват стартует один раз; `DetectorHangError` вместо `os._exit` в драйвере (решение в сервере); lifecycle (`close_device` при ошибке init, `executor.shutdown`, `atexit.unregister`); модель/пиксель кэшируются, ошибка логируется; одна формула таймаутов; `capture_frame()` на сервере (1 RPC на кадр); 409 на детекторные роуты при эксперименте | robotom: короткий эксперимент, превью, `journalctl -k | grep segfault` |
| `refactor/experiment-base` | `BaseExperiment` для `Experiment`/`AdvancedExperiment`; один `carry_out_experiment`; верхняя граница экспозиции; `Content-Type: application/json`; лок на старт эксперимента | mock-режим |

Не делаем без отдельного решения: смена транспорта (Redis → HTTP), двухпоточный сервер (§2.3, второй вариант),
удаление роутов, которые не вызывает rbtm-web (нужно согласовать с rbtm-web), возобновление эксперимента после падения.
