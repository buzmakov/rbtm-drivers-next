"""RPC между Flask-процессом и процессом железа (``tomograph_server.py``) через Redis.

Зачем отдельный процесс: xiAPI (детектор XIMEA) умеет ронять процесс segfault'ом,
и Flask должен это переживать. Redis здесь только транспорт: очередь запросов
и ключ-ответ на каждый запрос; он переживает рестарт любой из сторон.

Протокол (pickle):

    запрос  : {'id': str, 'method': 'source.off_high_voltage', 'args': tuple,
               'kwargs': dict, 'expires_at': float}
    ответ   : {'result': obj}  либо  {'error': {'type': str, 'message': str,
               'traceback': str}}

Сервер владеет ровно одним объектом железа (``HWTomograph``), создаёт его сам
и пересоздаёт, если инициализация не удалась. Клиент ничего не создаёт и не
хранит: только ``call('a.b.c', *args, timeout=...)``. Ошибка на сервере
приходит клиенту как :class:`HardwareError` с сохранённым именем типа;
таймаут/отсутствие сервера — :class:`HardwareUnavailable`.

Запрос, который клиент уже перестал ждать (``expires_at`` в прошлом), сервер
пропускает — команда не выполнится «потом», когда её никто не ждёт.
"""
import json
import logging
import pickle
import time
import traceback
import uuid

import redis

log = logging.getLogger('hwrpc')

REQUEST_QUEUE = 'hw:requests'
RESPONSE_KEY = 'hw:response:{}'
RESPONSE_TTL_S = 300
DEFAULT_TIMEOUT_S = 15.0

# Служебные методы, которые сервер обрабатывает сам, без объекта железа.
STATUS_METHOD = '__status__'


class HardwareError(Exception):
    """Исключение, поднятое на стороне железа и переданное клиенту."""

    def __init__(self, type_name, message, traceback_text=''):
        super().__init__('{}: {}'.format(type_name, message))
        self.type_name = type_name
        self.message = message
        self.traceback_text = traceback_text


class HardwareUnavailable(HardwareError):
    """Сервер железа не ответил (не запущен, занят дольше таймаута, Redis недоступен)."""

    def __init__(self, message):
        super().__init__('HardwareUnavailable', message)


def configure_logging(process_name, log_dir='logs'):
    """Корневой логгер INFO → консоль + ``logs/hwrpc_<process_name>.log``.

    Драйверы пишут через ``logging.<level>()`` в корневой логгер, поэтому в этом
    файле оказываются и все их сообщения (``HV:1 sent`` и т.п.).
    """
    import os
    os.makedirs(log_dir, exist_ok=True)
    formatter = logging.Formatter('%(asctime)s [{}] [%(levelname)s] %(message)s'.format(process_name))
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    for handler in root.handlers[:]:
        root.removeHandler(handler)
    for handler in (logging.StreamHandler(),
                    logging.FileHandler(os.path.join(log_dir, 'hwrpc_{}.log'.format(process_name)))):
        handler.setFormatter(formatter)
        root.addHandler(handler)


def _short(obj, limit=100):
    text = repr(obj)
    return text if len(text) <= limit else text[:limit] + '...'


# ----------------------------------------------------------------------
# Сервер
# ----------------------------------------------------------------------

