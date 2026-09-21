"""Процесс железа: владеет HWTomograph и обслуживает очередь запросов из Redis.

Запускается в контейнере rbtm-tomograph-server (см. docker-compose.yml).
Любое необработанное исключение завершает процесс с ненулевым кодом — Docker
перезапустит контейнер (restart: unless-stopped), а Flask-сторона получит
HardwareUnavailable и не упадёт.
"""
import logging
import sys

import redis

from hwrpc import HardwareServer, configure_logging

REDIS_HOST = 'redis'   # имя сервиса из docker-compose
REDIS_PORT = 6379


def main():
    configure_logging('server')
    log = logging.getLogger('tomograph_server')

    # Импорт после настройки логирования: драйверы пишут в корневой логгер при импорте.
    from drivers.Tomograph.Tomograph import HWTomograph

    server = HardwareServer(factory=HWTomograph,
                            redis_client=redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0))
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        log.info('interrupted, shutting down')
    except Exception:
        log.exception('hardware server crashed')
        sys.exit(1)


if __name__ == '__main__':
    main()
