from PyQt6.QtWidgets import QWidget, QHBoxLayout, QPushButton
from PyQt6.QtCore import pyqtSignal

class BottomBar(QWidget):
    rename_clicked = pyqtSignal()
    copy_clicked = pyqtSignal()
    remove_clicked = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setup_ui()

    def setup_ui(self):
        layout = QHBoxLayout()

        self.btn_rename = QPushButton("Rename")
        self.btn_rename.clicked.connect(self.rename_clicked.emit)
        layout.addWidget(self.btn_rename)

        self.btn_copy = QPushButton("Copy")
        self.btn_copy.clicked.connect(self.copy_clicked.emit)
        layout.addWidget(self.btn_copy)

        self.btn_remove = QPushButton("Remove")
        self.btn_remove.clicked.connect(self.remove_clicked.emit)
        layout.addWidget(self.btn_remove)

        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)