#!/usr/bin/env python3
"""Smoke-проверка задеплоенного rbtm-drivers-next на robotom через HTTP API и логи.

Запускается с любой машины, откуда доступен API (порт 5001) и ssh на хост:

    python tools/verify_robotom.py                      # A–H: без ВН, моторы и затвор двигаются
    python tools/verify_robotom.py --restart-server     # + I: останавливает rbtm-tomograph-server на ~1 мин
    python tools/verify_robotom.py --with-hv            # + J, K: включает ВН (прогрев до 30 мин) и короткий эксперимент

Ничего не импортирует из драйверов — только requests/numpy. Логи читаются по ssh
(read-only), docker stop/start — только с --restart-server.

Что проверяется — см. docs/REVIEW-2026-09-hardware.md §5.
"""
import argparse
import io
import json
import os
import shlex
import subprocess
import sys
import time
import uuid

import numpy as np
import requests

# ---------------------------------------------------------------- параметры

DEFAULT_BASE = 'http://robotom:5001/tomograph/1'
DEFAULT_SSH = 'ssh -o ConnectTimeout=15 -i ~/.ssh/id_ed25519_mars robotom@robotom'
REMOTE_DIR = '/home/robotom/workspace/xtomo/rbtm-drivers-next'
SERVER_CONTAINER = 'rbtm-tomograph-server'

ANGLE_SMALL_STEP_DEG = 0.5
ANGLE_TOLERANCE_DEG = 0.05
ANGLE_SHORT_PATH_MAX_S = 5.0       # 359.5 → 0 кратчайшим путём; раньше ~65 с
ANGLE_LONG_MOVE_MAX_S = 60.0       # ≤180° при speed=500 ≈ 33 с
PARK_STEPS_EXPECTED = -4200.63     # -21.06 мм × 199.46 шаг/мм; (-4201,+95) и (-4200,-161) дают одно число
PARK_TOLERANCE_STEPS = 1.0
LINEAR_MOVE_MAX_S = 40.0
POLL_S = 0.5

PREVIEW_EXPOSURES_MS = (100.0, 500.0)
HV_VOLTAGE_KV = 40.0
HV_CURRENT_MA = 10.0
HV_READY_MAX_S = 35 * 60
WARMUP_INTERRUPT_AFTER_S = 20
EXPERIMENT = {'advanced': True, 'exposure': 500.0, 'series_length': 2, 'data_total': 3,
              'data_angle_step': 120.0, 'data_count_per_step': 1, 'empty_period': 50}
EXPERIMENT_MAX_S = 10 * 60
UNAVAILABLE_MAX_S = 15
READY_AFTER_START_MAX_S = 120

PASS, FAIL, SKIP = 'PASS', 'FAIL', 'SKIP'


class Check(Exception):
    pass


# ---------------------------------------------------------------- инфраструктура

class Remote:
    def __init__(self, ssh_cmd):
        self.ssh = shlex.split(ssh_cmd)
        self.ssh = [os.path.expanduser(a) if a.startswith('~') else a for a in self.ssh]

    def run(self, command, timeout=60):
        proc = subprocess.run(self.ssh + [command], capture_output=True, text=True, timeout=timeout)
        if proc.returncode != 0 and not proc.stdout:
            raise Check('ssh failed: {}'.format(proc.stderr.strip()[-300:]))
        return proc.stdout

    def count(self, command):
        out = self.run(command + ' 2>/dev/null | wc -l').strip().splitlines()
        return int(out[-1]) if out else 0

    def segfaults(self):
        return int(self.run("journalctl -k --no-pager 2>/dev/null | grep -c segfault || true").strip().splitlines()[-1])

    def restart_count(self):
        return int(self.run("docker inspect {} --format '{{{{.RestartCount}}}}'".format(SERVER_CONTAINER)).strip())

    def server_log_grep(self, pattern):
        return self.count("grep -- {} {}/logs/tomo_server/hwrpc_server.log".format(shlex.quote(pattern), REMOTE_DIR))

    def hw_log_grep(self, pattern):
        """Последний log_*.hw.log сервера железа (TomoLogger детектора пишет туда)."""
        return self.count("grep -- {} \"$(ls -t {}/logs/tomo_server/log_*.hw.log | head -1)\""
                          .format(shlex.quote(pattern), REMOTE_DIR))

    def exp_log_grep(self, pattern):
        return self.count("grep -- {} \"$(ls -t {}/logs/experiment/log_*.log | head -1)\""
                          .format(shlex.quote(pattern), REMOTE_DIR))


