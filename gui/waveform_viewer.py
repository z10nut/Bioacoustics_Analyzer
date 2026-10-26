import os
import time
import json
import logging
import numpy as np
import pandas as pd
import soundfile as sf
import sounddevice as sd
from scipy import signal
import pyqtgraph as pg

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
    QInputDialog, QScrollBar, QMessageBox, QFileDialog
)
from PyQt6.QtCore import Qt, QRectF, QTimer
from PyQt6.QtGui import QShortcut, QKeySequence

from gui.components.menu_bar import MenuBar
from gui.components.viewbox_zoom import ViewBox

# Initialize module-level logger
logger = logging.getLogger(__name__)

# SVG icons for the custom scrollbar
SCROLLBAR_LEFT_SVG = "PHN2ZyB4bWxucz0naHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmcnIHdpZHRoPScxMicgaGVpZ2h0PScxMicgdmlld0JveD0nMCAwIDEyIDEyJz48cGF0aCBkPSdNOCAyIEwzIDYgTDggMTAnIHN0cm9rZT0nIzMzMycgc3Ryb2tlLXdpZHRoPScyJyBmaWxsPSdub25lJyBzdHJva2UtbGluZWNhcD0ncm91bmQnIHN0cm9rZS1saW5lam9pbj0ncm91bmQnLz48L3N2Zz4="
SCROLLBAR_RIGHT_SVG = "PHN2ZyB4bWxucz0naHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmcnIHdpZHRoPScxMicgaGVpZ2h0PScxMicgdmlld0JveD0nMCAwIDEyIDEyJz48cGF0aCBkPSdNNCAyIEw5IDYgTDQgMTAnIHN0cm9rZT0nIzMzMycgc3Ryb2tlLXdpZHRoPScyJyBmaWxsPSdub25lJyBzdHJva2UtbGluZWNhcD0ncm91bmQnIHN0cm9rZS1saW5lam9pbj0ncm91bmQnLz48L3N2Zz4="

# ==========================================
# Textgrid Annotation Region
# ==========================================
class AnnotationRegion(pg.LinearRegionItem):
    """
    A custom PyQtGraph LinearRegionItem representing an annotated segment of audio.
    Supports double-clicking to edit the label text.
    """
    def __init__(self, bounds, label_text, parent_plot, main_app=None, **kwargs):
        super().__init__(bounds, brush=pg.mkBrush(255, 255, 0, 50), pen=pg.mkPen('y', width=2), **kwargs)
        self.label_text = label_text
        self.parent_plot = parent_plot
        self.main_app = main_app
        
        self.text_item = pg.TextItem(label_text, color='k', anchor=(0.5, 0.5))
        self.parent_plot.addItem(self.text_item)
        
        self.sigRegionChanged.connect(self.update_label_pos)
        self.update_label_pos()

    def update_label_pos(self):
        """Keeps the text label centered within the bounding region."""
        minX, maxX = self.getRegion()
        self.text_item.setPos((minX + maxX) / 2, 0.5)

    def mouseClickEvent(self, ev):
        """Handles single clicks for selection and double clicks for label editing."""
        if ev.button() == Qt.MouseButton.LeftButton:
            ev.accept()

            if ev.double():
                new_label, ok = QInputDialog.getText(None, "Edit", "Name:", text=self.label_text)
                if ok and new_label is not None:
                    self.label_text = new_label
                    self.text_item.setText(new_label)
                    logger.info(f"Annotation label updated to: '{new_label}'")
            else:
                if self.main_app:
                    minX, maxX = self.getRegion()
                    self.main_app.force_selection(minX, maxX)
        else:
            super().mouseClickEvent(ev)

