import logging
import os
from logging.handlers import RotatingFileHandler

def setup_global_logger():
    """Configure the global logger for the application.
       This directory keeps last 5 log files with a maximum size of 5MB each.
    """
    log_dir = os.path.join(os.getcwd(), "logs")
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "app.log")

    log_format = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | [%(name)s] | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    file_handler = RotatingFileHandler(log_file, maxBytes=5*1024*1024, backupCount=5, encoding='utf-8')
    file_handler.setFormatter(log_format)
    file_handler.setLevel(logging.DEBUG)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(log_format)
    console_handler.setLevel(logging.INFO)

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)

    if not root_logger.handlers:
        root_logger.addHandler(file_handler)
        root_logger.addHandler(console_handler)
    
    logging.getLogger(__name__).info("Global logger configured. Logs will be saved to: %s", log_file)