class Api:
    def __init__(self, base):
        self.base = base.rstrip('/')
        self.last_content_type = None

    def _check(self, r):
        self.last_content_type = r.headers.get('Content-Type', '')
        return r

    def get(self, path, timeout=30):
        return self._check(requests.get(self.base + path, timeout=timeout))

    def post(self, path, body, timeout=30):
        data = body if isinstance(body, (str, bytes)) else json.dumps(body)
        return self._check(requests.post(self.base + path, data=data, timeout=timeout))

    def result(self, path, method='get', body=None, timeout=30):
        r = self.get(path, timeout) if method == 'get' else self.post(path, body, timeout)
        try:
            payload = r.json()
        except ValueError:
            raise Check('{} {}: not JSON (HTTP {}): {!r}'.format(method.upper(), path, r.status_code, r.text[:120]))
        if not payload.get('success'):
            raise Check('{} {}: HTTP {} {} / {}'.format(method.upper(), path, r.status_code,
                                                        payload.get('error'), payload.get('exception message')))
        return payload['result']

    def angle(self):
        return float(self.result('/motor/get-angle-position'))

    def x(self):
        return float(self.result('/motor/get-horizontal-position'))

    def shutter(self):
        return json.loads(self.result('/shutter/state'))['state']

    def source(self):
        return self.result('/source/state')


def wait_until(predicate, timeout_s, what):
    start = time.monotonic()
    while time.monotonic() - start < timeout_s:
        if predicate():
            return time.monotonic() - start
        time.sleep(POLL_S)
    raise Check('timeout {:.0f} s waiting for {}'.format(timeout_s, what))


def angle_close(a, b, tol=ANGLE_TOLERANCE_DEG):
    d = abs((a - b + 180.0) % 360.0 - 180.0)
    return d <= tol


# ---------------------------------------------------------------- проверки

def check_a_server_up(api, remote):
    state = api.result('/state')
    if state != 'ready':
        raise Check('/state = {}'.format(state))
    ready = remote.server_log_grep('hardware object ready')
    errors = remote.server_log_grep('SERVER ERROR')
    main_log = remote.run('ls {}/logs/experiment/hwrpc_main.log 2>&1'.format(REMOTE_DIR)).strip()
    if ready < 1:
        raise Check('no "hardware object ready" in hwrpc_server.log')
    if 'No such file' in main_log:
        raise Check('hwrpc_main.log missing')
    return 'ready; "hardware object ready" ×{}; SERVER ERROR ×{} (до прогона)'.format(ready, errors)


def check_b_detector_model(api, remote):
    r = api.result('/detector/model')
    if 'MH110XC' not in str(r.get('model')):
        raise Check('model = {!r}'.format(r.get('model')))
    if abs(float(r.get('pixel_size_mm', 0)) - 0.009) > 1e-9:
        raise Check('pixel_size_mm = {!r}, expected 0.009'.format(r.get('pixel_size_mm')))
    return '{} / {} mm'.format(r['model'], r['pixel_size_mm'])


def check_c_source_comm(api, remote):
    s = api.source()
    if s.get('mocked'):
        raise Check('source is mocked')
    if not isinstance(s.get('warming_status'), dict):
        raise Check('warming_status = {!r} (нет связи с генератором?)'.format(s.get('warming_status')))
    v = api.result('/source/get-voltage')
    c = api.result('/source/get-current')
    if not isinstance(v, (int, float)) or not isinstance(c, (int, float)):
        raise Check('voltage/current not numeric: {!r} / {!r}'.format(v, c))
    return 'on={on} busy={busy} warming={warming_status} U={u} kV I={i} mA'.format(u=v, i=c, **s)


def check_d_shutter(api, remote):
    before = api.shutter()
    api.result('/shutter/open/0')
    if api.shutter() != 'OPEN':
        raise Check('after open: {}'.format(api.shutter()))
    api.result('/shutter/close/0')
    if api.shutter() != 'CLOSE':
        raise Check('after close: {}'.format(api.shutter()))
    return 'was {}, OPEN → CLOSE ok'.format(before)


