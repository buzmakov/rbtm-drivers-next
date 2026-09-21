"""Общий файловый логгер для обоих процессов (Flask и tomograph_server).

Создаёт ``logs/log_<timestamp><suffix>`` при первом импорте модуля-обёртки
(``experiment/tomologger.py`` → ``.log``, ``drivers/hwtomologger.py`` → ``.hw.log``)
и пишет туда всё, начиная с уровня TRACE (autologging).
"""
import datetime
import logging
import os

from autologging import TRACE

_FORMAT = "%(asctime)s:%(levelname)s:%(filename)s,%(lineno)d:%(name)s.%(funcName)s:%(message)s"


class TomoLogger:
    def __init__(self, name, suffix, log_dir="logs"):
        self.log_dir = log_dir
        os.makedirs(self.log_dir, exist_ok=True)
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_path = os.path.join(self.log_dir, "log_{}{}".format(timestamp, suffix))

        self.logger = logging.getLogger(name)
        self.logger.setLevel(TRACE)
        formatter = logging.Formatter(_FORMAT)
        for handler in (logging.FileHandler(self.log_path), logging.StreamHandler()):
            handler.setLevel(TRACE)
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

    def debug(self, message):
        self.logger.debug(message)

    def info(self, message):
        self.logger.info(message)

    def warning(self, message):
        self.logger.warning(message)

    def error(self, message):
        self.logger.error(message)

    def critical(self, message):
        self.logger.critical(message)
