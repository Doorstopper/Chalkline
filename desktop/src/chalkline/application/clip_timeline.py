"""All clip-strip interaction state lives here, separate from playback."""
from copy import deepcopy
from PySide6.QtCore import QObject, Property, Signal, Slot
from chalkline.domain.clip_timeline import strip_model, trim_edge
from chalkline.domain.timing_edits import drag_timing


class ClipTimeline(QObject):
    changed = Signal()

    def __init__(self, studio):
        super().__init__(studio)
        self.studio = studio
        self._drag = None
        studio.changed.connect(self._refresh)
        studio.exportChanged.connect(self._refresh)

    def _valid(self):
        s, d = self.studio, self._drag
        return (d is not None and not s.busy and d['project'] is s.project
                and d['mark'] == s.current and d['key'] == s.notesEditorKey
                and d['offset'] == s.project['session'].get('offset', 0)
                and d['duration'] == s.duration)

    def _refresh(self):
        if self._drag and not self._valid():
            self._drag = None
        self.changed.emit()

    @Property(bool, notify=changed)
    def dragging(self):
        return self._drag is not None

    @Property('QVariantMap', notify=changed)
    def model(self):
        s = self.studio
        try:
            mark = self._drag['preview'] if self._drag else s.current
            window = (self._drag['left'], self._drag['right']) if self._drag else None
            result = strip_model(mark, s.project['session'].get('offset', 0), s.duration, s.renderSettings, window)
            return result
        except (ValueError, KeyError, TypeError):
            return {}

    @Slot(str, result=bool)
    def begin(self, edge):
        s, model = self.studio, self.model
        if s.busy or self.dragging or s.markup.drawing or not model or edge not in ('start', 'end'):
            return False
        s.finishNotesEdit()
        self._drag = dict(project=s.project, mark=deepcopy(s.current), preview=deepcopy(s.current),
                          key=s.notesEditorKey, offset=s.project['session'].get('offset', 0),
                          duration=s.duration, left=model['left'], right=model['right'], edge=edge, kind='trim')
        self.changed.emit()
        return True

    @Slot(str, int, str, result=bool)
    def beginTiming(self, kind, index, edge):
        s, model = self.studio, self.model
        if s.busy or self.dragging or s.markup.drawing or not model:
            return False
        try:
            entries = s.current.get('freezes', []) if kind == 'freezes' else s.current.get('slow', [])
            if isinstance(entries, dict):
                entries = [entries]
            if index < 0 or index >= len(entries):
                return False
            at = entries[index][edge]
            # Validate before acquiring the gesture; keep the unchanged baseline
            # so a click on an unsnapped imported point stays a genuine no-op.
            drag_timing(s.current, kind, index, edge, at,
                        s.project['session'].get('offset', 0), s.duration)
        except (ValueError, KeyError, TypeError) as error:
            s.message(str(error))
            return False
        s.finishNotesEdit()
        self._drag = dict(project=s.project, mark=deepcopy(s.current), preview=deepcopy(s.current),
                          key=s.notesEditorKey, offset=s.project['session'].get('offset', 0),
                          duration=s.duration, left=model['left'], right=model['right'],
                          kind=kind, index=index, edge=edge)
        self.changed.emit()
        return True

    @Slot(float)
    def preview(self, source_time):
        if not self._valid():
            self.cancel()
            return
        d = self._drag
        try:
            if d['kind'] == 'trim':
                d['preview'] = trim_edge(d['mark'], d['edge'], source_time, d['offset'], d['duration'])
            else:
                d['preview'] = drag_timing(d['mark'], d['kind'], d['index'], d['edge'],
                                          source_time, d['offset'], d['duration'])
            self.changed.emit()
        except (ValueError, KeyError, TypeError) as error:
            self.studio.message(str(error))

    @Slot(result=bool)
    def commit(self):
        if not self._valid():
            self.cancel()
            return False
        s, d = self.studio, self._drag
        self._drag = None
        if d['preview'] != d['mark']:
            s.checkpoint()
            s.clips[s.selected] = d['preview']
            s.touchCurrent()
        self.changed.emit()
        return True

    @Slot()
    def cancel(self):
        self._drag = None
        self.changed.emit()

    @Slot(str, float)
    def nudge(self, edge, delta):
        model = self.model
        if edge in ('start', 'end') and self.begin(edge):
            self.preview(model[edge]+delta)
            self.commit()

    @Slot(str, int, float)
    def editPoint(self, kind, index, at):
        if self.studio.busy or self.dragging:
            return
        self.studio.seek(at)
        if kind == 'freezes' and index < 0:
            self.studio.addFreeze()
        elif kind in ('freezes', 'slow'):
            self.studio.editTiming(kind, index)
        elif kind == 'markup':
            self.studio.markup.select(index)