def check_e_angle_shortest_path(api, remote):
    a0 = api.angle()
    if not 0.0 <= a0 < 360.0:
        raise Check('get-angle not normalised: {}'.format(a0))
    target = (a0 + ANGLE_SMALL_STEP_DEG) % 360.0
    api.result('/motor/set-angle-position', 'post', target)
    wait_until(lambda: angle_close(api.angle(), target), 30, 'small step')
    api.result('/motor/set-angle-position', 'post', 359.5)
    t_long = wait_until(lambda: angle_close(api.angle(), 359.5), ANGLE_LONG_MOVE_MAX_S, 'move to 359.5')
    api.result('/motor/set-angle-position', 'post', 0.0)
    t_short = wait_until(lambda: angle_close(api.angle(), 0.0), ANGLE_LONG_MOVE_MAX_S, 'move 359.5 → 0')
    # возвращаем исходное положение
    api.result('/motor/set-angle-position', 'post', a0)
    wait_until(lambda: angle_close(api.angle(), a0), ANGLE_LONG_MOVE_MAX_S, 'return to a0')
    if t_short > ANGLE_SHORT_PATH_MAX_S:
        raise Check('359.5 → 0 took {:.1f} s (long way round?)'.format(t_short))
    return 'a0={:.2f}; →359.5 за {:.1f} с; 359.5→0 за {:.1f} с; вернулся'.format(a0, t_long, t_short)


def check_f_parking(api, remote):
    x0 = api.x()
    timeouts_before = remote.server_log_grep('MotorTimeoutError')
    api.result('/motor/move-away', timeout=LINEAR_MOVE_MAX_S + 10)

    def parked():
        return abs(api.x() - PARK_STEPS_EXPECTED) <= PARK_TOLERANCE_STEPS
    wait_until(parked, LINEAR_MOVE_MAX_S, 'move-away')
    parked_at = api.x()
    api.result('/motor/move-back', timeout=LINEAR_MOVE_MAX_S + 10)
    wait_until(lambda: abs(api.x() - 0.0) <= PARK_TOLERANCE_STEPS, LINEAR_MOVE_MAX_S, 'move-back')
    if remote.server_log_grep('MotorTimeoutError') != timeouts_before:
        raise Check('MotorTimeoutError appeared in server log')
    return 'x0={:.2f}; parked at {:.2f} (expected {:.2f}); back at {:.2f}'.format(x0, parked_at, PARK_STEPS_EXPECTED, api.x())


def check_g_detector_preview(api, remote):
    seg0 = remote.segfaults()
    started0 = remote.hw_log_grep('постоянный захват запущен')
    stopped0 = remote.hw_log_grep('постоянный захват остановлен')
    shapes = []
    for exp_ms in PREVIEW_EXPOSURES_MS:
        r = api.post('/detector/get-frame-preview', {'exposure_ms': exp_ms, 'downsample': 4},
                     timeout=exp_ms / 1e3 * 2 + 60)
        if r.status_code != 200 or 'octet-stream' not in api.last_content_type:
            raise Check('preview {} ms: HTTP {} {}'.format(exp_ms, r.status_code, r.text[:200]))
        npz = np.load(io.BytesIO(r.content))
        data = npz['data']
        if data.dtype != np.uint16 or data.size == 0:
            raise Check('preview {} ms: dtype {} shape {}'.format(exp_ms, data.dtype, data.shape))
        shapes.append(data.shape)
    if api.shutter() != 'CLOSE':
        raise Check('shutter not closed after preview: {}'.format(api.shutter()))
    started = remote.hw_log_grep('постоянный захват запущен') - started0
    stopped = remote.hw_log_grep('постоянный захват остановлен') - stopped0
    seg = remote.segfaults() - seg0
    if seg:
        raise Check('segfault count grew by {}'.format(seg))
    if stopped:
        raise Check('acquisition was stopped {} times between previews'.format(stopped))
    if started > 1:
        raise Check('acquisition started {} times (expected lazy start once)'.format(started))
    return 'shapes {}; захват запущен ×{} (лениво), остановлен ×0, segfault +0'.format(shapes, started)


