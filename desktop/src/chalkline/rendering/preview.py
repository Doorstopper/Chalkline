from PySide6.QtCore import Property, Signal, Slot
from PySide6.QtQuick import QQuickPaintedItem
from chalkline.rendering.annotations import paint_annotations


class AnnotationLayer(QQuickPaintedItem):
    changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._data = {}
        self._time = 0.0
        self._settings = {}

    def get_data(self):
        return self._data

    def set_data(self, value):
        self._data = value
        self.update()

    dataModel = Property('QVariantMap', get_data, set_data, notify=changed)

    def get_time(self):
        return self._time

    def set_time(self, value):
        self._time = value
        self.update()

    sourceTime = Property(float, get_time, set_time, notify=changed)

    def get_settings(self):
        return self._settings

    def set_settings(self, value):
        self._settings = value
        self.update()

    settings = Property('QVariantMap', get_settings, set_settings, notify=changed)

    def paint(self, painter):
        paint_annotations(painter, round(self.width()), round(self.height()), self._data, self._time, self._settings)
