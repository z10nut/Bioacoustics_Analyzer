import os
import time
import logging
import numpy as np
import soundfile as sf
import sounddevice as sd
import pyqtgraph as pg
from scipy import signal
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QMessageBox)
from PyQt6.QtCore import Qt, QRectF, QTimer, pyqtSignal

logger = logging.getLogger(__name__)

class AudioPlotWidget(QWidget):
    """
        Widget for displaying audio waveform and spectrogram.
    """

    cursor_moved = pyqtSignal(float)  # Signal emitted when the cursor is moved

    def __init__(self, parent=None):
        super().__init__(parent)
        self.audio_data = None
        self.sr = None
        self.duration_sec = 0.0

        # Timer for updating the cursor position while audio is playing
        self.playback_timer = QTimer()
        self.playback_timer.setInterval(30)
        self.playback_timer.timeout.connect(self._update_playback_cursor)

        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.graph_layout = pg.GraphicsLayoutWidget()
        self.graph_layout.ci.layout.setSpacing(0)
        layout.addWidget(self.graph_layout)

        # Waveform Plot
        self.plot_waveform = self.graph_layout.addPlot(row=0, col=0)
        self.plot_waveform.hideAxis('bottom')
        self.plot_waveform.showAxis('left')
        self.plot_waveform.setLabel('left', 'Amplitude')
        self.plot_waveform.getViewBox().setBorder(pg.mkPen('k', width=1))
        self.plot_waveform.getAxis('left').setWidth(60)
        self.plot_waveform.setMouseEnabled(x=False, y=False)
        self.waveform_curve = self.plot_waveform.plot(pen=pg.mkPen('k', width=1.5))

        # Spectrogram Plot
        self.plot_spectrogram = self.graph_layout.addPlot(row=1, col=0)
        self.plot_spectrogram.showAxis('bottom')
        self.plot_spectrogram.showAxis('left')
        self.plot_spectrogram.setLabel('left', 'Frequency (Hz)')
        self.plot_spectrogram.setLabel('bottom', 'Time (s)')
        self.plot_spectrogram.getViewBox().setBorder(pg.mkPen('k', width=1))
        self.plot_spectrogram.getAxis('left').setWidth(60)
        self.plot_spectrogram.setMouseEnabled(x=False, y=False)
        self.plot_spectrogram.setXLink(self.plot_waveform)

        self.img_spectrogram = pg.ImageItem()
        self.plot_spectrogram.addItem(self.img_spectrogram)

        praat_cmap = pg.ColorMap(pos=[0.0, 1.0], color=[(255, 255, 255, 255), (0, 0, 0, 255)])
        self.img_spectrogram.setLookupTable(praat_cmap.getLookupTable())

        # Cursor Line
        self.cursors = []
        for plot in [self.plot_waveform, self.plot_spectrogram]:
            cursor = pg.InfiniteLine(angle=90, movable=False, pen=pg.mkPen('r', width=1.5))
            cursor.setValue(0)
            plot.addItem(cursor)
            self.cursors.append(cursor)
        
        self.graph_layout.scene().sigMouseClicked.connect(self._on_mouse_clicked)
    
    def load_audio(self, filepath, auto_levels=False):
        """Load audio file and render graphs."""
        try:
            self.audio_data, self.sr = sf.read(filepath)

            if len(self.audio_data.shape) > 1:
                self.audio_data = np.mean(self.audio_data, axis=1)

            self.duration_sec = len(self.audio_data) / self.sr

            step = max(1, len(self.audio_data) // 5000)
            waveform_data = self.audio_data[::step]
            time_axis = np.linspace(0, self.duration_sec, len(waveform_data))
            self.waveform_curve.setData(x=time_axis, y=waveform_data)

            f, t, Sxx = signal.spectrogram(
                self.audio_data, fs=self.sr, window='hann',
                nperseg=1024, noverlap=896, nfft=4096
            )

            Sxx_log = 10 * np.log10(Sxx + 1e-10)
            max_val = np.max(Sxx_log)
            Sxx_log = np.clip(Sxx_log, max_val - 60, a_max=max_val)

            self.img_spectrogram.setImage(Sxx_log.T, autoLevels=auto_levels)
            if not auto_levels:
                self.img_spectrogram.setLevels([max_val - 60, max_val])

            self.img_spectrogram.setRect(QRectF(0, 0, self.duration_sec, self.sr / 2))
            self.plot_spectrogram.setYRange(0, min(4000, self.sr / 2))
            logger.info(f"Audio file loaded successfully: {filepath}")

            self.plot_waveform.setXRange(0, self.duration_sec)
            self.set_cursor_position(0.0)

        except Exception as e:
            logger.error(f"Failed to load audio file: {e}")
            raise RuntimeError(f"Failed to load audio file: {e}")

    def clear_plots(self):
        """Clear the waveform and spectrogram plots."""
        self.waveform_curve.setData([], [])
        self.img_spectrogram.clear()
        self.audio_data = None
        self.set_cursor_position(0.0)
        logger.info("Cleared waveform and spectrogram plots.")

    def play_audio(self):
        """Play the loaded audio."""
        if self.audio_data is not None: return

        sd.stop()
        self.playback_timer.stop()

        t_start = self.cursors[0].value()
        if t_start >= self.duration_sec - 0.05:
            t_start = 0.0
            self.set_cursor_position(0.0)

        start_frame = int(t_start * self.sr)
        audio_to_play = self.audio_data[start_frame:]

        if len(audio_to_play) > 0:
            self.audio_start_pos = t_start
            self.playback_start_time = time.time()
            sd.play(audio_to_play, self.sr)
            self.playback_timer.start()
            logger.info("Audio playback started.")
        else:
            logger.warning("No audio data to play from the selected cursor position.")

    def stop_audio(self):
        """Stop audio playback."""
        sd.stop()
        self.playback_timer.stop()
        logger.info("Audio playback stopped.")

    def set_cursor_position(self, x_pos):
        """Set the cursor at the specified x position (in seconds)."""
        x_pos = max(0, min(self.duration_sec, x_pos))
        for cursor in self.cursors:
            cursor.setValue(x_pos)
        self.cursor_moved.emit(x_pos)
        logger.info(f"Cursor moved to position: {x_pos:.2f} seconds.")

    def _on_mouse_clicked(self, event):
        """Handle mouse clicked event and moves the cursor at selected position"""
        if event.button() == Qt.MouseButton.LeftButton and self.audio_data is not None:
            pos = event.scenePos()
            vb = None
            if self.plot_waveform.sceneBoundingRect().contains(pos):
                vb = self.plot_waveform.getViewBox()
            elif self.plot_spectrogram.sceneBoundingRect().contains(pos):
                vb = self.plot_spectrogram.getViewBox()

            if vb:
                mouse_point = vb.mapSceneToView(pos)
                self.set_cursor_position(mouse_point.x())

    def _update_playback_cursor(self):
        """Update the cursor position during audio playback."""
        if self.audio_data is None: return

        elapsed = time.time() - self.playback_start_time
        current_pos = self.audio_start_pos + elapsed

        if current_pos >= self.duration_sec:
            current_pos = self.duration_sec
            self.stop_audio()
        
        for cursor in self.cursors:
            cursor.setValue(current_pos)