def check_h_http_errors(api, remote):
    r = api.post('/source/set-voltage', 'not json')
    if r.status_code != 400 or 'application/json' not in api.last_content_type:
        raise Check('bad JSON → HTTP {} {}'.format(r.status_code, api.last_content_type))
    r = api.get('/state')
    if 'application/json' not in api.last_content_type:
        raise Check('/state Content-Type = {}'.format(api.last_content_type))
    return '400 + application/json'


def check_i_server_restart(api, remote):
    rc0 = remote.restart_count()
    ready0 = remote.server_log_grep('hardware object ready')
    remote.run('docker stop {}'.format(SERVER_CONTAINER), timeout=90)
    try:
        t_unavail = wait_until(lambda: api.result('/state') == 'unavailable', UNAVAILABLE_MAX_S + 20, '/state unavailable')
        r = api.get('/source/state')
        if r.status_code != 503 or 'application/json' not in api.last_content_type:
            raise Check('/source/state while server down: HTTP {} {}'.format(r.status_code, api.last_content_type))
    finally:
        remote.run('docker start {}'.format(SERVER_CONTAINER), timeout=90)
    t_ready = wait_until(lambda: api.result('/state') == 'ready', READY_AFTER_START_MAX_S, '/state ready after start')
    ready1 = remote.server_log_grep('hardware object ready')
    rc1 = remote.restart_count()
    if ready1 <= ready0:
        raise Check('no new "hardware object ready" after start')
    if rc1 != rc0:
        raise Check('RestartCount changed {} → {}'.format(rc0, rc1))
    return 'unavailable за {:.0f} с (503 JSON), ready через {:.0f} с после старта; RestartCount={}'.format(
        t_unavail, t_ready, rc1)


def check_j_hv_and_warmup(api, remote):
    api.result('/source/set-voltage', 'post', HV_VOLTAGE_KV)
    api.result('/source/set-current', 'post', HV_CURRENT_MA)
    warm0 = remote.server_log_grep('Source.warmup() starting')
    hv0_0 = remote.server_log_grep('HV:0 sent')
    api.result('/source/power-on')
    time.sleep(WARMUP_INTERRUPT_AFTER_S)
    s = api.source()
    interrupted = None
    if s.get('busy') and remote.server_log_grep('Source.warmup() starting') > warm0:
        # Прогрев идёт — проверяем, что off_high_voltage() его прерывает.
        api.result('/source/power-off')
        wait_until(lambda: not api.source().get('busy') and not api.source().get('on'), 60, 'warm-up interrupt')
        if remote.server_log_grep('HV:0 sent') <= hv0_0:
            raise Check('no "HV:0 sent" after power-off during warm-up')
        interrupted = True
        api.result('/source/power-on')
    t = wait_until(lambda: api.source().get('on') and not api.source().get('busy'), HV_READY_MAX_S, 'HV on')
    v = api.result('/source/get-voltage')
    c = api.result('/source/get-current')
    note = 'прогрев прерван power-off и запущен заново; ' if interrupted else 'прогрев не потребовался (прерывание не проверено); '
    return note + 'HV on через {:.0f} с, U={} kV I={} mA'.format(t, v, c)


