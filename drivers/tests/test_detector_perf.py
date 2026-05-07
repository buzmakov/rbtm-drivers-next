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
Результаты логируются через logging.info() и выводятся в консоль при -s.
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


def _capture_legacy(detector: HWDetector, exposure_s: float, n: int) -> list[float]:
    """Capture n frames in legacy mode (start/stop per call). Returns per-frame times."""
    times = []
    for _ in range(n):
        t0 = time.perf_counter()
        detector.get_frames(exposure=exposure_s, number_frames=1)
        times.append(time.perf_counter() - t0)
    return times


def _capture_persistent(detector: HWDetector, exposure_s: float, n: int,
                         use_trigger: bool) -> list[float]:
    """Capture n frames in persistent mode. Returns per-frame times."""
    detector.start_acquisition(exposure=exposure_s, use_trigger=use_trigger)
    try:
        times = []
        for _ in range(n):
            t0 = time.perf_counter()
            detector.get_frames(exposure=exposure_s, number_frames=1)
            times.append(time.perf_counter() - t0)
        return times
    finally:
        detector.stop_acquisition()


def _report(label: str, times: list[float]) -> dict:
    arr = np.array(times)
    result = {
        'mean_s':  float(arr.mean()),
        'min_s':   float(arr.min()),
        'max_s':   float(arr.max()),
        'std_s':   float(arr.std()),
        'total_s': float(arr.sum()),
    }
    logging.info(
        "[%s] n=%d  mean=%.3f s  min=%.3f s  max=%.3f s  std=%.4f s  total=%.3f s",
        label, len(times),
        result['mean_s'], result['min_s'], result['max_s'],
        result['std_s'],  result['total_s'],
    )
    return result


@pytest.mark.parametrize("exposure_s, n_frames", BENCH_PARAMS)
def test_detector_perf_comparison(exposure_s: float, n_frames: int):
    """Compare per-frame timing of legacy vs persistent-trigger acquisition.

    Parametrised exposures: 0.1 s, 1 s, 10 s.

    Checks:
    - Both modes return valid numpy uint16 frames (correctness gate).
    - Persistent trigger mode mean time is not worse than legacy + 10 %
      (loose bound — real hardware should be significantly faster).
    - Overhead (mean - exposure) is logged for manual inspection.
    """
    d = HWDetector()

    # ── correctness sanity check ──────────────────────────────────────
    sample_legacy = d.get_frames(exposure=exposure_s, number_frames=1)
    assert isinstance(sample_legacy, np.ndarray) and sample_legacy.dtype == np.uint16, \
        "Legacy frame must be uint16 ndarray"

    d.start_acquisition(exposure=exposure_s, use_trigger=True)
    sample_trigger = d.get_frames(exposure=exposure_s, number_frames=1)
    d.stop_acquisition()
    assert isinstance(sample_trigger, np.ndarray) and sample_trigger.dtype == np.uint16, \
        "Trigger-mode frame must be uint16 ndarray"

    # ── warm up (discard first frame to avoid cold-start bias) ─────────
    d.get_frames(exposure=exposure_s, number_frames=1)

    # ── legacy benchmark ───────────────────────────────────────────────
    logging.info("=== LEGACY MODE  exposure=%.1f s, n=%d ===", exposure_s, n_frames)
    legacy_times = _capture_legacy(d, exposure_s, n_frames)
    legacy = _report("legacy", legacy_times)

    # ── persistent + software trigger benchmark ────────────────────────
    logging.info("=== PERSISTENT TRIGGER MODE  exposure=%.1f s, n=%d ===", exposure_s, n_frames)
    trig_times = _capture_persistent(d, exposure_s, n_frames, use_trigger=True)
    trig = _report("persistent_trigger", trig_times)

    # ── summary ───────────────────────────────────────────────────────
    overhead_legacy_ms  = (legacy['mean_s'] - exposure_s) * 1e3
    overhead_trigger_ms = (trig['mean_s']   - exposure_s) * 1e3
    speedup = legacy['total_s'] / trig['total_s'] if trig['total_s'] > 0 else 0.0

    logging.info(
        "exposure=%.1f s | overhead legacy=%.1f ms | trigger=%.1f ms "
        "| speedup=%.2fx over %d frames",
        exposure_s, overhead_legacy_ms, overhead_trigger_ms, speedup, n_frames,
    )

    # ── assertion: persistent must not be substantially slower ─────────
    assert trig['mean_s'] <= legacy['mean_s'] * 1.10, (
        f"exposure={exposure_s}s: Persistent trigger mode ({trig['mean_s']:.3f} s) "
        f"is more than 10 % slower than legacy ({legacy['mean_s']:.3f} s) "
        f"— unexpected regression"
    )
