import os
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QListWidget, QListWidgetItem
from PyQt6.QtGui import QFont

class FileListWidget(QWidget):
    def __init__(self):
        super().__init__()

        self.file_counter = 1
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout()

        self.label_files = QLabel("Files:")
        self.label_files.setFont(QFont("Arial", 12))

        self.file_list = QListWidget()

        layout.addWidget(self.label_files)
        layout.addWidget(self.file_list)

        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

    def add_file(self, file_path):
        """Adds a file to the list."""
        file_name = os.path.basename(file_path)
        display_text = f"{self.file_counter}. {file_name}"

        item = QListWidgetItem(display_text)
        item.setData(256, file_path)

        self.file_list.addItem(item)
        self.file_counter += 1

    def remove_selected_file(self):
        """Removes the selected file from the list."""

        current_row = self.file_list.currentRow()

        if current_row != -1:
            self.file_list.takeItem(current_row)
            self.file_counter -= 1
            self.update_file_numbers()

    def get_selected_file_path(self):
        """Returns the file path of the selected file."""
        current_item = self.file_list.currentItem()

        if current_item:
            return current_item.data(256)
        return None

    def update_file_numbers(self):
        """Updates the IDs of the files in the list after a removal."""
        self.file_counter = 1

        for index in range(self.file_list.count()):
            item = self.file_list.item(index)

            file_path = item.data(256)
            file_name = os.path.basename(file_path)

            display_text = f"{self.file_counter}. {file_name}"
            item.setText(display_text)

            self.file_counter += 1

    def update_selected_file_path(self, new_path):
        """Updates the file path of the selected file."""
        current_item = self.file_list.currentItem()

        if current_item:
            current_item.setData(256, new_path)
            self.update_file_numbers()