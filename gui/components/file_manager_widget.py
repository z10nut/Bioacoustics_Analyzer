import os
import shutil
import logging
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QListWidget, QListWidgetItem, QPushButton,
                             QInputDialog, QMessageBox, QFileDialog)
from PyQt6.QtGui import QFont
from PyQt6.QtCore import Qt

logger = logging.getLogger(__name__)

class FileManagerWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Files list
        self.label_files = QLabel("Files:")
        self.label_files.setFont(QFont("Arial", 12))
        self.file_list = QListWidget()

        layout.addWidget(self.label_files)
        layout.addWidget(self.file_list)

        # Buttons
        btn_layout = QHBoxLayout()
        self.btn_rename = QPushButton("Rename")
        self.btn_copy = QPushButton("Copy")
        self.btn_remove = QPushButton("Remove")

        self.btn_rename.clicked.connect(self.handle_rename)
        self.btn_copy.clicked.connect(self.handle_copy)
        self.btn_remove.clicked.connect(self.remove_selected_file)

        btn_layout.addWidget(self.btn_rename)
        btn_layout.addWidget(self.btn_copy)
        btn_layout.addWidget(self.btn_remove)

        layout.addLayout(btn_layout)

    def add_file(self, file_path):
        """Add a file to the list."""
        file_name = os.path.basename(file_path)
        next_index = self.file_list.count() + 1
        display_text = f"{next_index}. {file_name}"

        item = QListWidgetItem(display_text)
        item.setData(Qt.ItemDataRole.UserRole, file_path)

        self.file_list.addItem(item)
        logger.info(f"[INFO] File added to the list: {file_path}")

    def remove_selected_file(self):
        """Remove the selected file from the list."""
        current_row = self.file_list.currentRow()
        if current_row != -1:
            item = self.file_list.takeItem(current_row)
            file_path = item.data(Qt.ItemDataRole.UserRole)
            self.update_file_indices()
            logger.info(f"[INFO] File removed from the list: {file_path}")
        else:
            logger.warning("No file selected to remove.")

    def get_selected_file_path(self):
        """Get the file path of the selected item."""
        current_item = self.file_list.currentItem()
        if current_item:
            logger.info(f"[INFO] Selected file path: {current_item.data(Qt.ItemDataRole.UserRole)}")
            return current_item.data(Qt.ItemDataRole.UserRole)
        else:
            logger.warning("Could not get selected file path.")
            return None

    def update_file_indices(self):
        """Update the indices of the files in the list."""
        for index in range(self.file_list.count()):
            item = self.file_list.item(index)
            file_path = item.data(Qt.ItemDataRole.UserRole)
            file_name = os.path.basename(file_path)
            item.setText(f"{index + 1}. {file_name}")
            logger.info(f"[INFO] Updated file index: {index + 1}. {file_name}")

    def handle_rename(self):
        """Handle the renaming of the selected file."""
        selected_file = self.get_selected_file_path()
        if not selected_file:
            QMessageBox.warning(self, "Rename", "No file selected to rename.")
            logger.warning("No file selected to rename.")
            return

        directory = os.path.dirname(selected_file)
        old_name = os.path.basename(selected_file)

        new_name, ok = QInputDialog.getText(
            self,
            "Rename File",
            f"Enter new name for {old_name}:",
            text=old_name
        )

        if ok and new_name and new_name != old_name:
            new_file_path = os.path.join(directory, new_name)
            if os.path.exists(new_file_path):
                QMessageBox.critical(
                    self,
                    "Error",
                    f"A file named '{new_name}' already exists in the directory."
                )
                logger.error(f"[ERROR] Rename failed: '{new_name}' already exists.")
                return
            try:
                os.rename(selected_file, new_file_path)
                current_item = self.file_list.currentItem()
                current_item.setData(Qt.ItemDataRole.UserRole, new_file_path)
                self.update_file_indices()
                logger.info(f"[INFO] File renamed from '{old_name}' to '{new_name}'.")
            except Exception as e:
                logger.exception(f"[ERROR] Failed to rename file '{old_name}' to '{new_name}': {e}")
                QMessageBox.critical(
                    self,
                    "Error",
                    f"Failed to rename file: {e}"
                )

    def handle_copy(self):
        """Handle copying the selected file to a new location."""
        selected_file = self.get_selected_file_path()
        if not selected_file:
            QMessageBox.warning(
                self,
                "Copy",
                "No file selected to copy."
            )
            logger.warning("No file selected to copy.")
            return

        directory = os.path.dirname(selected_file)
        base_name = os.path.splitext(os.path.basename(selected_file))
        default_new_name = os.path.join(directory, f"{base_name}_copy{base_name[1]}")

        destination_path, _ = QFileDialog.getSaveFileName(
            self,
            "Copy File",
            default_new_name,
            "Audio Files (*.wav *.mp3);;All Files (*)"
        )

        if destination_path:
            try:
                shutil.copyfile(selected_file, destination_path)
                self.add_file(destination_path)
                logger.info(f"File copied from '{selected_file}' to '{destination_path}'.")
            except Exception as e:
                logger.exception(f"Copy failed: {e}")
                QMessageBox.critical(
                    self,
                    "Error",
                    f"Failed to copy file: {e}"
                )