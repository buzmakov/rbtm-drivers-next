import logging
import datetime
import os
from autologging import traced, TRACE


class TomoLogger:
    def __init__(self):
        self.log_dir = "logs"
        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir)

        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        log_filename = f"log_{timestamp}.hw.log"
        self.log_path = os.path.join(self.log_dir, log_filename)

        # Create logger
        self.logger = logging.getLogger('HWTomoLogger')
        self.logger.setLevel(TRACE)

        # Create file handler
        file_handler = logging.FileHandler(self.log_path)
        file_handler.setLevel(TRACE)

        # Create console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(TRACE)

        # Create formatter
        formatter = logging.Formatter(
            "%(asctime)s:%(levelname)s:%(filename)s,%(lineno)d:%(name)s.%(funcName)s:%(message)s")
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)

        # Add handlers to logger
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)

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


tomologger = TomoLogger()