# ==========================================
# Main Waveform Viewer Window
# ==========================================
class WaveformViewer(QMainWindow):
    """
    Advanced audio viewer supporting waveform, spectrogram, and Praat-style TextGrid annotations.
    """
    def __init__(self, audio_path):
        super().__init__()
        self.audio_path = audio_path
        self.annotation_regions = []

        # Throttle GUI updates to prevent lag during rapid scrolling
        self.update_timer = QTimer()
        self.update_timer.setSingleShot(True)
        self.update_timer.timeout.connect(self.update_view)
        self.current_range = (0, 0)

        # Synchronizes the red playback line with actual audio output
        self.playback_timer = QTimer()
        self.playback_timer.setInterval(30)
        self.playback_timer.timeout.connect(self.update_playback_cursor)

        logger.info(f"Initializing WaveformViewer for: {self.audio_path}")
        self.setup_ui()
        self.load_waveform()

    def setup_ui(self):
        """Constructs the main interface layout and connects interactive elements."""
        self.setWindowTitle(f"Waveform Viewer - {os.path.basename(self.audio_path)}")
        self.resize(1000, 700)
        
        pg.setConfigOption("background", "w")
        pg.setConfigOption("foreground", "k")
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        self.main_layout = QVBoxLayout(central_widget)
        self.main_layout.setContentsMargins(40, 30, 40, 20) 
        
        self.graph_layout = pg.GraphicsLayoutWidget()
        self.main_layout.addWidget(self.graph_layout)
        self.graph_layout.ci.layout.setSpacing(0) 

        self._setup_waveform_plot()
        self._setup_spectrogram_plot()
        self._setup_annotations_plot()
        self._setup_time_info_panel()
        self._setup_control_panel()
        self._setup_menu_bar()
        self._setup_selection_tools()

        # Keyboard Shortcuts
        self.shortcut_play = QShortcut(QKeySequence(Qt.Key.Key_Tab), self)
        self.shortcut_play.activated.connect(self.play_audio)

        self.shortcut_delete = QShortcut(QKeySequence("Ctrl+Alt+Backspace"), self)
        self.shortcut_delete.activated.connect(self.delete_selected_annotation)

    def _setup_waveform_plot(self):
        """Initializes the top plot displaying the amplitude envelope."""
        vb_waveform = ViewBox()
        vb_waveform.cursor_moved.connect(self.set_cursor)
        vb_waveform.selection_started.connect(self.start_selection)
        vb_waveform.selection_updated.connect(self.update_selection)

        self.plot_waveform = self.graph_layout.addPlot(row=0, col=0, viewBox=vb_waveform)
        self.plot_waveform.setLabel('left', 'Amplitude')
        self.plot_waveform.hideAxis('bottom')
        self.plot_waveform.getViewBox().setBorder(pg.mkPen('k', width=1))
        self.plot_waveform.getAxis('left').setWidth(60)
        self.plot_waveform.setMouseEnabled(x=True, y=False)
        self.waveform_curve = self.plot_waveform.plot(pen=pg.mkPen('k', width=1))
        
        self.plot_waveform.getViewBox().sigXRangeChanged.connect(self.on_xrange_changed)

    def _setup_spectrogram_plot(self):
        """Initializes the middle plot displaying the frequency spectrum."""
        vb_spectrogram = ViewBox()
        vb_spectrogram.cursor_moved.connect(self.set_cursor)
        vb_spectrogram.selection_started.connect(self.start_selection)
        vb_spectrogram.selection_updated.connect(self.update_selection)

        self.graph_layout.nextRow()
        self.plot_spectrogram = self.graph_layout.addPlot(row=1, col=0, viewBox=vb_spectrogram)
        self.plot_spectrogram.setLabel('left', 'Frequency (Hz)')
        self.plot_spectrogram.hideAxis('bottom')
        self.plot_spectrogram.setXLink(self.plot_waveform)
        self.plot_spectrogram.getViewBox().setBorder(pg.mkPen('k', width=1))
        self.plot_spectrogram.getAxis('left').setWidth(60)
        self.plot_spectrogram.setMouseEnabled(x=True, y=False)
        self.plot_spectrogram.setYRange(0, 4000)
        
        self.img_spectrogram = pg.ImageItem()
        self.plot_spectrogram.addItem(self.img_spectrogram)
        
        praat_cmap = pg.ColorMap(pos=[0.0, 1.0], color=[(255, 255, 255, 255), (0, 0, 0, 255)])
        self.img_spectrogram.setLookupTable(praat_cmap.getLookupTable())

        self.spectrogram_warning = pg.TextItem(
            "Spectrogram is displayed only for visible regions shorter than 10 seconds.", 
            color='k', anchor=(0.5, 0.5))
        self.plot_spectrogram.addItem(self.spectrogram_warning)
        self.spectrogram_warning.hide()

    def _setup_annotations_plot(self):
        """Initializes the bottom plot where TextGrid annotation regions are drawn."""
        vb_annotations = ViewBox()
        vb_annotations.cursor_moved.connect(self.set_cursor)
        vb_annotations.selection_started.connect(self.start_selection)
        vb_annotations.selection_updated.connect(self.update_selection)

        self.graph_layout.nextRow()
        self.plot_annotations = self.graph_layout.addPlot(row=2, col=0, viewBox=vb_annotations)
        self.plot_annotations.setLabel('bottom', 'Time', units='s')
        self.plot_annotations.setMaximumHeight(150)
        self.plot_annotations.hideAxis('left')
        self.plot_annotations.setYRange(0, 1)
        self.plot_annotations.setXLink(self.plot_waveform)
        self.plot_annotations.getViewBox().setBorder(pg.mkPen('k', width=1))
        self.plot_annotations.showAxis('left')
        self.plot_annotations.getAxis('left').setWidth(60)
        self.plot_annotations.getAxis('left').setStyle(showValues=False)
        self.plot_annotations.setMouseEnabled(x=True, y=False)

    def _setup_control_panel(self):
        """Builds the button row for saving, loading, zooming, and playback."""
        btn_layout = QHBoxLayout()

        self.btn_save = QPushButton("Save Labels")
        self.btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_save.clicked.connect(self.save_labels)

        self.btn_load_excel = QPushButton("Load Model Output")
        self.btn_load_excel.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_load_excel.clicked.connect(self._prompt_load_excel)

        self.btn_zoom_in = QPushButton("Zoom In")
        self.btn_zoom_in.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_zoom_in.clicked.connect(self.zoom_in)

        self.btn_zoom_out = QPushButton("Zoom Out")
        self.btn_zoom_out.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_zoom_out.clicked.connect(self.zoom_out)

        self.btn_play = QPushButton("Play")
        self.btn_play.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_play.clicked.connect(self.play_audio)

        self.scrollbar = self._setup_scrollbar()
        btn_layout.addWidget(self.scrollbar, stretch=1)

        btn_layout.addWidget(self.btn_save)
        btn_layout.addWidget(self.btn_load_excel)
        btn_layout.addWidget(self.btn_zoom_in)
        btn_layout.addWidget(self.btn_zoom_out)
        btn_layout.addWidget(self.btn_play)

        self.main_layout.addLayout(btn_layout)

    def _setup_time_info_panel(self):
        """Creates the labels displaying current selection and visible duration."""
        self.time_info_layout = QVBoxLayout()
        self.time_info_layout.setSpacing(0)

        def create_info_label(text):
            lbl = QLabel(text)
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setStyleSheet("""
                background-color: #d9d9d9;
                border: 1px solid #888888;
                color: black;
                font-size: 12px;
                padding: 2px;
            """)
            return lbl

        self.lbl_selection = create_info_label("Selected Region: None")
        self.lbl_visible = create_info_label("Visible Region: None")
        self.lbl_total = create_info_label("Total Duration: None")

        self.time_info_layout.addWidget(self.lbl_selection)
        self.time_info_layout.addWidget(self.lbl_visible)
        self.time_info_layout.addWidget(self.lbl_total)

        self.main_layout.addLayout(self.time_info_layout)

    def _setup_menu_bar(self):
        self.menu_bar = MenuBar()
        self.setMenuBar(self.menu_bar)
    
    def _setup_scrollbar(self):
        """Configures the custom styled horizontal scrollbar."""
        scrollbar = QScrollBar(Qt.Orientation.Horizontal)
        scrollbar.setCursor(Qt.CursorShape.PointingHandCursor)
        scrollbar.setFixedHeight(26)
        scrollbar.valueChanged.connect(self.on_scrollbar_moved)
        self._is_scrolling = False

        scrollbar.setStyleSheet(f"""
            QScrollBar:horizontal {{
                height: 26px;
                background: #e0e0e0;
                border: 1px solid #999;
                border-radius: 4px;
                margin: 0px 24px 0px 24px;
            }}
            QScrollBar::handle:horizontal {{ background: #888; min-width: 30px; border-radius: 3px; margin: 2px 0px 2px 0px; }}
            QScrollBar::handle:horizontal:hover {{ background: #666; }}
            QScrollBar::sub-line:horizontal {{ border: 1px solid #999; background: #d0d0d0; width: 24px; subcontrol-position: left; subcontrol-origin: margin; border-top-left-radius: 4px; border-bottom-left-radius: 4px; }}
            QScrollBar::add-line:horizontal {{ border: 1px solid #999; background: #d0d0d0; width: 24px; subcontrol-position: right; subcontrol-origin: margin; border-top-right-radius: 4px; border-bottom-right-radius: 4px; }}
            QScrollBar::left-arrow:horizontal {{ image: url("data:image/svg+xml;base64,{SCROLLBAR_LEFT_SVG}"); width: 10px; height: 10px; }}
            QScrollBar::right-arrow:horizontal {{ image: url("data:image/svg+xml;base64,{SCROLLBAR_RIGHT_SVG}"); width: 10px; height: 10px; }}
            QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{ background: none; }}
        """)
        return scrollbar

    def _setup_selection_tools(self):
        """Initializes the red playback cursors and the blue drag-selection bounding boxes."""
        self.cursors = []
        self.selection_boxes = []
        self.is_selection_active = False
        self.selection_start = 0

        for plot in [self.plot_waveform, self.plot_spectrogram, self.plot_annotations]:
            cursor = pg.InfiniteLine(angle=90, movable=False, pen=pg.mkPen('r', width=1))
            cursor.hide()
            plot.addItem(cursor)
            self.cursors.append(cursor)

            region = pg.LinearRegionItem(brush=pg.mkBrush(0, 100, 255, 50), pen=pg.mkPen('b', width=1), movable=False)
            region.hide()
            plot.addItem(region)
            self.selection_boxes.append(region)

    def zoom_in(self):
        """Halves the currently visible duration."""
        x_min, x_max = self.plot_waveform.getViewBox().viewRange()[0]
        center = (x_min + x_max) / 2.0
        new_duration = (x_max - x_min) * 0.5
        new_min = max(0, center - new_duration / 2.0)
        new_max = min(self.total_duration, center + new_duration / 2.0)
        self.plot_waveform.setXRange(new_min, new_max)

    def zoom_out(self):
        """Doubles the currently visible duration."""
        x_min, x_max = self.plot_waveform.getViewBox().viewRange()[0]
        center = (x_min + x_max) / 2.0
        new_duration = (x_max - x_min) * 2.0
        new_min = max(0, center - new_duration / 2.0)
        new_max = min(self.total_duration, center + new_duration / 2.0)
        self.plot_waveform.setXRange(new_min, new_max)

    def add_annotation(self, tmin, tmax, label):
        """Draws a new yellow annotation region on the bottom plot."""
        region = AnnotationRegion([tmin, tmax], label, self.plot_annotations, main_app=self)
        self.plot_annotations.addItem(region)
        self.annotation_regions.append(region)
        region.sigRegionChanged.connect(lambda: self.update_selection_info(region))
        return region

    def load_waveform(self):
        """Reads the audio metadata and initializes the plot bounds."""
        try:
            self.audio_info = sf.info(self.audio_path)
            self.sr = self.audio_info.samplerate
            self.total_duration = self.audio_info.frames / self.sr

            self.lbl_total.setText(f"Total duration {self.total_duration:.6f} seconds")

            if self.audio_info.frames == 0:
                self.lbl_info.setText("Error: Audio file is empty.")
                logger.error("Loaded audio file is empty.")
                return

            self.plot_waveform.setLimits(xMin=0, xMax=self.total_duration)
            self.plot_waveform.setXRange(0, min(20.0, self.total_duration))
            logger.info("Audio waveform metadata loaded successfully.")
            
        except Exception as e:
            logger.exception(f"Error loading audio file '{self.audio_path}': {e}")

    def on_xrange_changed(self, view_box, range_tuple):
        """Triggers a re-render of the plots when the user zooms or scrolls."""
        self.current_range = range_tuple
        self.update_timer.start(150)

        t_start, t_end = range_tuple
        t_start = max(0, t_start)
        t_end = min(self.total_duration, t_end)
        self.lbl_visible.setText(f"Visible part {t_end - t_start:.6f} seconds")

        if getattr(self, 'is_selection_active', False):
            self._update_visual_selection()

        if not getattr(self, '_is_scrolling', False):
            self._is_scrolling_from_graph = True

            scale = 1000.0
            visible_duration = t_end - t_start
            page_step = int(visible_duration * scale)
            self.scrollbar.setPageStep(page_step)
            self.scrollbar.setSingleStep(max(1, int(page_step * 0.1)))
            max_scroll = int((self.total_duration - visible_duration) * scale)
            self.scrollbar.setMaximum(max(0, max_scroll))
            self.scrollbar.setValue(int(t_start * scale))

            self._is_scrolling_from_graph = False

    def update_view(self):
        """
        Dynamically reads a chunk of audio from disk based on the visible range
        and computes the spectrogram. This prevents RAM exhaustion on huge files.
        """
        if not hasattr(self, 'audio_info'):
            return
            
        t_start, t_end = self.current_range
        t_start = max(0, t_start)
        t_end = min(self.total_duration, t_end)
        
        start_frame = int(t_start * self.sr)
        frames_to_read = int((t_end - t_start) * self.sr)
        
        if frames_to_read <= 0:
            return
            
        data, _ = sf.read(self.audio_path, start=start_frame, frames=frames_to_read)
        
        if len(data.shape) > 1:
            data = np.mean(data, axis=1)

        # Downsample waveform plotting if too many points are visible
        max_plot_points = 200_000
        if len(data) > max_plot_points:
            indices = np.linspace(0, len(data) - 1, max_plot_points, dtype=np.int64)
            plot_data = data[indices]
            time_axis = np.linspace(t_start, t_end, max_plot_points)
        else:
            plot_data = data
            time_axis = np.linspace(t_start, t_end, len(data))
            
        self.waveform_curve.setData(time_axis, plot_data)

        visible_duration = t_end - t_start

        # Only compute the heavy spectrogram if the visible window is < 10 seconds
        if len(data) > 1024 and visible_duration <= 10.0:
            self.spectrogram_warning.hide()

            f, t, Sxx = signal.spectrogram(
                data, fs=self.sr, window='hann',
                nperseg=1024, noverlap=896, nfft=4096      
            )
            
            Sxx_log = 10 * np.log10(Sxx + 1e-10)
            max_val = np.max(Sxx_log)
            Sxx_log = np.clip(Sxx_log, a_min=max_val - 60, a_max=max_val)
            
            self.img_spectrogram.setImage(Sxx_log.T, autoLevels=False)
            self.img_spectrogram.setLevels([max_val - 60, max_val])
            
            rect = QRectF(t_start, 0, t_end - t_start, self.sr / 2)
            self.img_spectrogram.setRect(rect)
        else:
            self.img_spectrogram.clear()
            center_x = t_start + (visible_duration / 2.0)
            self.spectrogram_warning.setPos(center_x, 2000)
            self.spectrogram_warning.show()

    def play_audio(self):
        """Plays the selected region, or the visible region if nothing is selected."""
        if not hasattr(self, 'audio_info'):
            return

        if getattr(self, 'is_selection_active', False):
            t_start = self.selection_tmin
            t_end = self.selection_tmax
            if t_start == t_end:
                return
        elif getattr(self, 'cursors', None) and self.cursors[0].isVisible():
            t_start = self.cursors[0].value()
            t_end = self.current_range[1]
            if t_start >= t_end:
                return
        else:
            t_start, t_end = self.current_range

        t_start = max(0, t_start)
        t_end = min(self.total_duration, t_end)

        start_frame = int(t_start * self.sr)
        frames_to_read = int((t_end - t_start) * self.sr)

        if frames_to_read <= 0:
            return

        try:
            self.stop_audio()
            data, _ = sf.read(self.audio_path, start=start_frame, frames=frames_to_read)

            self.audio_start_pos = t_start
            self.audio_end_pos = t_end
            self.playback_start_time = time.time()

            for cursor in self.cursors:
                cursor.show()
            
            sd.play(data, samplerate=self.sr)
            self.playback_timer.start()
            logger.info(f"Playback started from {t_start:.2f} to {t_end:.2f}")

        except Exception as e:
            logger.exception(f"Error playing audio: {e}")

    def set_cursor(self, x_pos):
        x_pos = max(0, min(self.total_duration, x_pos))
        self.is_selection_active = False

        for region in self.selection_boxes:
            region.hide()

        for cursor in self.cursors:
            cursor.setValue(x_pos)
            cursor.show()

    def _update_visual_selection(self):
        """Updates the rendering bounds of the blue drag-selection box."""
        t_start, t_end = self.current_range
        v_start = max(t_start - 2.0, self.selection_tmin)
        v_end = min(t_end + 2.0, self.selection_tmax)

        for region in self.selection_boxes:
            region.setRegion([v_start, v_end])

    def start_selection(self, x_pos):
        x_pos = max(0, min(self.total_duration, x_pos))
        self.selection_start = x_pos
        self.selection_tmin = x_pos
        self.selection_tmax = x_pos
        self.is_selection_active = True

        for cursor in self.cursors:
            cursor.hide()

        for region in self.selection_boxes:
            region.show()

        self._update_visual_selection()

    def update_selection(self, x_pos):
        x_pos = max(0, min(self.total_duration, x_pos))
        self.selection_tmin = min(self.selection_start, x_pos)
        self.selection_tmax = max(self.selection_start, x_pos)

        duration = self.selection_tmax - self.selection_tmin
        self.lbl_selection.setText(f"Selected Region: {duration:.6f} s ({self.selection_tmin:.6f} - {self.selection_tmax:.6f})")
        self._update_visual_selection()

    def update_selection_info(self, region):
        minX, maxX = region.getRegion()
        duration = maxX - minX
        self.lbl_selection.setText(f"Selected Region: {duration:.6f} s ({minX:.6f} - {maxX:.6f})")

    def stop_audio(self):
        """Halts the sounddevice playback and resets the cursor timer."""
        try:
            sd.stop()
            self.playback_timer.stop()
        except Exception as e:
            logger.error(f"Error stopping audio playback: {e}")

    def update_playback_cursor(self):
        """Timer callback that moves the red line during active playback."""
        elapsed = time.time() - self.playback_start_time
        current_pos = self.audio_start_pos + elapsed

        if current_pos >= self.audio_end_pos:
            current_pos = self.audio_end_pos
            self.playback_timer.stop()
        
        for cursor in self.cursors:
            cursor.setValue(current_pos)

    def on_scrollbar_moved(self, value):
        """Handles panning the plots via the bottom scrollbar."""
        if getattr(self, '_is_scrolling_from_graph', False):
            return
        
        self._is_scrolling = True
        scale = 1000.0
        t_start = value / scale
        visible_duration = self.current_range[1] - self.current_range[0]
        t_end = t_start + visible_duration

        self.plot_waveform.setXRange(t_start, t_end, padding=0)
        self._is_scrolling = False

    def keyPressEvent(self, event):
        """Intercepts specific key presses (Enter to annotate, Escape to stop)."""
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.handle_annotation_enter()
        elif event.key() == Qt.Key.Key_Escape:
            self.stop_audio()
        elif event.key() == Qt.Key.Key_Tab:
            self.play_audio()
            event.accept()
        else:
            super().keyPressEvent(event)

    def prompt_for_label(self, region):
        """Displays a dialog to name a newly created annotation region."""
        new_label, ok = QInputDialog.getText(self, "Edit Annotation", "Enter label:", text=region.label_text)
        if ok and new_label is not None:
            region.label_text = new_label
            region.text_item.setText(new_label)
            logger.info(f"Created new annotation: '{new_label}'")

    def remove_annotation(self, region):
        """Safely removes an annotation from the plot and tracking list."""
        if region in self.annotation_regions:
            self.plot_annotations.removeItem(region)
            self.plot_annotations.removeItem(region.text_item)
            self.annotation_regions.remove(region)
            logger.info(f"Removed annotation: '{region.label_text}'")
    
    def handle_annotation_enter(self):
        """Processes the Enter key to instantiate a permanent yellow TextGrid region from a blue selection."""
        if getattr(self, 'is_selection_active', False) and self.selection_tmin != self.selection_tmax:
            t_min = min(self.selection_tmin, self.selection_tmax)
            t_max = max(self.selection_tmin, self.selection_tmax)

            # Prevent overlaps
            for region in self.annotation_regions:
                r_min, r_max = region.getRegion()
                if max(t_min, r_min) < min(t_max, r_max):
                    logger.warning("Annotation creation failed: Overlap detected.")
                    QMessageBox.warning(self, "Overlap Detected", "The selected region overlaps with an existing annotation.")
                    return
            
            new_region = self.add_annotation(t_min, t_max, "")
            self.prompt_for_label(new_region)

        # Handle splitting an existing annotation using the red cursor
        elif getattr(self, 'cursors', None) and self.cursors[0].isVisible():
            t_cursor = self.cursors[0].value()
            left_bound, right_bound = 0.0, self.total_duration
            hit_region = None

            for region in self.annotation_regions:
                r_min, r_max = region.getRegion()
                if r_min < t_cursor < r_max:
                    hit_region = region
                    left_bound, right_bound = r_min, r_max
                    break
                elif r_max <= t_cursor:
                    left_bound = max(left_bound, r_max)
                elif r_min >= t_cursor:
                    right_bound = min(right_bound, r_min)
            
            if hit_region:
                old_text = hit_region.label_text
                self.remove_annotation(hit_region)
                self.add_annotation(left_bound, t_cursor, old_text)
                self.add_annotation(t_cursor, right_bound, "")
                logger.info("Split existing annotation at cursor.")
            else:
                self.add_annotation(left_bound, t_cursor, "")
                self.add_annotation(t_cursor, right_bound, "")

    def force_selection(self, t_min, t_max):
        """Programmatically forces a blue selection box (used when double-clicking labels)."""
        self.selection_start = t_min
        self.selection_tmin = t_min
        self.selection_tmax = t_max
        self.is_selection_active = True

        for cursor in self.cursors:
            cursor.hide()
        for region in self.selection_boxes:
            region.show()
        
        duration = self.selection_tmax - self.selection_tmin
        self.lbl_selection.setText(f"Selected Region: {duration:.6f} s ({self.selection_tmin:.6f} - {self.selection_tmax:.6f})")
        self._update_visual_selection() 

    def delete_selected_annotation(self):
        """Deletes annotations that intersect with the current cursor or selection box."""
        to_remove = []

        if getattr(self, 'is_selection_active', False) and self.selection_tmin != self.selection_tmax:
            t_start = min(self.selection_tmin, self.selection_tmax)
            t_end = max(self.selection_tmin, self.selection_tmax)

            for region in self.annotation_regions:
                r_min, r_max = region.getRegion()
                if max(t_start, r_min) < min(t_end, r_max):
                    to_remove.append(region)

        elif getattr(self, 'cursors', None) and self.cursors[0].isVisible():
            t_cursor = self.cursors[0].value()
            for region in self.annotation_regions:
                r_min, r_max = region.getRegion()
                if r_min <= t_cursor <= r_max:
                    to_remove.append(region)

        for region in to_remove:
            self.remove_annotation(region)
    
    def save_labels(self):
        """Exports the current annotations to a JSON, CSV, or Excel file."""
        if not self.annotation_regions:
            logger.warning("User attempted to save empty annotations.")
            QMessageBox.information(self, "Info", "No annotations to save.")
            return

        labels_data = []
        sorted_regions = sorted(self.annotation_regions, key=lambda r: r.getRegion()[0])

        for region in sorted_regions:
            t_start, t_end = region.getRegion()
            labels_data.append({
                "tmin": round(t_start, 4),
                "tmax": round(t_end, 4),
                "label": region.label_text
            })

        current_audio_filename = os.path.basename(self.audio_path)
        base_name = os.path.splitext(current_audio_filename)[0]

        file_name, selected_filter = QFileDialog.getSaveFileName(
            self, "Save Labels", f"labels_{base_name}",
            "JSON Files (*.json);;Excel Files (*.xlsx);;CSV Files (*.csv)"
        )

        if file_name:
            try:
                # Force correct extension
                if "JSON" in selected_filter and not file_name.endswith('.json'):
                    file_name += '.json'
                elif "Excel" in selected_filter and not file_name.endswith('.xlsx'):
                    file_name += '.xlsx'
                elif "CSV" in selected_filter and not file_name.endswith('.csv'):
                    file_name += '.csv'

                if file_name.endswith('.json'):
                    with open(file_name, 'w') as f:
                        json.dump(labels_data, f, indent=4)
                else:
                    df = pd.DataFrame(labels_data)
                    df.insert(0, 'File', current_audio_filename)
                    if file_name.endswith('.xlsx'):
                        df.to_excel(file_name, index=False)
                    elif file_name.endswith('.csv'):
                        df.to_csv(file_name, index=False)
                        
                logger.info(f"Annotations successfully saved to: {file_name}")
                QMessageBox.information(self, "Success", f"Labels saved to:\n{file_name}")
            except Exception as e:
                logger.exception("Failed to save annotation labels.")
                QMessageBox.critical(self, "Error", f"Failed to save labels: {str(e)}")
    
    def _prompt_load_excel(self):
        """Prompts the user to load pre-existing labels from a CSV or Excel file."""
        file_name, _ = QFileDialog.getOpenFileName(
            self, "Select Model Output", "",
            "Excel Files (*.xlsx);; CSV Files (*.csv)"
        )
        if file_name:
            if file_name.endswith('.csv'):
                try:
                    df = pd.read_csv(file_name)
                    self._process_loaded_dataframe(df)
                except Exception as e:
                    logger.error(f"Failed to load CSV: {e}")
                    QMessageBox.critical(self, "Error", f"Failed to load CSV: {str(e)}")
            else:
                self.load_labels_from_excel(file_name)

    def _process_loaded_dataframe(self, df):
        """Parses a DataFrame and draws annotation regions on the UI."""
        try:
            current_audio_filename = os.path.basename(self.audio_path)
            current_base_name = os.path.splitext(current_audio_filename)[0]

            if 'File' in df.columns:
                df = df[df['File'].str.contains(current_base_name, case=False, na=False)]

                if df.empty:
                    logger.warning(f"No matching entries found for '{current_base_name}' in the loaded file.")
                    QMessageBox.warning(self, "Warning", f"No matching entries found for {current_base_name} in the provided file.")
                    return
            
            for _, row in df.iterrows():
                tmin, tmax, label_text = float(row['tmin']), float(row['tmax']), str(row['label'])
                self.add_annotation(tmin, tmax, label_text)
                
            logger.info(f"Successfully loaded {len(df)} annotations into the viewer.")
        
        except Exception as e:
            logger.exception("Error processing loaded dataframe.")
            QMessageBox.critical(self, "Error", f"Error processing data: {str(e)}")
    
    def load_labels_from_excel(self, excel_path):
        """Wrapper to read an Excel file into a DataFrame."""
        try:
            df = pd.read_excel(excel_path)
            self._process_loaded_dataframe(df)
        except Exception as e:
            logger.error(f"Failed to load Excel file: {e}")
            QMessageBox.critical(self, "Error", f"Failed to load Excel file: {str(e)}")