"""Процесс железа: владеет HWTomograph и обслуживает очередь запросов из Redis.

Запускается в контейнере rbtm-tomograph-server (см. docker-compose.yml).
Любое необработанное исключение завершает процесс с ненулевым кодом — Docker
перезапустит контейнер (restart: unless-stopped), а Flask-сторона получит
HardwareUnavailable и не упадёт.
"""
import logging
import os
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
    from drivers.Detector import Detector

    def on_detector_hang(exc):
        # Поток захвата навсегда остался внутри xiGetImage — процесс уже не
        # спасти. Сбрасываем логи и выходим; Docker перезапустит контейнер,
        # Flask получит HardwareUnavailable и выключит источник/затвор
        # через safe_hardware_shutdown после рестарта сервера.
        log.critical('detector hang: %s — exiting for container restart', exc)
        logging.shutdown()
        os._exit(1)

    Detector.set_on_hang(on_detector_hang)

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
