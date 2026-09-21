"""Оффлайн-тесты hwrpc на фейковом Redis (без железа и без сервера Redis).

Запуск из корня репозитория: ``python -m pytest tests/``.
"""
import threading
import time

import pytest
import redis

import hwrpc
from hwrpc import HardwareClient, HardwareError, HardwareServer, HardwareUnavailable


class FakeRedis:
    """Минимум списочных операций Redis, нужных hwrpc."""

    def __init__(self):
        self._lists = {}
        self._cv = threading.Condition()
        self.expired = {}
        self.fail = False

    def rpush(self, key, value):
        if self.fail:
            raise redis.exceptions.ConnectionError('fake down')
        with self._cv:
            self._lists.setdefault(key, []).append(value)
            self._cv.notify_all()

    def blpop(self, key, timeout=0):
        if self.fail:
            raise redis.exceptions.ConnectionError('fake down')
        deadline = time.monotonic() + timeout
        with self._cv:
            while not self._lists.get(key):
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    return None
                self._cv.wait(min(remaining, 0.05))
            return key, self._lists[key].pop(0)

    def expire(self, key, ttl):
        self.expired[key] = ttl

    def pipeline(self):
        fake = self

        class Pipe:
            def __init__(self):
                self.ops = []

            def rpush(self, *a):
                self.ops.append(('rpush', a))
                return self

            def expire(self, *a):
                self.ops.append(('expire', a))
                return self

            def execute(self):
                for op, a in self.ops:
                    getattr(fake, op)(*a)

        return Pipe()


class Motor:
    def __init__(self):
        self.position = 0

    def move(self, pos, blocking=True):
        self.position = pos
        return pos


class FakeHardware:
    def __init__(self):
        self.angle_motor = Motor()
        self.mock = True

    def fail(self):
        raise RuntimeError('boom')

    def slow(self, seconds):
        time.sleep(seconds)
        return 'done'


@pytest.fixture
def rpc():
    fake = FakeRedis()
    server = HardwareServer(factory=FakeHardware, redis_client=fake, reinit_interval_s=0.2)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    client = HardwareClient(fake, default_timeout_s=2)
    yield fake, server, client
    server.stop()
    thread.join(timeout=3)


def test_call_method_and_attribute(rpc):
    _, _, client = rpc
    assert client.call('angle_motor.move', 42, blocking=False) == 42
    assert client.call('angle_motor.position') == 42
    assert client.call('mock') is True


def test_error_keeps_type(rpc):
    _, _, client = rpc
    with pytest.raises(HardwareError) as excinfo:
        client.call('fail')
    assert excinfo.value.type_name == 'RuntimeError'
    assert excinfo.value.message == 'boom'
    assert 'boom' in excinfo.value.traceback_text


def test_unknown_method_is_attribute_error(rpc):
    _, _, client = rpc
    with pytest.raises(HardwareError) as excinfo:
        client.call('no_such_thing')
    assert excinfo.value.type_name == 'AttributeError'


def test_status(rpc):
    _, _, client = rpc
    assert client.status() == {'available': True, 'error': None}


def test_timeout_raises_unavailable_and_server_skips_stale_request(rpc):
    fake, server, client = rpc
    with pytest.raises(HardwareUnavailable):
        client.call('slow', 1.5, timeout=0.5)
    # После таймаута ответа не должно появиться (сервер выполнил медленный вызов,
    # а следующий просроченный запрос пропустит). Проверяем пропуск напрямую:
    stale = {'id': 'stale', 'method': 'angle_motor.move', 'args': (7,), 'kwargs': {},
             'expires_at': time.time() - 1}
    import pickle
    server.handle(pickle.dumps(stale))
    assert hwrpc.RESPONSE_KEY.format('stale') not in fake._lists
    time.sleep(1.2)  # дать отработать slow()
    assert client.call('angle_motor.position') == 0  # move(7) не выполнялся


def test_no_server_is_unavailable():
    fake = FakeRedis()
    client = HardwareClient(fake, default_timeout_s=0.3)
    with pytest.raises(HardwareUnavailable):
        client.call('mock')


def test_redis_down_is_unavailable():
    fake = FakeRedis()
    fake.fail = True
    client = HardwareClient(fake, default_timeout_s=0.3)
    with pytest.raises(HardwareUnavailable):
        client.call('mock')


def test_hardware_init_failure_is_reported_and_retried():
    attempts = []

    def factory():
        attempts.append(1)
        if len(attempts) < 2:
            raise OSError('port busy')
        return FakeHardware()

    fake = FakeRedis()
    server = HardwareServer(factory=factory, redis_client=fake, reinit_interval_s=0.2)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    client = HardwareClient(fake, default_timeout_s=2)
    try:
        assert client.status()['available'] is False
        assert 'port busy' in client.status()['error']
        with pytest.raises(HardwareUnavailable):   # в пределах reinit_interval — без повторной попытки
            client.call('mock')
        assert len(attempts) == 1
        time.sleep(0.25)
        assert client.call('mock') is True         # вторая попытка инициализации удалась
        assert client.status() == {'available': True, 'error': None}
    finally:
        server.stop()
        thread.join(timeout=3)


def test_response_key_expires(rpc):
    fake, _, client = rpc
    client.call('mock')
    assert fake.expired and all(ttl == hwrpc.RESPONSE_TTL_S for ttl in fake.expired.values())


def test_make_redis_disables_socket_timeout():
    """redis-py ≥ 8: DEFAULT_SOCKET_TIMEOUT=5 с ломает BLPOP с таймаутом ≥ 5 с."""
    client = hwrpc.make_redis('localhost')
    kwargs = client.connection_pool.connection_kwargs
    assert kwargs['socket_timeout'] is None
    assert kwargs['socket_connect_timeout'] == 5.0
