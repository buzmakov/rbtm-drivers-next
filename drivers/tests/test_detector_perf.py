# pytest --log-cli-level=INFO -s -v test_detector_perf.py
"""
Benchmark: Legacy get_frames() vs Persistent-Trigger get_frames().

Запуск:
    pytest --log-cli-level=INFO -s -v drivers/tests/test_detector_perf.py

Что измеряется
--------------
* Legacy mode — каждый get_frames() вызывает start_acquisition + get_image + stop_acquisition.
* Persistent trigger mode — start_acquisition() один раз, затем N × (set_trigger_software + get_image).

Тест параметризован по временам экспозиции: 0.1, 1, 10 с.
Результаты выводятся в виде таблицы через logging.info().
"""
import logging
import time
import pytest
import numpy as np

from ..Detector.Detector import HWDetector

# ── параметры бенчмарка ────────────────────────────────────────────────
#   (exposure_s, n_frames)
#   n_frames уменьшается для длинных экспозиций чтобы тест не длился часами
BENCH_PARAMS = [
    pytest.param(0.1,  10, id="exp=0.1s_n=10"),
    pytest.param(1.0,   5, id="exp=1.0s_n=5"),
    pytest.param(10.0,  3, id="exp=10.0s_n=3"),
]
# ──────────────────────────────────────────────────────────────────────


@pytest.fixture
def detector():
    """Open HWDetector once per test and guarantee close() on teardown.
    XI_DL_FATAL suppresses xiAPI verbose stdout during benchmark runs.
    """
    d = HWDetector()
    # Suppress xiAPI stdout noise (AllocateBuffers, bandwidth, scheduler warnings).
    # XI_DL_FATAL keeps only fatal errors visible.
    d.cam.set_debug_level("XI_DL_FATAL")
    yield d
    d.close()


def _measure(fn, n: int) -> "dict[str, float]":
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
def test_detector_perf_comparison(detector, exposure_s: float, n_frames: int):
    """Compare per-frame timing of legacy vs persistent-trigger acquisition.

    Parametrised exposures: 0.1 s, 1 s, 10 s.

    Checks:
    - Both modes return valid numpy uint16 frames (correctness gate).
    - Persistent trigger mode mean time is not worse than legacy + 10 %.
    """
    # ── correctness check ─────────────────────────────────────────────
    sample_legacy = detector.get_frames(exposure=exposure_s, number_frames=1)
    assert isinstance(sample_legacy, np.ndarray) and sample_legacy.dtype == np.uint16, \
        "Legacy frame must be uint16 ndarray"

    detector.start_acquisition(exposure=exposure_s, use_trigger=True)
    sample_trigger = detector.get_frames(exposure=exposure_s, number_frames=1)
    detector.stop_acquisition()
    assert isinstance(sample_trigger, np.ndarray) and sample_trigger.dtype == np.uint16, \
        "Trigger-mode frame must be uint16 ndarray"

    # ── warm-up (discard cold-start frame) ───────────────────────────
    detector.get_frames(exposure=exposure_s, number_frames=1)

    # ── legacy benchmark ──────────────────────────────────────────────
    legacy = _measure(
        lambda: detector.get_frames(exposure=exposure_s, number_frames=1),
        n_frames,
    )

    # ── persistent trigger benchmark ──────────────────────────────────
    detector.start_acquisition(exposure=exposure_s, use_trigger=True)
    try:
        trig = _measure(
            lambda: detector.get_frames(exposure=exposure_s, number_frames=1),
            n_frames,
        )
    finally:
        detector.stop_acquisition()

    # ── results table ─────────────────────────────────────────────────
    overhead_legacy_ms  = (legacy['mean'] - exposure_s) * 1e3
    overhead_trigger_ms = (trig['mean']   - exposure_s) * 1e3
    speedup = legacy['total'] / trig['total'] if trig['total'] > 0 else 0.0
    saved_ms = (legacy['total'] - trig['total']) * 1e3

    sep = "─" * 62
    logging.info(
        "\n"
        "  Detector benchmark  exposure=%.2f s  n=%d frames\n"
        "%s\n"
        "  %-24s %8s %8s %8s %8s\n"
        "%s\n"
        "  %-24s %7.3f s %7.3f s %7.3f s %7.1f ms\n"
        "  %-24s %7.3f s %7.3f s %7.3f s %7.1f ms\n"
        "%s\n"
        "  Speedup: %.2fx   Saved: %.0f ms total   "
        "(overhead: legacy=%.0f ms  trigger=%.0f ms per frame)\n"
        "%s",
        exposure_s, n_frames,
        sep,
        "Mode", "mean", "min", "max", "overhead",
        sep,
        "legacy",            legacy['mean'], legacy['min'], legacy['max'], overhead_legacy_ms,
        "persistent+trigger", trig['mean'],  trig['min'],  trig['max'],   overhead_trigger_ms,
        sep,
        speedup, saved_ms, overhead_legacy_ms, overhead_trigger_ms,
        sep,
    )

    # ── assertion ─────────────────────────────────────────────────────
    assert trig['mean'] <= legacy['mean'] * 1.10, (
        f"exposure={exposure_s}s: persistent trigger ({trig['mean']:.3f} s) "
        f"is >10% slower than legacy ({legacy['mean']:.3f} s)"
    )
