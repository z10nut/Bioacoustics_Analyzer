from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QFileDialog,
                             QInputDialog, QMessageBox, QPushButton)
from PyQt6.QtCore import Qt
from core.audio_worker import AudioAnalysisWorker
from gui.components.file_list import FileListWidget
from gui.components.action_panel import ActionPanelWidget
from gui.components.menu_bar import MenuBar
from gui.components.bottom_bar import BottomBar
from gui.waveform_viewer import WaveformViewer
from gui.manual_labeling import ManualLabelingWindow
import logging
import os
import shutil

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Bioacoustics Analyzer")
        self.resize(1000, 800)

        self.setup_ui()

    def setup_ui(self):
        # Menu Bar
        self.menu_bar = MenuBar()
        self.setMenuBar(self.menu_bar)

        self.menu_bar.action_exit_triggered.connect(self.close)
        self.menu_bar.action_open_triggered.connect(self.handle_open_file)

        # Central Widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        self.main_layout = QVBoxLayout()
        central_widget.setLayout(self.main_layout)

        # Middle Layout
        middle_layout = QHBoxLayout()

        self.file_list_widget = FileListWidget()
        self.action_panel_widget = ActionPanelWidget()

        middle_layout.addWidget(self.file_list_widget, stretch=2)
        middle_layout.addWidget(self.action_panel_widget, stretch=1)

        self.main_layout.addLayout(middle_layout)

        self.action_panel_widget.btn_run_analysis.clicked.connect(self.handle_run_analysis)
        self.action_panel_widget.btn_view_edit.clicked.connect(self.on_view_waveform_clicked)
        self.action_panel_widget.btn_manual_labeling.clicked.connect(self.open_manual_labeling)

        # Bottom Layout
        self.bottom_bar_widget = BottomBar()
        self.main_layout.addWidget(self.bottom_bar_widget)

        self.bottom_bar_widget.remove_clicked.connect(self.handle_remove)
        self.bottom_bar_widget.rename_clicked.connect(self.handle_rename)
        self.bottom_bar_widget.copy_clicked.connect(self.handle_copy)

    def handle_open_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open File",
            "",
            "Audio Files (*.wav);;All Files (*)"
        )

        if file_path:
            self.file_list_widget.add_file(file_path)
            logging.info(f"Added {file_path} to the file list.")
        
    def handle_remove(self):
        selected_file = self.file_list_widget.get_selected_file_path()

        if selected_file:
            self.file_list_widget.remove_selected_file()
            logging.info(f"Removed {selected_file} from the file list.")
        else:
            logging.warning("No file selected to remove.")

    def handle_rename(self):
        selected_file = self.file_list_widget.get_selected_file_path()

        if not selected_file:
            logging.warning("No file selected to rename.")
            QMessageBox.warning(self, "Rename File", "No file selected to rename.")
            return

        directory = os.path.dirname(selected_file)
        old_name = os.path.basename(selected_file)

        new_name, ok = QInputDialog.getText(
            self,
            "Rename File",
            f"Enter new name for {old_name} (including extension):",
            text=old_name
        )

        if ok and new_name and new_name != old_name:
            new_file_path = os.path.join(directory, new_name)

            if os.path.exists(new_file_path):
                QMessageBox.critical(
                    self,
                    "Error",
                    f"A file named {new_name} already exists in the directory."
                )
                logging.error(f"Rename failed: {new_file_path} already exists.")
                return

            try:
                os.rename(selected_file, new_file_path)
                logging.info(f"Renamed {selected_file} to {new_file_path}.")

                self.file_list_widget.update_selected_file_path(new_file_path)

            except Exception as e:
                logging.error(f"Error renaming file: {e}")
                QMessageBox.critical(
                    self,
                    "Error",
                    f"An error occurred while renaming the file: {e}"
                )

    def handle_copy(self):
        """Copies the selected file to a new location."""

        selected_file = self.file_list_widget.get_selected_file_path()

        if not selected_file:
            logging.warning("No file selected to copy.")
            QMessageBox.warning(self, "Warning", "No file selected to copy.")
            return

        directory = os.path.dirname(selected_file)
        base_name, ext = os.path.splitext(os.path.basename(selected_file))
        default_new_name = os.path.join(directory, f"{base_name}_copy{ext}")

        destination_path, _ = QFileDialog.getSaveFileName(
            self,
            "Copy File",
            default_new_name,
            "Audio Files (*.wav);;All Files (*)"
        )

        if destination_path:
            try:
                shutil.copyfile(selected_file, destination_path)
                logging.info(f"Copied {selected_file} to {destination_path}.")

                self.file_list_widget.add_file(destination_path)

                QMessageBox.information(
                    self,
                    "Success",
                    f"File copied to {destination_path}."
                )

            except Exception as e:
                logging.error(f"Error copying file: {e}")
                QMessageBox.critical(
                    self,
                    "Error",
                    f"An error occurred while copying the file: {e}"
                )

    def handle_run_analysis(self):
        selected_file = self.file_list_widget.get_selected_file_path()
        if not selected_file:
            logging.warning("No file selected for analysis.")
            QMessageBox.warning(self, "Warning", "No file selected for analysis.")
            return

        selected_model = self.action_panel_widget.get_selected_model()
        if not selected_model:
            logging.warning("No model selected for analysis.")
            QMessageBox.warning(self, "Warning", "No model selected for analysis.")
            return

        output_dir = QFileDialog.getExistingDirectory(self, "Choose Output Directory")
        if not output_dir:
            logging.warning("No output directory selected for analysis.")
            QMessageBox.warning(self, "Warning", "No output directory selected for analysis.")
            return

        self.action_panel_widget.btn_run_analysis.setEnabled(False)

        logging.info(f"Running analysis on {selected_file} using {selected_model}.")
        QMessageBox.information(
            self,
            "Analysis",
            f"Running analysis on {selected_file} using {selected_model}."
        )

        self.worker = AudioAnalysisWorker(selected_file, selected_model, output_dir)
        self.worker.finished.connect(self.analysis_finished)
        self.worker.error.connect(self.analysis_error)

        self.worker.progress.connect(self.update_progress)
        self.action_panel_widget.progress_bar.setValue(0)

        self.worker.start()

    def update_progress(self, value, message):
        self.action_panel_widget.progress_bar.setValue(value)
        self.statusBar().showMessage(message)

    def analysis_finished(self, output_path):
        self.action_panel_widget.btn_run_analysis.setEnabled(True)
        self.action_panel_widget.progress_bar.setValue(100)
        self.statusBar().showMessage("Analysis completed successfully.")
        logging.info(f"Analysis finished. Results saved to {output_path}.")
        QMessageBox.information(
            self,
            "Analysis Complete",
            f"Analysis finished. Results saved to {output_path}."
        )

    def analysis_error(self, error_message):
        self.action_panel_widget.btn_run_analysis.setEnabled(True)
        self.action_panel_widget.progress_bar.setValue(0)
        self.statusBar().showMessage("Analysis failed.")
        logging.error(f"Analysis error: {error_message}")
        QMessageBox.critical(
            self,
            "Analysis Error",
            f"An error occurred during analysis: {error_message}"
        )

    # Waveform Viewer
    def on_view_waveform_clicked(self):
        selected_audio_path = self.file_list_widget.get_selected_file_path()

        if not selected_audio_path:
            QMessageBox.warning(self, "Warning", "No audio file selected to view.")
            return;

        self.waveform_viewer = WaveformViewer(selected_audio_path)

        self.waveform_viewer.show()

    def open_manual_labeling(self):
        # Cerem folderul de bază unde se află HFC și LFC
        base_dir = QFileDialog.getExistingDirectory(self, "Selectează Folderul Principal (care conține LFC/HFC)")
        
        if base_dir:
            # Salvăm referința ferestrei ca atribut al clasei pentru a nu fi distrusă de Garbage Collector
            self.qc_window = ManualLabelingWindow(base_dir)
            self.qc_window.show()