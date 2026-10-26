from PyQt6.QtWidgets import QMenuBar
from PyQt6.QtGui import QAction
from PyQt6.QtCore import pyqtSignal

class MenuBar(QMenuBar):
    action_open_triggered = pyqtSignal()
    action_save_triggered = pyqtSignal()
    action_exit_triggered = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setup_ui()

    def setup_ui(self):
        file_menu = self.addMenu("File")

        open_action = QAction("Open", self)
        open_action.setShortcut("Ctrl+0")

        open_action.triggered.connect(self.action_open_triggered.emit)
        file_menu.addAction(open_action)

        file_menu.addSeparator()

        exit_action = QAction("Exit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.action_exit_triggered.emit)
        file_menu.addAction(exit_action)

        save_menu = self.addMenu("Save")

        save_action = QAction("Save", self)
        save_action.setShortcut("Ctrl+S")
        save_action.triggered.connect(self.action_save_triggered.emit)
        save_menu.addAction(save_action)

        help_menu = self.addMenu("Help")

        about_action = QAction("About", self)
        help_menu.addAction(about_action)