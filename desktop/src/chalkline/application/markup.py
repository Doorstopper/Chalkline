"""Drawing defaults, selection and one-gesture transactions, separate from Studio."""
from copy import deepcopy
import math
from PySide6.QtCore import QObject, Property, Signal, Slot
from PySide6.QtWidgets import QInputDialog
from chalkline.domain.markup import TOOLS, COLORS, point, make_shape, edit_shape, move_shape


class Markup(QObject):
    changed = Signal()

    def __init__(self, studio):
        super().__init__(studio)
        self.studio = studio
        self._tool = 'pan'
        self._color = 'space'
        self._size = 19
        self._shape = None
        self._drag = None
        self._timing_revision = 0
        studio.changed.connect(self._refresh)
        studio.exportChanged.connect(self._refresh)
        studio.positionChanged.connect(self._position_changed)

    def _position_changed(self):
        if self._drag and not self._valid():
            self.cancel()

    def _valid(self):
        d, s = self._drag, self.studio
        return (d is not None and not s.busy and d['project'] is s.project
                and d['key'] == s.notesEditorKey and d['mark'] == s.current
                and abs(d['at']-s.position) < .001)

    def _refresh(self):
        self._timing_revision += 1
        if self._drag and not self._valid():
            self._drag = None
        if self._shape is not None and not any(s is self._shape for s in self.studio.current.get('shapes', [])):
            self._shape = None
        self.changed.emit()

    @Property(str, notify=changed)
    def tool(self):
        return self._tool

    @Property(int, notify=changed)
    def timingEditKey(self):
        return self._timing_revision

    @Property(str, notify=changed)
    def color(self):
        return self._color

    @Property(float, notify=changed)
    def textSize(self):
        return self._size

    @Property(bool, notify=changed)
    def drawing(self):
        return self._drag is not None

    @Property(int, notify=changed)
    def selection(self):
        return next((i for i, shape in enumerate(self.studio.current.get('shapes', [])) if shape is self._shape), -1)

    @Property('QVariantMap', notify=changed)
    def selected(self):
        return self._shape or {}

    @Property('QVariantList', notify=changed)
    def rows(self):
        return [dict(index=i, label=f"{i+1}. {shape.get('tool', 'Unknown')} · {shape.get('t', 0):.1f}s"
                     + (f" · {shape.get('text', '')[:28]}" if shape.get('text') else ''))
                for i, shape in enumerate(self.studio.current.get('shapes', []))]

    @Property('QVariantMap', notify=changed)
    def preview(self):
        mark = deepcopy(self.studio.current)
        if self._drag:
            mark.setdefault('shapes', []).append(self._drag['preview'])
        return mark

    @Slot(str)
    def setTool(self, tool):
        if tool in ('pan', *TOOLS):
            self.cancel()
            self._tool = tool
            self.changed.emit()

    @Slot(int)
    def select(self, index):
        self.cancel()
        self._timing_revision += 1
        shapes = self.studio.current.get('shapes', [])
        self._shape = shapes[index] if 0 <= index < len(shapes) else None
        if self._shape is not None:
            self.studio.stopReview()
            self.studio.player.pause()
            self.studio.frame_resume.stop()
            self.studio.seek(self._shape.get('t', self.studio.position))
            if self._shape.get('color') in COLORS:
                self._color = self._shape['color']
            if self._shape.get('tool') == 'text':
                self._size = self._shape.get('fs', 19)
        self.changed.emit()

    def _replace(self, candidate):
        index, s = self.selection, self.studio
        if index < 0 or s.busy or candidate == self._shape:
            return
        self.cancel()
        s.checkpoint()
        s.current['shapes'][index] = candidate
        self._shape = candidate
        s.touchCurrent()

    @Slot(str, 'QVariant', result=bool)
    def edit(self, field, value):
        if self.selection < 0 or self.studio.busy:
            return False
        try:
            self._replace(edit_shape(self._shape, field, value, self.studio.duration))
            if field == 't':
                self.studio.seek(float(value))
            return True
        except (ValueError, TypeError, KeyError) as error:
            self.studio.message(str(error))
            return False

    @Slot(str, 'QVariant', int, result=bool)
    def editTiming(self, field, value, expected_key):
        if field not in ('t', 'linger'):
            return False
        if expected_key != self._timing_revision:
            self.studio.message('The selected markup changed. Check its timing and apply again.')
            return False
        return self.edit(field, value)

    @Slot(str)
    def setColor(self, color):
        if color in COLORS and not self.studio.busy:
            self._color = color
            self.edit('color', color)
            self.changed.emit()

    @Slot(float)
    def setSize(self, size):
        if math.isfinite(size) and not self.studio.busy:
            size = max(10, min(60, round(size)))
            self._size = size
            if self.selected.get('tool') == 'text':
                self.edit('fs', size)
            self.changed.emit()

    @Slot(float)
    def setWeight(self, weight):
        s = self.studio
        if not math.isfinite(weight):
            return
        weight = max(.6, min(3, round(weight, 1)))
        if not s.busy and weight != s.renderSettings['lineWt']:
            self.cancel()
            s.checkpoint()
            s.project['session']['lineWt'] = round(weight, 2)
            s.changed.emit()

    @Slot()
    def editText(self):
        if self.selected.get('tool') != 'text' or self.studio.busy:
            return
        original, project = self._shape, self.studio.project
        text, ok = QInputDialog.getMultiLineText(None, 'Edit markup text', 'Text', original.get('text', ''))
        if ok and self._shape is original and self.studio.project is project:
            self.edit('text', text)

    @Slot(float, float)
    def move(self, dx, dy):
        if self.selection >= 0 and not self.studio.busy:
            try:
                self._replace(move_shape(self._shape, dx, dy))
            except (ValueError, KeyError, TypeError) as error:
                self.studio.message(str(error))

    @Slot()
    def duplicate(self):
        if self.selection >= 0 and not self.studio.busy:
            self.cancel()
            s = self.studio
            candidate = deepcopy(self._shape)
            s.checkpoint()
            s.current['shapes'].append(candidate)
            self._shape = candidate
            s.touchCurrent()
            s.message('Markup duplicated at the same position. Use the move arrows to place it.')

    @Slot()
    def delete(self):
        index, s = self.selection, self.studio
        if index >= 0 and not s.busy:
            self.cancel()
            s.checkpoint()
            s.current['shapes'].pop(index)
            self._shape = None
            s.touchCurrent()

    @Slot(float, float, result=bool)
    def begin(self, x, y):
        s = self.studio
        if s.busy or not s.current or self._tool not in TOOLS or s.duration <= 0:
            return False
        self.cancel()
        s.finishNotesEdit()
        s.stopReview()
        s.player.pause()
        s.frame_resume.stop()
        a = point(x, y)
        self._drag = dict(project=s.project, key=s.notesEditorKey, mark=deepcopy(s.current),
                          at=s.position, a=a, b=a, points=[a], tool=self._tool, color=self._color, size=self._size)
        self.update(x, y)
        return True

    @Slot(float, float)
    def update(self, x, y):
        if not self._valid():
            self.cancel()
            return
        d = self._drag
        d['b'] = point(x, y)
        if d['tool'] == 'pen' and d['b'] != d['points'][-1]:
            d['points'].append(d['b'])
        d['preview'] = make_shape(d['tool'], d['a'], d['b'], d['at'], d['color'], d['size'], d['points'], 'Text')
        self.changed.emit()

    @Slot()
    def commit(self):
        if not self._valid():
            self.cancel()
            return
        d, s = self._drag, self.studio
        if d['tool'] == 'text':
            text, ok = QInputDialog.getMultiLineText(None, 'Add markup text', 'Text')
            if not ok or not text.strip() or not self._valid():
                self.cancel()
                return
            d['preview']['text'] = text
        elif d['a'] == d['b'] and len(d['points']) < 2:
            self.cancel()
            return
        s.checkpoint()
        candidate = d['preview']
        self._drag = None
        s.current.setdefault('shapes', []).append(candidate)
        self._shape = candidate
        s.touchCurrent()

    @Slot()
    def cancel(self):
        self._drag = None
        self.changed.emit()
