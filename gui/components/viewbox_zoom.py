import pyqtgraph as pg
import logging
from PyQt6.QtCore import Qt, pyqtSignal

logger = logging.getLogger(__name__)
class ViewBox(pg.ViewBox):
    cursor_moved = pyqtSignal(float)  # Signal emitted when the cursor is moved
    selection_started = pyqtSignal(float)  # Signal emitted when selection starts
    selection_updated = pyqtSignal(float)  # Signal emitted when selection is updated

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def wheelEvent(self, ev, axis=None):
        """Zoom in/out on the plot when CTRL is pressed, otherwise ignore the event."""
        if ev.modifiers() & Qt.KeyboardModifier.ControlModifier:
            super().wheelEvent(ev, axis)
            logger.info(f"Zoom event: delta={ev.angleDelta()}, axis={axis}")
        else:
            ev.accept() 
    
    def mouseClickEvent(self, ev):
        """Handle mouse click events to move the cursor."""
        if ev.isAccepted():
            return

        if ev.button() == Qt.MouseButton.LeftButton:
            ev.accept()
            pos = self.mapSceneToView(ev.scenePos())
            self.cursor_moved.emit(pos.x())
        else:
            super().mouseClickEvent(ev)
    
    def mouseDragEvent(self, ev, axis=None):
        """Handle mouse drag events to start or update selection."""
        if ev.isAccepted():
            return

        if ev.button() == Qt.MouseButton.LeftButton:
            ev.accept()
            pos = self.mapSceneToView(ev.scenePos())

            if ev.isStart():
                self.selection_started.emit(pos.x())
            else:
                self.selection_updated.emit(pos.x())
        else:
            super().mouseDragEvent(ev, axis)