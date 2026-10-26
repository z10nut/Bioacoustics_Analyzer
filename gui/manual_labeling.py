import os
import logging
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QProgressBar, QCheckBox)
from PyQt6.QtGui import QShortcut, QKeySequence
from PyQt6.QtCore import Qt
from core.qc_manager import QCActionManager
from gui.components.audio_plot_widget import AudioPlotWidget

logger = logging.getLogger(__name__)

class ManualLabelingWindow(QMainWindow):
    def __init__(self, base_dir):
        super().__init__()
        self.base_dir = base_dir

        self.qc_manager = QCActionManager(base_dir)

        self.playlist = []
        self.current_filepath = None
        self.total_files = 0

        self.setup_ui()
        self.setup_shortcuts()
        self.build_playlist()
        self.load_next_file()

    def setup_ui(self):
        """Sets up the layout, buttons and other UI components."""
        self.setWindowTitle("Manual Labeling Tool")
        self.resize(1000, 800)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # Info Label
        self.lbl_info = QLabel("Loading...")
        self.lbl_info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_info.setStyleSheet("font-size: 16px; font-weight: bold; margin: 5px;")
        layout.addWidget(self.lbl_info)

        # Progress Bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(10)
        layout.addWidget(self.progress_bar)

        # Buttons Layout
        btn_layout = QHBoxLayout()
        self.btn_lfc = QPushButton("LFC")
        self.btn_hfc = QPushButton("HFC")
        self.btn_noise = QPushButton("Noise")
        self.btn_undo = QPushButton("Undo")
        self.btn_redo = QPushButton("Redo")

        for btn in [self.btn_lfc, self.btn_hfc, self.btn_noise, self.btn_undo, self.btn_redo]:
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setMinimumHeight(40)
            btn_layout.addWidget(btn)

        self.btn_lfc.clicked.connect(lambda: self.classify_current("LFC"))
        self.btn_hfc.clicked.connect(lambda: self.classify_current("HFC"))
        self.btn_noise.clicked.connect(lambda: self.classify_current("Noise"))
        self.btn_undo.clicked.connect(self.trigger_undo)
        self.btn_redo.clicked.connect(self.trigger_redo)

        # Autoplay Checkbox
        self.chk_autoplay = QCheckBox("Autoplay")
        self.chk_autoplay.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_layout.addWidget(self.chk_autoplay)
        layout.addLayout(btn_layout)

        self.audio_widget = AudioPlotWidget()
        layout.addWidget(self.audio_widget)

    def setup_shortcuts(self):
        """Maps keyboard shortcuts to their respective actions."""
        QShortcut(QKeySequence(Qt.Key.Key_1), self).activated.connect(lambda: self.classify_current("LFC"))
        QShortcut(QKeySequence(Qt.Key.Key_2), self).activated.connect(lambda: self.classify_current("HFC"))
        QShortcut(QKeySequence(Qt.Key.Key_3), self).activated.connect(lambda: self.classify_current("Noise"))
        QShortcut(QKeySequence("Ctrl+Z"), self).activated.connect(self.trigger_undo)
        QShortcut(QKeySequence("Ctrl+Y"), self).activated.connect(self.trigger_redo)
        QShortcut(QKeySequence(Qt.Key.Key_Space), self).activated.connect(self.audio_widget.play_audio)


    def build_playlist(self):
        """Scans the base directory for audio files and builds a playlist."""
        self.playlist.clear()
        folder_path = os.path.join(self.base_dir, "Detections")

        if os.path.exists(folder_path):
            for f in sorted(os.listdir(folder_path)):
                if f.lower().endswith(".wav"):
                    self.playlist.append(os.path.join(folder_path, f))
            logger.info(f"Playlist built with {len(self.playlist)} audio files from {folder_path}.")
        else:
            logger.warning(f"Detections folder not found in {self.base_dir}. No audio files loaded.")

        self.total_files = len(self.playlist)
        self.progress_bar.setMaximum(max(self.total_files, 1))

    def load_next_file(self):
        """Loads the next audio file in the playlist for labeling."""
        if not self.playlist:
            self.lbl_info.setText("No more files to label")
            self.audio_widget.clear_plots()
            self.current_filepath = None
            self.progress_bar.setValue(self.total_files)
            logger.info("All files have been labeled. Playlist is empty.")
            return

        self.current_filepath = self.playlist.pop(0)

        processed = self.total_files - len(self.playlist) - 1
        self.progress_bar.setValue(processed)

        filename = os.path.basename(self.current_filepath)
        remaining = len(self.playlist)
        self.lbl_info.setText(f"Current File: {filename} | Remaining: {remaining}")

        try:
            self.audio_widget.load_audio(self.current_filepath, audio_levels=False)

            if self.chk_autoplay.isChecked():
                self.audio_widget.play_audio()
        except Exception as e:
            logger.error(f"Error loading audio file {self.current_filepath}: {e}")
            self.load_next_file()

    def classify_current(self, label):
        """Moves the current file to the deired classification folder and loads the next file."""
        if not self.current_filepath:
            logger.warning("No current file to classify.")
            return

        self.audio_widget.stop_audio()
        logger.info(f"Classifying {self.current_filepath} as {label}.")

        self.qc_manager.classify_file(self.current_filepath, label)
        self.load_next_file()

    def trigger_undo(self):
        """Undoes the last classification action."""
        restored_path = self.qc_manager.undo()

        if restored_path:
            self.audio_widget.stop_audio()

            if self.current_filepath and os.path.exists(self.current_filepath):
                self.playlist.insert(0, self.current_filepath)

            self.playlist.insert(0, restored_path)
            self.load_next_file()
            logger.info(f"Undo action performed. Restored file: {restored_path}")

    def trigger_redo(self):
        """Redoes the last undone classification action."""
        redone_path = self.qc_manager.redo()

        if redone_path:
            self.audio_widget.stop_audio()

            if self.current_filepath and os.path.exists(self.current_filepath):
                self.playlist.insert(0, self.current_filepath)

            self.playlist.insert(0, redone_path)
            self.load_next_file()
            logger.info(f"Redo action performed. Redone file: {redone_path}")

    def closeEvent(self, event):
        """Handles the window close event to ensure proper cleanup."""
        self.audio_widget.stop_audio()
        logger.info("Manual Labeling Window closed.")
        super().closeEvent(event)