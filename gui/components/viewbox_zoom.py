import pyqtgraph as pg
from PyQt6.QtCore import Qt

class ViewBox(pg.ViewBox):
    def __init__(self, main_app=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.main_app = main_app

    def wheelEvent(self, ev, axis=None):
        if ev.modifiers() & Qt.KeyboardModifier.ControlModifier:
            super().wheelEvent(ev, axis)
        else:
            ev.accept()
    
    def mouseClickEvent(self, ev):
        if ev.isAccepted():
            return

        if ev.button() == Qt.MouseButton.LeftButton:
            ev.accept()

            pos = self.mapSceneToView(ev.scenePos())
            if self.main_app:
                self.main_app.set_cursor(pos.x())
        else:
            super().mouseClickEvent(ev)
    
    def mouseDragEvent(self, ev, axis=None):
        if ev.isAccepted():
            return

        if ev.button() == Qt.MouseButton.LeftButton:
            ev.accept()
            pos = self.mapSceneToView(ev.scenePos())

            if ev.isStart():
                if self.main_app:
                    self.main_app.start_selection(pos.x())
            else:
                if self.main_app:
                    self.main_app.update_selection(pos.x())
        else:
            super().mouseDragEvent(ev, axis)