class HardwareServer:
    """Однопоточный обработчик очереди запросов к объекту железа."""

    def __init__(self, factory, redis_client, reinit_interval_s=30.0):
        """
        Args:
            factory: функция без аргументов, создающая объект железа (``HWTomograph``).
            redis_client: ``redis.Redis``.
            reinit_interval_s: не пытаться пересоздать объект чаще, чем раз в столько секунд.
        """
        self._factory = factory
        self._redis = redis_client
        self._reinit_interval_s = reinit_interval_s
        self._target = None
        self._target_error = None
        self._last_init_attempt = 0.0
        self.running = False

    # -- объект железа ---------------------------------------------------

    def _ensure_target(self):
        if self._target is not None:
            return self._target
        now = time.monotonic()
        if now - self._last_init_attempt < self._reinit_interval_s:
            raise HardwareUnavailable('hardware init failed: {}'.format(self._target_error))
        self._last_init_attempt = now
        try:
            log.info('creating hardware object...')
            self._target = self._factory()
            self._target_error = None
            log.info('hardware object ready')
        except Exception as e:
            self._target_error = '{}: {}'.format(type(e).__name__, e)
            log.error('hardware init failed: %s', self._target_error)
            log.debug(traceback.format_exc())
            raise HardwareUnavailable('hardware init failed: {}'.format(self._target_error))
        return self._target

    def status(self):
        return {'available': self._target is not None, 'error': self._target_error}

    # -- обработка --------------------------------------------------------

    @staticmethod
    def _resolve(target, dotted):
        obj = target
        for part in dotted.split('.'):
            obj = getattr(obj, part)
        return obj

    def _execute(self, request):
        method = request['method']
        if method == STATUS_METHOD:
            return self.status()
        target = self._ensure_target()
        attr = self._resolve(target, method)
        if callable(attr):
            return attr(*request.get('args', ()), **request.get('kwargs', {}))
        return attr

    def handle(self, raw_request):
        try:
            request = pickle.loads(raw_request)
        except Exception as e:
            log.error('cannot decode request: %s', e)
            return
        request_id = request.get('id')
        method = request.get('method')
        log.info('SERVER RECEIVED: %s', json.dumps(
            {'id': request_id, 'method': method,
             'args': _short(request.get('args')) if request.get('args') else None,
             'kwargs': _short(request.get('kwargs')) if request.get('kwargs') else None},
            ensure_ascii=False))

        expires_at = request.get('expires_at')
        if expires_at is not None and time.time() > expires_at:
            log.warning('SERVER SKIPPED (client gave up %.1f s ago): %s',
                        time.time() - expires_at, method)
            return

        started = time.monotonic()
        try:
            response = {'result': self._execute(request)}
        except Exception as e:
            response = {'error': {'type': type(e).__name__,
                                  'message': str(e),
                                  'traceback': traceback.format_exc()}}
            log.error('SERVER ERROR in %s: %s: %s', method, type(e).__name__, e)

        log.info('SERVER SENT: %s', json.dumps(
            {'id': request_id, 'method': method,
             'success': 'error' not in response,
             'error': response.get('error', {}).get('type'),
             'elapsed_s': round(time.monotonic() - started, 3)},
            ensure_ascii=False))

        try:
            payload = pickle.dumps(response)
        except Exception as e:
            payload = pickle.dumps({'error': {'type': 'SerializationError',
                                              'message': str(e),
                                              'traceback': traceback.format_exc()}})
        key = RESPONSE_KEY.format(request_id)
        pipe = self._redis.pipeline()
        pipe.rpush(key, payload)
        pipe.expire(key, RESPONSE_TTL_S)
        pipe.execute()

    def serve_once(self, block_s=1):
        item = self._redis.blpop(REQUEST_QUEUE, timeout=block_s)
        if item is None:
            return False
        self.handle(item[1])
        return True

    def serve_forever(self):
        self.running = True
        # Объект железа создаём сразу, чтобы ошибки инициализации были видны в логе при старте.
        try:
            self._ensure_target()
        except HardwareUnavailable:
            pass
        log.info('hardware server ready, waiting for requests')
        while self.running:
            try:
                self.serve_once()
            except redis.exceptions.ConnectionError as e:
                log.error('redis connection error: %s; retrying in 1 s', e)
                time.sleep(1)

    def stop(self):
        self.running = False


# ----------------------------------------------------------------------
# Клиент
# ----------------------------------------------------------------------

class HardwareClient:
    """Вызов методов объекта железа по имени через очередь Redis."""

    def __init__(self, redis_client, default_timeout_s=DEFAULT_TIMEOUT_S):
        self._redis = redis_client
        self._default_timeout_s = default_timeout_s

    def call(self, method, *args, timeout=None, **kwargs):
        """Вызвать ``method`` (точечный путь, например ``'angle_motor.get_position_deg'``).

        Если по пути лежит не callable, возвращается значение атрибута.

        Raises:
            HardwareError: исключение на стороне железа (``type_name`` — его класс).
            HardwareUnavailable: нет ответа за ``timeout`` секунд или Redis недоступен.
        """
        timeout = self._default_timeout_s if timeout is None else float(timeout)
        request_id = uuid.uuid4().hex
        request = {'id': request_id, 'method': method, 'args': args, 'kwargs': kwargs,
                   'expires_at': time.time() + timeout}
        log.info('CLIENT SENT: %s', json.dumps(
            {'id': request_id, 'method': method,
             'args': _short(args) if args else None,
             'kwargs': _short(kwargs) if kwargs else None,
             'timeout_s': timeout}, ensure_ascii=False))
        key = RESPONSE_KEY.format(request_id)
        try:
            self._redis.rpush(REQUEST_QUEUE, pickle.dumps(request))
            # blpop принимает только целые секунды
            item = self._redis.blpop(key, timeout=max(1, int(timeout + 0.999)))
        except redis.exceptions.ConnectionError as e:
            raise HardwareUnavailable('redis: {}'.format(e))
        if item is None:
            log.error('CLIENT TIMEOUT after %.1f s: %s', timeout, method)
            raise HardwareUnavailable('no answer from hardware server in {:.0f} s ({})'.format(timeout, method))

        response = pickle.loads(item[1])
        error = response.get('error')
        log.info('CLIENT RECEIVED: %s', json.dumps(
            {'id': request_id, 'method': method, 'success': error is None,
             'error': error['type'] if error else None}, ensure_ascii=False))
        if error:
            log.error('hardware error in %s: %s: %s\n%s', method, error['type'],
                      error['message'], error.get('traceback', ''))
            if error['type'] == 'HardwareUnavailable':
                raise HardwareUnavailable(error['message'])
            raise HardwareError(error['type'], error['message'], error.get('traceback', ''))
        return response.get('result')

    def status(self, timeout=3.0):
        """Состояние сервера: ``{'available': bool, 'error': str|None}``; HardwareUnavailable, если сервер не отвечает."""
        return self.call(STATUS_METHOD, timeout=timeout)
