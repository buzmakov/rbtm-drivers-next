# pytest --log-cli-level=INFO -s -v -m hardware drivers/tests/test_detector_perf.py
"""
Бенчмарк постоянного режима захвата (software trigger).

Запуск (при остановленном tomograph_server — камера должна быть свободна):
    pytest --log-cli-level=INFO -s -v drivers/tests/test_detector_perf.py

Что измеряется
--------------
Накладные расходы на кадр = (время get_frame) − экспозиция: программный
триггер, чтение матрицы, передача кадра по FireWire и упаковка в numpy.
Абсолютные времена не сравниваются — они целиком определяются экспозицией.

Прежнего «legacy»-режима (start/stop acquisition на каждый кадр) больше
нет: он и был источником segfault в libm3api, сравнивать не с чем.
Исторический ориентир: legacy добавлял 100–250 мс на кадр.

Тест параметризован по временам экспозиции: 0.1, 1, 10 с.
"""
import logging
import time

import numpy as np
import pytest

try:
    from ..Detector import Detector as _detector_module
except ImportError as err:  # XIMEA SDK не установлен — железных тестов нет
    pytest.skip("XIMEA SDK is not available: {}".format(err),
                allow_module_level=True)

# Офлайн-тесты (test_detector_offline.py) подсовывают заглушку пакета ximea,
# чтобы модуль драйвера импортировался без SDK. Отличаем её от настоящего
# биндинга по наличию методов у Camera — иначе железные тесты «успешно»
# запустились бы на заглушке.
if not hasattr(_detector_module.xiapi.Camera, 'open_device'):
    pytest.skip("XIMEA SDK is not available (ximea stub is installed)",
                allow_module_level=True)

HWDetector = _detector_module.HWDetector

pytestmark = pytest.mark.hardware

# ── параметры бенчмарка ────────────────────────────────────────────────
#   (exposure_s, n_frames)
#   n_frames уменьшается для длинных экспозиций чтобы тест не длился часами
BENCH_PARAMS = [
    pytest.param(0.1,  10, id="exp=0.1s_n=10"),
    pytest.param(1.0,   5, id="exp=1.0s_n=5"),
    pytest.param(10.0,  3, id="exp=10.0s_n=3"),
]

# Бюджет накладных расходов на кадр, секунды. Величина не зависит от
# экспозиции: это триггер + чтение матрицы + передача кадра.
OVERHEAD_BUDGET_S = 0.75
# ──────────────────────────────────────────────────────────────────────


@pytest.fixture(scope="session")
def detector():
    """Open HWDetector ONCE per pytest session and close at the very end.

    session scope prevents repeated open/close cycles between parametrised
    test cases — each cycle may fail with ERROR 1 (Invalid handle) if the
    bus has not settled after the previous close_device().

    XI_DL_FATAL suppresses xiAPI verbose stdout during benchmark runs.
    """
    d = HWDetector()
    # Suppress xiAPI stdout noise (AllocateBuffers, bandwidth, scheduler warnings).
    d.cam.set_debug_level("XI_DL_FATAL")
    yield d
    d.close()


def _measure(fn, n):
    """Run fn() n times, return timing stats in seconds."""
    times = []
    for _ in range(n):
        t0 = time.perf_counter()
        fn()
        times.append(time.perf_counter() - t0)
    arr = np.array(times)
    return {
        'mean':  float(arr.mean()),
        'min':   float(arr.min()),
        'max':   float(arr.max()),
        'std':   float(arr.std()),
        'total': float(arr.sum()),
        'n':     n,
    }


@pytest.mark.parametrize("exposure_s, n_frames", BENCH_PARAMS)
def test_detector_frame_overhead(detector, exposure_s, n_frames):
    """Накладные расходы на кадр в постоянном режиме захвата.

    Проверяет:
    - кадры корректны (uint16 ndarray) — гейт на осмысленность замеров;
    - средний overhead (mean − exposure) укладывается в OVERHEAD_BUDGET_S;
    - overhead не отрицательный (иначе кадр пришёл до конца экспозиции).
    """
    detector.start_acquisition(exposure_s)
    try:
        # прогрев: первый кадр после смены экспозиции — холодный
        sample = detector.get_frame(exposure_s)
        assert isinstance(sample, np.ndarray) and sample.dtype == np.uint16, \
            "Кадр должен быть uint16 ndarray"

        stats = _measure(lambda: detector.get_frame(exposure_s), n_frames)
    finally:
        detector.stop_acquisition()

    overhead_mean_ms = (stats['mean'] - exposure_s) * 1e3
    overhead_min_ms = (stats['min'] - exposure_s) * 1e3
    overhead_max_ms = (stats['max'] - exposure_s) * 1e3

    sep = "─" * 62
    logging.info(
        "\n"
        "  Detector overhead  exposure=%.2f s  n=%d frames\n"
        "%s\n"
        "  %-24s %10s %10s %10s\n"
        "  %-24s %9.1f ms %9.1f ms %9.1f ms\n"
        "  %-24s %9.3f s  std=%.3f s\n"
        "%s",
        exposure_s, n_frames,
        sep,
        "overhead (mean-exposure)", "mean", "min", "max",
        "", overhead_mean_ms, overhead_min_ms, overhead_max_ms,
        "frame time (mean)", stats['mean'], stats['std'],
        sep,
    )

    assert overhead_mean_ms <= OVERHEAD_BUDGET_S * 1e3, (
        "exposure={}s: накладные расходы {:.0f} мс на кадр превышают бюджет "
        "{:.0f} мс".format(exposure_s, overhead_mean_ms, OVERHEAD_BUDGET_S * 1e3)
    )
    assert overhead_min_ms > -1.0, (
        "exposure={}s: кадр пришёл раньше конца экспозиции ({:.1f} мс) — "
        "похоже, экспозиция применилась не к этому кадру".format(
            exposure_s, overhead_min_ms)
    )
