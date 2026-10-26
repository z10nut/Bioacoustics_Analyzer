import os
import logging
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QFileDialog, QMessageBox, QTabWidget)
from core.audio_worker import AudioAnalysisWorker
from gui.components.file_manager_widget import FileManagerWidget
from gui.components.action_panel_widget import ActionPanelWidget
from gui.components.menu_bar import MenuBar
from gui.waveform_viewer import WaveformViewer
from gui.manual_labeling import ManualLabelingWindow
from gui.feature_extraction_tab import FeatureExtractionTab

logger = logging.getLogger(__name__)

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
        self.menu_bar.action_open_triggered.connect(self.handle_open_files)

        # Central Widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        self.main_layout = QVBoxLayout(central_widget)

        self.tabs = QTabWidget()

        # Analysis Tab
        tab_analysis = QWidget()
        tab_analysis_layout = QVBoxLayout(tab_analysis)

        middle_layout = QHBoxLayout()
        self.file_manager_widget = FileManagerWidget()
        self.action_panel_widget = ActionPanelWidget()

        middle_layout.addWidget(self.file_manager_widget, stretch=2)
        middle_layout.addWidget(self.action_panel_widget, stretch=1)
        tab_analysis_layout.addLayout(middle_layout)

        # Analysis Tab Buttons
        self.action_panel_widget.btn_run_analysis.clicked.connect(self.handle_run_analysis)
        self.action_panel_widget.btn_view_edit.clicked.connect(self.on_view_waveform_clicked)
        self.action_panel_widget.btn_manual_labeling.clicked.connect(self.open_manual_labeling)

        # Feature Extraction Tab
        self.feature_extraction_tab = FeatureExtractionTab()

        self.tabs.addTab(tab_analysis, "Audio Processing")
        self.tabs.addTab(self.feature_extraction_tab, "Feature Extraction")

        self.main_layout.addWidget(self.tabs)

    def handle_open_files(self):
        """Open a file dialog to select audio files and add them to the file manager."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open File",
            "",
            "Audio Files (*.wav *.mp3);;All Files (*)"
        )
        if file_path:
            self.file_manager_widget.add_file(file_path)
            logger.info(f"File manually opened and added to the list: {file_path}")
    
    def handle_run_analysis(self):
        """Run analysis on the selected audio file using the selected method."""
        selected_file = self.file_manager_widget.get_selected_file_path()
        if not selected_file:
            logger.warning("No file selected for analysis.")
            QMessageBox.warning(
                self,
                "Warning",
                "No file selected for analysis. Please select a file from the list."
            )
            return

        selected_model = self.action_panel_widget.get_selected_model()
        if not selected_model:
            logger.warning("No model selected for analysis.")
            QMessageBox.warning(
                self,
                "Warning",
                "No model selected for analysis. Please select a model from the dropdown."
            )
            return

        output_dir = QFileDialog.getExistingDirectory(self, "Choose Output Directory")
        if not output_dir:
            logger.warning("No output directory selected for analysis.")
            return

        self.action_panel_widget.btn_run_analysis.setEnabled(False)
        logger.info(f"Starting analysis on {selected_file} using model {selected_model}. Output will be saved to {output_dir}.")

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
        """Handle the completion of the analysis."""
        self.action_panel_widget.btn_run_analysis.setEnabled(True)
        self.action_panel_widget.progress_bar.setValue(100)
        self.statusBar().showMessage("Analysis completed successfully.")
        logger.info(f"Analysis completed successfully. Output saved to: {output_path}")
        QMessageBox.information(
            self,
            "Analysis Complete",
            f"Analysis completed successfully. Output saved to:\n{output_path}"
        )
    
    def analysis_error(self, error_message):
        """Handle errors that occur during the analysis process."""
        self.action_panel_widget.btn_run_analysis.setEnabled(True)
        self.action_panel_widget.progress_bar.setValue(0)
        self.statusBar().showMessage("Analysis failed.")
        logger.error(f"Analysis failed with error: {error_message}")
        QMessageBox.critical(
            self,
            "Analysis Error",
            f"An error occurred during analysis:\n{error_message}"
        )
    
    def on_view_waveform_clicked(self):
        """Open the waveform viewer for the selected audio file."""
        selected_audio_path = self.file_manager_widget.get_selected_file_path()
        if not selected_audio_path:
            logger.warning("No audio file selected for waveform viewing.")
            QMessageBox.warning(
                self,
                "Warning",
                "No audio file selected. Please select a file from the list."
            )
            return
        
        self.waveform_viewer = WaveformViewer(selected_audio_path)
        self.waveform_viewer.show()
        logger.info(f"Waveform viewer opened for file: {selected_audio_path}")

    def open_manual_labeling(self):
        """Open the manual labeling window for the selected audio file."""
        base_dir = QFileDialog.getExistingDirectory(self, "Select Base Directory for Manual Labeling")
        if base_dir:
            self.qc_window = ManualLabelingWindow(base_dir)
            self.qc_window.show()
            logger.info(f"Manual labeling window opened with base directory: {base_dir}")
        else:
            logger.warning("No base directory selected for manual labeling.")