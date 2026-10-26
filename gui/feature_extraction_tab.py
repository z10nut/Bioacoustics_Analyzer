import os
import logging
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
    QComboBox, QFileDialog, QProgressBar, QMessageBox, QGroupBox, QFormLayout
)
from PyQt6.QtCore import Qt
from core.feature_extraction_worker import FeatureExtractionWorker # Asigură-te că importul corespunde structurii tale

logger = logging.getLogger(__name__)

class FeatureExtractionTab(QWidget):
    def __init__(self):
        super().__init__()
        self.selected_dir = None
        self.worker = None
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)

        # Extraction Settings Group
        settings_group = QGroupBox("Acoustic Feature Extraction Settings")
        form_layout = QFormLayout()

        # Select Directory Row
        dir_layout = QHBoxLayout()
        self.lbl_dir = QLabel("No directory selected")
        self.lbl_dir.setStyleSheet("color: gray; font-style: italic;")
        
        self.btn_browse = QPushButton("Browse...")
        self.btn_browse.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_browse.clicked.connect(self.browse_directory)
        
        dir_layout.addWidget(self.lbl_dir, stretch=1)
        dir_layout.addWidget(self.btn_browse)
        form_layout.addRow("Input Folder:", dir_layout)

        # Animal Type Dropdown
        self.combo_animal = QComboBox()
        self.combo_animal.addItems(["cow", "calf"])
        self.combo_animal.setCursor(Qt.CursorShape.PointingHandCursor)

        self.combo_animal.currentTextChanged.connect(self.on_animal_changed)
        form_layout.addRow("Animal Type:", self.combo_animal)

        # Call Type Dropdown
        self.combo_call = QComboBox()
        self.combo_call.addItems(["LFC", "HFC"])
        self.combo_call.setCursor(Qt.CursorShape.PointingHandCursor)
        form_layout.addRow("Call Type:", self.combo_call)

        settings_group.setLayout(form_layout)
        layout.addWidget(settings_group)

        # Run Extraction Button
        self.btn_start = QPushButton("Run Extraction")
        self.btn_start.setMinimumHeight(40)
        self.btn_start.setStyleSheet("font-weight: bold;")
        self.btn_start.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_start.clicked.connect(self.start_extraction)
        layout.addWidget(self.btn_start)

        # Status and Progress Bar
        self.lbl_status = QLabel("Ready.")
        self.lbl_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_status.setStyleSheet("margin-top: 10px;")
        layout.addWidget(self.lbl_status)

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

        layout.addStretch()

    def browse_directory(self):
        """Opens a dialog to select the input directory containing audio files."""
        folder = QFileDialog.getExistingDirectory(
            self, 
            "Select Directory with Audio Files",
            ""
        )
        if folder:
            self.selected_dir = folder
            self.lbl_dir.setText(folder)
            self.lbl_dir.setStyleSheet("color: black; font-weight: normal;")
            logger.info(f"User selected directory for feature extraction: {folder}")

    def on_animal_changed(self, text):
        """Disables the call type dropdown if 'calf' is selected, as calves only have one call type."""
        if text == "calf":
            self.combo_call.setEnabled(False)
            logger.debug("Animal changed to 'calf', call type selection disabled.")
        else:
            self.combo_call.setEnabled(True)
            logger.debug("Animal changed to 'cow', call type selection enabled.")

    def start_extraction(self):
        """Configures the output path and starts the extraction worker thread."""
        if not self.selected_dir or not os.path.isdir(self.selected_dir):
            logger.warning("Attempted to start extraction without a valid input directory.")
            QMessageBox.warning(self, "Warning", "Please select a valid input directory first.")
            return

        # Automatically build the save path inside the selected directory
        output_csv = os.path.join(self.selected_dir, "acoustic_features.csv")
        animal = self.combo_animal.currentText()
        call_type = self.combo_call.currentText()

        # Lock the UI elements to prevent further interaction during processing
        self.btn_start.setEnabled(False)
        self.btn_browse.setEnabled(False)
        self.progress_bar.setValue(0)
        
        # Instantiate and connect the Worker
        self.worker = FeatureExtractionWorker(
            input_dir=self.selected_dir,
            output_csv=output_csv,
            animal_type=animal,
            call_type=call_type
        )

        self.worker.progress.connect(self.update_progress)
        self.worker.finished.connect(self.on_finished)
        self.worker.error.connect(self.on_error)

        self.worker.start()

    def update_progress(self, pct, msg):
        self.progress_bar.setValue(pct)
        self.lbl_status.setText(msg)

    def on_finished(self, output_path):
        """Handles the successful completion of the feature extraction process."""
        self.btn_start.setEnabled(True)
        self.btn_browse.setEnabled(True)
        self.progress_bar.setValue(100)
        self.lbl_status.setText("Extraction Complete.")

        logger.info(f"Feature extraction completed successfully. Results saved to: {output_path}")
        
        QMessageBox.information(
            self, 
            "Success", 
            f"Feature extraction finished successfully!\n\nResults saved to:\n{output_path}"
        )

    def on_error(self, error_msg):
        """Handles errors that occur during the feature extraction process."""
        self.btn_start.setEnabled(True)
        self.btn_browse.setEnabled(True)
        self.lbl_status.setText("Extraction Failed.")

        logger.error(f"Feature extraction failed with error: {error_msg}")
        QMessageBox.critical(self, "Error", error_msg)