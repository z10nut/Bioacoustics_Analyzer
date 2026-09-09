import os
import numpy as np
import soundfile as sf
import sounddevice as sd
import pyqtgraph as pg
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QShortcut, QKeySequence
from core.qc_manager import QCActionManager

class ManualLabelingWindow(QMainWindow):
    def __init__(self, base_dir):
        super().__init__()
        self.base_dir = base_dir
        self.qc_manager = QCActionManager(base_dir)

        self.playlist = []
        self.current_filepath = None
        self.audio_data = None
        self.sr = None

        self.setup_ui()
        self.setup_shortcuts()
        self.build_playlist()
        self.load_next_file()

    def setup_ui(self):
        self.setWindowTitle("Manual Labeling Tool")
        self.resize(1000, 800)

        pg.setConfigOption("background", "w")
        pg.setConfigOption("foreground", "k")

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        self.lbl_info = QLabel("Loading...")
        self.lbl_info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_info.setStyleSheet("font-size: 16px; font-weight: bold; margin: 10px;")
        layout.addWidget(self.lbl_info)

        btn_layout = QHBoxLayout()
        self.btn_lfc = QPushButton("LFC")
        self.btn_hfc = QPushButton("HFC")
        self.btn_noise = QPushButton("Noise (Trash)")
        self.btn_undo = QPushButton("Undo")
        self.btn_redo = QPushButton("Redo")

        for btn in [self.btn_lfc, self.btn_hfc, self.btn_noise, self.btn_undo, self.btn_redo]:
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setMinimumHeight(40)

        self.btn_lfc.clicked.connect(lambda: self.classify_current("LFC"))
        self.btn_hfc.clicked.connect(lambda: self.classify_current("HFC"))
        self.btn_noise.clicked.connect(lambda: self.classify_current("Noise"))
        self.btn_undo.clicked.connect(self.trigger_undo)
        self.btn_redo.clicked.connect(self.trigger_redo)

        btn_layout.addWidget(self.btn_lfc)
        btn_layout.addWidget(self.btn_hfc)
        btn_layout.addWidget(self.btn_noise)
        btn_layout.addWidget(self.btn_undo)
        btn_layout.addWidget(self.btn_redo)

        layout.addLayout(btn_layout)

        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setMouseEnabled(x=False, y=False)
        self.plot_widget.hideAxis('bottom')
        self.plot_widget.hideAxis('left')
        self.waveform_curve = self.plot_widget.plot(pen=pg.mkPen('k', width=1.5))
        layout.addWidget(self.plot_widget)

    def setup_shortcuts(self):
        QShortcut(QKeySequence(Qt.Key.Key_1), self).activated.connect(lambda: self.classify_current("LFC"))
        QShortcut(QKeySequence(Qt.Key.Key_2), self).activated.connect(lambda: self.classify_current("HFC"))
        QShortcut(QKeySequence(Qt.Key.Key_3), self).activated.connect(lambda: self.classify_current("Noise"))
        QShortcut(QKeySequence("Ctrl+Z"), self).activated.connect(self.trigger_undo)
        QShortcut(QKeySequence("Ctrl+Y"), self).activated.connect(self.trigger_redo)

        QShortcut(QKeySequence(Qt.Key.Key_Space), self).activated.connect(self.play_current_audio)

    def build_playlist(self):
        self.playlist.clear()

        for folder in ["HFC", "LFC"]:
            folder_path = os.path.join(self.base_dir, folder)
            if os.path.exists(folder_path):
                for f in sorted(os.listdir(folder_path)):
                    if f.lower().endswith(".wav"):
                        self.playlist.append(os.path.join(folder_path, f))

    def load_next_file(self):
        if not self.playlist:
            self.lbl_info.setText("No more files to label.")
            self.plot_widget.clear()
            self.current_filepath = None
            return
        
        self.current_filepath = self.playlist.pop(0)
        filename = os.path.basename(self.current_filepath)
        remaining = len(self.playlist)
        self.lbl_info.setText(f"Current File: {filename} | Remaining: {remaining}")

        self.load_and_plot_audio()

    def load_and_plot_audio(self):
        try:
            self.audio_data, self.sr = sf.read(self.current_filepath)

            if len(self.audio_data.shape) > 1:
                self.audio_data = np.mean(self.audio_data, axis=1)

            step = max(1, len(self.audio_data) // 5000)
            self.waveform_curve.setData(self.audio_data[::step])

        except Exception as e:
            self.load_next_file()

    def play_current_audio(self):
        if self.audio_data is not None and self.sr is not None:
            sd.stop()
            sd.play(self.audio_data, self.sr)

    def classify_current(self, label):
        if not self.current_filepath:
            return

        sd.stop()
        self.qc_manager.classify_file(self.current_filepath, label)
        self.load_next_file()

    def trigger_undo(self):
        restored_path = self.qc_manager.undo()
        if restored_path:
            sd.stop()
            if self.current_filepath and os.path.exists(self.current_filepath):
                self.playlist.insert(0, self.current_filepath)

            self.playlist.insert(0, restored_path)
            self.load_next_file()
    
    def trigger_redo(self):
        redone_path = self.qc_manager.redo()
        if redone_path:
            sd.stop()
            if self.current_filepath and os.path.exists(self.current_filepath):
                self.playlist.insert(0, self.current_filepath)

            self.playlist.insert(0, redone_path)
            self.load_next_file()
    
    def closeEvent(self, event):
        sd.stop()
        event.accept()