def check_k_short_experiment(api, remote):
    seg0 = remote.segfaults()
    rc0 = remote.restart_count()
    errors0 = remote.server_log_grep('SERVER ERROR')
    exp_id = 'smoke-{}'.format(uuid.uuid4())
    params = dict(EXPERIMENT)
    params['exp_id'] = exp_id
    r = api.post('/experiment/start', {'exp_id': exp_id, 'experiment parameters': params}, timeout=60)
    payload = r.json()
    if not payload.get('success'):
        raise Check('start: {}'.format(payload))
    total = 2 + 2 + EXPERIMENT['data_total'] * EXPERIMENT['data_count_per_step']

    # Во время съёмки ручное управление должно отвечать 409.
    wait_until(lambda: api.result('/experiment/status').get('running'), 60, 'experiment running')
    r = api.get('/shutter/open/0')
    if r.status_code != 409:
        raise Check('manual shutter during experiment: HTTP {} (expected 409)'.format(r.status_code))

    t = wait_until(lambda: not api.result('/experiment/status').get('running'), EXPERIMENT_MAX_S, 'experiment finish')
    status = api.result('/experiment/status')
    if status.get('frame_num') != total or status.get('total_frames') != total:
        raise Check('frames {}/{} (expected {})'.format(status.get('frame_num'), status.get('total_frames'), total))
    time.sleep(3)  # событие завершения и логи
    shutdown_ok = remote.count("grep -- 'safe_hardware_shutdown: .* done' \"$(ls -t {}/logs/experiment/log_*.log | head -1)\" | tail -3".format(REMOTE_DIR))
    finished = remote.exp_log_grep('Experiment was finished successfully')
    s = api.source()
    if s.get('on'):
        raise Check('HV still on after experiment')
    if api.shutter() != 'CLOSE':
        raise Check('shutter not closed after experiment')
    seg = remote.segfaults() - seg0
    rc = remote.restart_count() - rc0
    errors = remote.server_log_grep('SERVER ERROR') - errors0
    if seg or rc or errors:
        raise Check('segfault +{} restarts +{} SERVER ERROR +{}'.format(seg, rc, errors))
    if shutdown_ok < 3 or finished < 1:
        raise Check('logs: safe_hardware_shutdown done ×{}, finished ×{}'.format(shutdown_ok, finished))
    return '{}: {} кадров за {:.0f} с, 409 на затвор, HV off, затвор CLOSE, segfault/restarts/errors +0'.format(
        exp_id, total, t)


def check_l_not_automatable(api, remote):
    raise Check('SKIP: коды 118/119/121 нельзя вызвать по требованию — покрыто TestSourceOffline')


CHECKS = [
    ('A', 'сервер поднялся', check_a_server_up, None),
    ('B', 'детектор: модель/пиксель', check_b_detector_model, None),
    ('C', 'источник: связь', check_c_source_comm, None),
    ('D', 'затвор open/close', check_d_shutter, None),
    ('E', 'угол: кратчайший путь', check_e_angle_shortest_path, None),
    ('F', 'парковка (микрошаги)', check_f_parking, None),
    ('G', 'детектор: превью, ленивый старт', check_g_detector_preview, None),
    ('H', 'HTTP: ошибки JSON', check_h_http_errors, None),
    ('I', 'рестарт сервера железа', check_i_server_restart, 'restart_server'),
    ('J', 'ВН и прогрев', check_j_hv_and_warmup, 'with_hv'),
    ('K', 'короткий эксперимент', check_k_short_experiment, 'with_hv'),
    ('L', 'коды 118/119/121', check_l_not_automatable, None),
]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--base', default=DEFAULT_BASE)
    ap.add_argument('--ssh', default=DEFAULT_SSH)
    ap.add_argument('--restart-server', action='store_true')
    ap.add_argument('--with-hv', action='store_true')
    ap.add_argument('--only', help='буквы проверок через запятую, например A,C,H')
    args = ap.parse_args()

    api = Api(args.base)
    remote = Remote(args.ssh)
    only = set(args.only.upper().split(',')) if args.only else None
    results = []
    for letter, title, func, flag in CHECKS:
        if only and letter not in only:
            continue
        if flag and not getattr(args, flag):
            results.append((letter, title, SKIP, 'нужен --{}'.format(flag.replace('_', '-'))))
            continue
        print('[{}] {} ...'.format(letter, title), flush=True)
        t0 = time.monotonic()
        try:
            note = func(api, remote)
            verdict = PASS
        except Check as e:
            note = str(e)
            verdict = SKIP if note.startswith('SKIP') else FAIL
        except Exception as e:  # noqa: BLE001 — любая ошибка = FAIL с текстом
            note = '{}: {}'.format(type(e).__name__, e)
            verdict = FAIL
        print('    {} ({:.0f} s): {}'.format(verdict, time.monotonic() - t0, note), flush=True)
        results.append((letter, title, verdict, note))

    print('\n| # | Проверка | Результат | Детали |\n|---|---|---|---|')
    for letter, title, verdict, note in results:
        print('| {} | {} | {} | {} |'.format(letter, title, verdict, note.replace('|', '/')))
    failed = [r for r in results if r[2] == FAIL]
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
