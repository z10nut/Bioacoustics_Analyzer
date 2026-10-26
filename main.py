import logging
import sys
from asyncio.log import logger

from core.logger_config import setup_global_logger
setup_global_logger()

from PyQt6.QtWidgets import QApplication
from gui.main_window import MainWindow


logging.basicConfig(level=logging.INFO)

def main():
    app = QApplication(sys.argv)

    try:
        with open("gui/styles/main_styles.qss", "r") as style_file:
            app.setStyleSheet(style_file.read())
    except FileNotFoundError:
        logging.error("Stylesheet file not found. Continuing without custom styles.")

    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()