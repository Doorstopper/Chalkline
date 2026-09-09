from copy import deepcopy
from dataclasses import replace
from pathlib import Path
import time
import math

from PySide6.QtCore import QObject, Property, Signal, Slot, QThread, QTimer, QUrl
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtWidgets import QFileDialog, QInputDialog, QMessageBox

from chalkline.domain.project import new_project, load_project, save_project, resolve_media
from chalkline.domain.timeline import clip_bounds, plan_clip, locate
from chalkline.domain.clips import pads_for, make_mark, clip_rows, players_of, set_players, delete_marks, TAG_KEYS
from chalkline.domain.transport import RATES, adjacent_clip, next_markup, review_offset
from chalkline.domain.timing_edits import slow_zones, update_timing, remove_timing
from chalkline.domain.notes import apply_notes, find_note, validate_style, freeze_note_context
from chalkline.ui.pad_editor import PadEditor
from chalkline.ui.timing_editor import TimingEditor
from chalkline.infrastructure.media import probe, find_tool
from chalkline.infrastructure.exporter import Exporter, ExportCancelled
from chalkline.rendering.annotations import SUPPORTED_TOOLS
from chalkline.rendering.text_layout import place_notes
from chalkline.application.clip_timeline import ClipTimeline
from chalkline.domain.clip_timeline import set_trim
from chalkline.application.markup import Markup


class ExportWorker(QObject):
    progress = Signal(float, str)
    finished = Signal(bool, str)

    def __init__(self, root, source, mark, offset, settings, destination):
        super().__init__()
        self.exporter = Exporter(root, progress=self.progress.emit)
        self.arguments = source, mark, offset, settings, destination

    @Slot()
    def run(self):
        try:
            result = self.exporter.export(*self.arguments)
            self.finished.emit(True, str(result))
        except Exception as error:
            self.finished.emit(False, str(error))


class Studio(QObject):
    changed = Signal()
    positionChanged = Signal()
    statusChanged = Signal()
    exportChanged = Signal()
    notesSyncRequested = Signal()

    def __init__(self, root: Path):
        super().__init__()
        self.root = root
        self.project = new_project()
        self.document = None
        self.source = None
        self.info = None
        self.selected = -1
        self._player_filter = '__all'
        self._loop_review = False
        self._loop_enabled = True
        self._clip_armed = False
        self._user_rate = 1.0
        self._review_paused = False
        self._review_elapsed = 0.0
        self._step_was_playing = False
        self._slow_pending = None
        self._slow_clip_id = None
        self._slow_default = .25
        self._freeze_default = 2
        self.dirty = False
        self.history = []
        self._notes_edit_id = None
        self._notes_context_generation = 0
        self._status = 'Open a match to test native playback and export.'
        self._progress = 0.0
        self._busy = False
        self.worker = None
        self.thread = None
        self._export_mark_id = None
        self._review = []
        self._review_start = 0.0
        self._review_segment = None
        self._source_time = 0.0
        self.player = QMediaPlayer(self)
        self.audio = QAudioOutput(self)
        self.player.setAudioOutput(self.audio)
        self.player.positionChanged.connect(self._position)
        self.player.playbackStateChanged.connect(self._playback_state_changed)
        self.player.errorOccurred.connect(lambda _, message: self.message(message))
        self.timer = QTimer(self)
        self.timer.setInterval(20)
        self.timer.timeout.connect(self._tick_review)
        self.timer.start()
        self.frame_resume = QTimer(self)
        self.frame_resume.setSingleShot(True)
        self.frame_resume.setInterval(700)
        self.frame_resume.timeout.connect(self._resume_after_step)
        self._clip_timeline = ClipTimeline(self)
        self._markup = Markup(self)

    @Property(QObject, constant=True)
    def markup(self):
        return self._markup

    @Property(QObject, constant=True)
    def clipTimeline(self):
        return self._clip_timeline

    @Property(QObject, constant=True)
    def mediaPlayer(self):
        return self.player

    @Property(str, notify=statusChanged)
    def status(self):
        return self._status

    @Property(float, notify=positionChanged)
    def position(self):
        return self._source_time

    @Property(float, notify=changed)
    def duration(self):
        return self.info.duration if self.info else 0

    @Property(float, notify=changed)
    def aspect(self):
        return self.info.width/self.info.height if self.info else 16/9

    @Property(str, notify=changed)
    def mediaName(self):
        return self.source.name if self.source else 'No match open'

    @Property(str, notify=changed)
    def mediaDetails(self):
        return f'{self.info.width} x {self.info.height}  /  {self.info.fps} fps' if self.info else 'Local files only'

    @Property(bool, notify=changed)
    def playing(self):
        if self._review:
            return not self._review_paused
        return self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState

    @Property(bool, notify=changed)
    def loopEnabled(self):
        return self._loop_enabled

    @Property(float, notify=changed)
    def playbackRate(self):
        return self._user_rate

    @Property(bool, notify=changed)
    def muted(self):
        return self.audio.isMuted()

    @Property(float, notify=changed)
    def bookmark(self):
        value = self.project['session'].get('watchMark')
        return float(value) if isinstance(value, (int, float)) and math.isfinite(value) and value >= 0 else -1

    @Property('QVariantList', notify=changed)
    def freezeRows(self):
        return self.current.get('freezes', [])

    @Property('QVariantList', notify=changed)
    def slowRows(self):
        return slow_zones(self.current)

    @Property(float, notify=changed)
    def slowPending(self):
        return self._slow_pending if self._slow_pending is not None and self._slow_clip_id == self.current.get('id') else -1

    @Property('QVariantMap', notify=changed)
    def notesStyle(self):
        return self.project['settings'].get('notesStyle', {'color': 'ours', 'size': 19, 'column': 0, 'row': 0})

    @Property(str, notify=changed)
    def notesEditorKey(self):
        return f"{self._notes_context_generation}:{self.current.get('id', '')}"

    @Slot(str, float, int, int)
    def setNotesStyle(self, color, size, column, row):
        if self._busy:
            return
        try:
            style = validate_style(color, size, column, row)
            previous = self.notesStyle
            candidate = deepcopy(self.current)
            index = find_note(candidate)
            if index is not None:
                shape = candidate['shapes'][index]
                shape.update(color=color, fs=size)
                if any(style[key] != previous[key] for key in ('size', 'column', 'row')):
                    place_notes(shape, column, row, self.info.width if self.info else 900,
                                self.info.height if self.info else 506)
            self.checkpoint()
            self.project['settings']['notesStyle'] = style
            if index is not None:
                self.clips[self.selected] = candidate
                self.touchCurrent()
            else:
                self.changed.emit()
        except ValueError as error:
            self.message(str(error))

    @Slot(str, str, result=bool)
    @Slot(str, str, str, result=bool)
    def applyNotes(self, mode, text, color=None):
        if not self.current or not self.info or self._busy:
            return False
        try:
            style = {**self.notesStyle}
            if color is not None:
                style['color'] = color
            candidate, index, created = apply_notes(self.current, text, mode, self.position,
                self.project['session'].get('offset', 0), self.duration, self.project['settings'].get('hold', 3), style)
            shape = candidate['shapes'][index]
            if created:
                place_notes(shape, style['column'], style['row'], self.info.width, self.info.height)
            self.checkpoint()
            if mode == 'freeze':
                self.stopReview()
                self.player.pause()
            self.clips[self.selected] = candidate
            self.touchCurrent()
            if mode == 'freeze':
                self.seek(shape['t'])
                self._clip_armed = True
            self.message('Notes applied at this freeze.' if mode == 'freeze' else 'Notes applied to the whole clip.')
            return True
        except (ValueError, KeyError, TypeError) as error:
            self.message(str(error))
            return False

    @Slot(result=str)
    def noteTextAtPlayhead(self):
        return self.freezeNoteAtPlayhead(True).get('text', '')

    @Slot(bool, result='QVariantMap')
    def freezeNoteAtPlayhead(self, snap):
        try:
            return freeze_note_context(self.current, self.position,
                self.project['session'].get('offset', 0), self.duration,
                self.project['settings'].get('hold', 3), snap=snap) or {}
        except (ValueError, KeyError, TypeError):
            return {}

    @Slot()
    def finishNotesEdit(self):
        self._notes_edit_id = None

    @Slot(str)
    def setNotesDraft(self, value):
        """Persist typing immediately, grouping it until focus/context changes.

        Notes draft text does not change applied shapes, so it need not rebuild
        the playback timeline. Apply still owns that separate annotation edit.
        """
        mark = self.current
        if not mark or mark.get('notes', '') == value:
            return
        if self._notes_edit_id != mark['id']:
            self.checkpoint()
            self._notes_edit_id = mark['id']
        mark['notes'] = value
        mark['u'] = max(round(time.time()*1000), mark.get('u', 0)+1)
        self.dirty = True
        self.changed.emit()


    def _playback_state_changed(self, state):
        self.changed.emit()
        if state == QMediaPlayer.PlaybackState.PausedState:
            self.notesSyncRequested.emit()

    @Property('QVariantList', notify=changed)
    def clips(self):
        return self.project['session']['marks']

    @Property('QVariantList', notify=changed)
    def clipRows(self):
        return clip_rows(self.project['session'], self._player_filter)

    @Property('QVariantList', notify=changed)
    def pads(self):
        return [{**p, 'key': TAG_KEYS[i] if i < len(TAG_KEYS) else ''} for i, p in enumerate(pads_for(self.project['session']))]

    @Property('QVariantMap', notify=changed)
    def tagSettings(self):
        session = self.project['session']
        return {'lag': session.get('tagLag', 1), 'autoEdit': session.get('autoEditNew', True),
                'player': session.get('defaultPlayer', ''), 'sort': session.get('clipSort', 'time')}

    @Property('QVariantList', notify=changed)
    def playerFilters(self):
        names = sorted({p for m in self.clips for p in players_of(m)}, key=str.casefold)
        return [{'label': 'All players', 'value': '__all'}, {'label': 'Team / unassigned', 'value': '__none'},
                *[{'label': p, 'value': p} for p in names]]

    @Property(str, notify=changed)
    def playerFilter(self):
        return self._player_filter

    @Property(str, notify=changed)
    def currentPlayers(self):
        return ', '.join(players_of(self.current))

    @Slot(str)
    def filterPlayer(self, value):
        self._player_filter = value
        self.changed.emit()

    @Slot(str)
    def sortClips(self, value):
        if value in ('time', 'player', 'category', 'kind'):
            self.checkpoint()
            self.project['session']['clipSort'] = value
            self.changed.emit()

    @Slot(float, bool, str)
    def setTagSettings(self, lag, auto_edit, player):
        if not 0 <= lag <= 5:
            return
        self.checkpoint()
        self.project['session'].update(tagLag=lag, autoEditNew=auto_edit, defaultPlayer=player.strip())
        self.changed.emit()

    @Slot()
    def editPads(self):
        dialog = PadEditor(pads_for(self.project['session']))
        if dialog.exec():
            self.checkpoint()
            self.project['session']['pads'] = dialog.result_pads
            self.changed.emit()

    @Property(int, notify=changed)
    def selection(self):
        return self.selected

    @Property('QVariantMap', notify=changed)
    def current(self):
        return self.clips[self.selected] if 0 <= self.selected < len(self.clips) else {}

    @Property('QVariantMap', notify=changed)
    def renderSettings(self):
        return {**self.project['settings'], 'lineWt': self.project['session'].get('lineWt', 1)}

    @Property(bool, notify=exportChanged)
    def busy(self):
        return self._busy

    @Property(float, notify=exportChanged)
    def progress(self):
        return self._progress

    @Slot(str)
    def message(self, message):
        self._status = message
        self.statusChanged.emit()

    def checkpoint(self):
        self.finishNotesEdit()
        self.history.append(deepcopy(self.project))
        self.history = self.history[-60:]
        self.dirty = True

    @Slot()
    def undo(self):
        if self.history and not self._busy:
            self.finishNotesEdit()
            self.cancelSlow()
            selected_id = self.current.get('id')
            self.stopReview()
            self.project = self.history.pop()
            self._notes_context_generation += 1
            self.selected = next((i for i, m in enumerate(self.clips) if m['id'] == selected_id), min(self.selected, len(self.clips)-1))
            self.dirty = True
            self.changed.emit()

    @Slot(result=bool)
    def canClose(self):
        if self._busy:
            self.message('Cancel or finish the export before closing.')
            return False
        if not self.dirty:
            return True
        choice = QMessageBox.question(None, 'Save project?', 'Save changes before continuing?',
                                      QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel)
        if choice == QMessageBox.StandardButton.Save:
            return self.save()
        return choice == QMessageBox.StandardButton.Discard

    @Slot()
    def openVideo(self):
        path, _ = QFileDialog.getOpenFileName(None, 'Open local match', str(self.root), 'Video (*.mp4 *.mov *.mkv *.avi *.webm);;All files (*)')
        if not path:
            return
        try:
            candidate, source, info = self._prepare_media(new_project(), Path(path))
            if self.canClose():
                self._activate_media(candidate, source, info, None, True)
                self.message('Match loaded. Create a clip, add a drawing, then review or export.')
        except Exception as error:
            self.message(f'Could not open match: {error}')

    def _prepare_media(self, project, path):
        """Do fallible filesystem/probe work before changing the active document."""
        source = Path(path).resolve(strict=True)
        info = probe(source, find_tool('ffprobe', self.root))
        size = source.stat().st_size
        candidate = deepcopy(project)
        candidate['media'].update({'path': str(source), 'name': source.name, 'size': size,
                                   'width': info.width, 'height': info.height, 'fps': str(info.fps)})
        # A manually relocated source must not retain a stale relative reference.
        candidate['media'].pop('relativePath', None)
        return candidate, source, info

    def _activate_media(self, project, source, info, document, dirty):
        self.finishNotesEdit()
        self.cancelSlow()
        self.stopReview()
        self.player.stop()
        self.project, self.source, self.info = project, source, info
        self._notes_context_generation += 1
        self.document = document
        self.selected = 0 if self.clips else -1
        self._clip_armed = False
        self.history.clear()
        self._player_filter = '__all'
        self._source_time = 0
        self.dirty = dirty
        self.player.setSource(QUrl.fromLocalFile(str(source)))
        self.changed.emit()
        self.positionChanged.emit()

    def load_media(self, path: Path):
        try:
            candidate, source, info = self._prepare_media(self.project, path)
            self._activate_media(candidate, source, info, self.document, True)
            self.message('Match loaded. Create a clip, add a drawing, then review or export.')
            return True
        except Exception as error:
            self.message(f'Could not open match: {error}')
            return False

    @Slot()
    def openProject(self):
        path, _ = QFileDialog.getOpenFileName(None, 'Open project or legacy marks', str(self.root / 'projects'), 'Chalkline (*.chalkline *.json)')
        if path:
            self.open_document(Path(path))

    def open_document(self, path: Path):
        try:
            path = Path(path)
            project = load_project(path)
            media = resolve_media(project, path)
            relocated = media is None
            if media is None:
                source, _ = QFileDialog.getOpenFileName(None, 'Locate footage for this project', str(self.root), 'Video (*.mp4 *.mov *.mkv *.webm)')
                if not source:
                    return False
                media = Path(source)
            candidate, source, info = self._prepare_media(project, media)
            if not self.canClose():
                return False
            native = path.suffix.lower() == '.chalkline'
            self._activate_media(candidate, source, info, path if native else None, not native or relocated)
            self.message('Project opened. Unported fields are preserved; prototype export rejects unsupported drawings.')
            return True
        except Exception as error:
            self.message(f'Could not open project: {error}')
            return False

    @Slot(result=bool)
    def save(self):
        return self._save(False)

    @Slot(result=bool)
    def saveAs(self):
        return self._save(True)

    def _save(self, choose_path):
        path = self.document
        if choose_path or not path:
            suggested = path or self.root / 'projects' / 'Match.chalkline'
            name, _ = QFileDialog.getSaveFileName(None, 'Save Chalkline project', str(suggested), 'Chalkline project (*.chalkline)')
            if not name:
                return False
            path = Path(name).with_suffix('.chalkline')
            if path != Path(name) and path.exists():
                if QMessageBox.question(None, 'Replace project?', f'Replace {path.name}?',
                                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                        QMessageBox.StandardButton.No) != QMessageBox.StandardButton.Yes:
                    return False
        try:
            save_project(self.project, path)
            self.document = path
            self.dirty = False
            self.finishNotesEdit()
            self.message(f'Saved {path.name}')
            return True
        except Exception as error:
            self.message(str(error))
            return False

    @Slot()
    def togglePlay(self):
        self._cancel_frame_resume()
        pausing = self.playing
        if self.playing:
            if self._review:
                self._review_elapsed = time.monotonic()-self._review_start
                self._review_paused = True
            self.player.pause()
        elif self._review:
            self._review_start = time.monotonic()-self._review_elapsed
            self._review_paused = False
            self._review_segment = None
            self._tick_review()
        elif self.current and self._clip_armed:
            self._begin_review(self.position)
        else:
            self.player.setPlaybackRate(self._user_rate)
            self.player.play()
        self.changed.emit()
        if pausing:
            self.notesSyncRequested.emit()

    @Slot(float)
    def seek(self, seconds):
        if not math.isfinite(seconds):
            return
        self.stopReview()
        self._clip_armed = False
        self._source_time = max(0, min(self.duration, seconds))
        self.player.setPosition(round(self._source_time*1000))
        self.positionChanged.emit()
        self.notesSyncRequested.emit()

    @Slot(int)
    def step(self, direction):
        armed = self._clip_armed
        self.seek(self.position+direction/float(self.info.fps if self.info else 30))
        self._clip_armed = armed
        self.player.pause()

    @Slot(int)
    def stepButton(self, direction):
        resume = self.playing or self._step_was_playing
        self.step(direction)
        self._step_was_playing = resume
        if resume and self.current and not self._busy:
            self.frame_resume.start()

    def _cancel_frame_resume(self):
        self.frame_resume.stop()
        self._step_was_playing = False

    def _resume_after_step(self):
        resume = self._step_was_playing
        self._step_was_playing = False
        if resume and self.current and not self._busy and not self.playing:
            self.togglePlay()

    @Slot(float)
    def skip(self, seconds):
        was_playing, armed = self.playing, self._clip_armed
        self.seek(self.position+seconds)
        if self.current and armed:
            try:
                start, end = clip_bounds(self.current, self.project['session'].get('offset', 0), self.duration)
                self._clip_armed = start <= self.position < end
            except ValueError:
                self._clip_armed = False
        self.player.pause()
        if was_playing:
            self.togglePlay()

    @Slot()
    def restartClip(self):
        if not self.current:
            return
        try:
            start, _ = clip_bounds(self.current, self.project['session'].get('offset', 0), self.duration)
            was_playing = self.playing
            self.seek(start)
            self._clip_armed = True
            self.player.pause()
            if was_playing:
                self.togglePlay()
        except ValueError as error:
            self.message(str(error))

    @Slot()
    def toggleLoop(self):
        self._loop_enabled = not self._loop_enabled
        if self._review:
            self._loop_review = self._loop_enabled
        self.changed.emit()

    @Slot(int)
    def navigateClip(self, direction):
        mark_id = adjacent_clip(self.project['session'], self._player_filter, self.current.get('id'), direction)
        if mark_id is None:
            self.message('No clips in this player filter.')
        else:
            self.selectClipId(mark_id)

    @Slot()
    def nextMarkup(self):
        point = next_markup(self.current, self.position, self.duration)
        if point is None:
            self.message('No markup on this clip yet.')
            return
        self.seek(point)
        self._clip_armed = True
        self.player.pause()

    @Slot()
    def closeClip(self):
        self.finishNotesEdit()
        self.cancelSlow()
        was_playing = self.playing
        self.stopReview()
        self.selected = -1
        self._clip_armed = False
        if was_playing:
            self.player.play()
        self.changed.emit()

    @Slot(bool)
    def playOn(self, last_clip):
        marks = self.clips if last_clip else [self.current] if self.current else []
        if not marks or not self.source:
            self.message('Pick a clip first.' if not last_clip else 'No clips tagged yet.')
            return
        offset = self.project['session'].get('offset', 0)
        endpoint = max(m['t']+offset+m.get('post', 7) for m in marks)
        if not last_clip:
            self.closeClip()
        self.seek(endpoint+.05)
        self.player.play()

    @Slot()
    def markSpot(self):
        if not self.source or self.duration <= 0:
            return
        self.checkpoint()
        clear = self.bookmark >= 0 and abs(self.bookmark-self.position) < .6
        self.project['session']['watchMark'] = None if clear else self.position
        self.changed.emit()
        self.message('Spot cleared.' if clear else 'Spot saved in this project.')

    @Slot()
    def resumeSpot(self):
        if self.bookmark < 0 or not self.source:
            return
        self.seek(self.bookmark)
        self.player.play()

    @Slot(float)
    def setRate(self, rate):
        if rate not in RATES:
            return
        self._user_rate = rate
        self._cancel_frame_resume()
        if self._review:
            paused = self._review_paused
            self._begin_review(self.position)
            if paused:
                self.togglePlay()
        else:
            self.player.setPlaybackRate(rate)
        self.changed.emit()

    @Slot(int)
    def stepRate(self, direction):
        index = min(range(len(RATES)), key=lambda i: abs(RATES[i]-self._user_rate))
        self.setRate(RATES[max(0, min(len(RATES)-1, index+direction))])

    @Slot()
    def mute(self):
        self.audio.setMuted(not self.audio.isMuted())
        self.changed.emit()
        self.message('Playback muted' if self.audio.isMuted() else 'Playback audio on')

    def _position(self, milliseconds):
        if not self._review:
            self._source_time = milliseconds/1000
            self.positionChanged.emit()

    @Slot()
    def tag(self):
        self.tagPad(0)

    @Slot(int)
    def tagPad(self, index):
        pads = pads_for(self.project['session'])
        if not 0 <= index < len(pads):
            return
        self._create_tag(pads[index], index, self.position, self.playing)

    @Slot()
    def customTag(self):
        if not self.source:
            return
        position, playing = self.position, self.playing
        label, ok = QInputDialog.getText(None, 'Custom tag', 'What is it?')
        if ok and label.strip():
            self._create_tag({'label': label.strip(), 'color': 'ball', 'pre': 6, 'post': 6, 'ask': ''}, -1, position, playing)

    def _create_tag(self, pad, index, position, playing):
        if not self.source or self._busy:
            return
        self.checkpoint()
        session = self.project['session']
        self.clips.append(make_mark(session, pad, index, position, playing, session.get('tagLag', 1)))
        if session.get('autoEditNew', True):
            self.selected = len(self.clips)-1
            self._player_filter = '__all'
            self.review()
            self._loop_review = bool(self._review) and self._loop_enabled
        self.message(f'Tagged {pad["label"]}' + (' — looping for editing.' if self._loop_review else '.'))
        self.changed.emit()

    @Slot(str)
    def selectClipId(self, mark_id):
        index = next((i for i, m in enumerate(self.clips) if m['id'] == mark_id), -1)
        self.selectClip(index)

    @Slot(str)
    def setPlayers(self, text):
        if self.current:
            self.checkpoint()
            set_players(self.current, text.split(','))
            self.touchCurrent()

    def touchCurrent(self):
        if self.current:
            self.current['u'] = max(round(time.time()*1000), self.current.get('u', 0)+1)
            if self._review:
                paused = self._review_paused
                self._begin_review(self.position)
                if paused:
                    self.togglePlay()
        self.changed.emit()

    @Slot(str)
    def setKind(self, kind):
        if self.current and kind in ('', 'highlight', 'learning'):
            self.checkpoint()
            if kind:
                self.current['kind'] = kind
            else:
                self.current.pop('kind', None)
            self.touchCurrent()

    @Slot(int)
    def recategorize(self, index):
        pads = pads_for(self.project['session'])
        if self.current and 0 <= index < len(pads):
            self.checkpoint()
            pad = pads[index]
            self.current.update({k: pad.get(k, '') for k in ('label', 'color', 'ask')})
            self.current['padIndex'] = index
            self.touchCurrent()

    @Slot()
    def deleteCurrent(self):
        if self.current and not self._busy:
            self.checkpoint()
            mark_id = self.current['id']
            self.stopReview()
            self.player.pause()
            delete_marks(self.project['session'], [mark_id])
            self.selected = -1
            self.changed.emit()
            self.message('Clip deleted. Undo restores it and its drawings.')

    @Slot()
    def clearClips(self):
        if not self.clips or self._busy:
            return
        if QMessageBox.question(None, 'Clear all clips?', 'Remove every clip and its drawings from this project? Footage is kept.',
                                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                QMessageBox.StandardButton.No) != QMessageBox.StandardButton.Yes:
            return
        self.checkpoint()
        self.stopReview()
        self.player.pause()
        delete_marks(self.project['session'], [m['id'] for m in self.clips])
        self.selected = -1
        self.changed.emit()

    @Slot(int)
    def selectClip(self, index):
        if 0 <= index < len(self.clips):
            self.finishNotesEdit()
            self._notes_context_generation += 1
            self.cancelSlow()
            self.selected = index
            self.changed.emit()
            try:
                start, _ = clip_bounds(self.current, self.project['session'].get('offset', 0), self.duration)
                self.seek(start)
                self._clip_armed = True
            except ValueError as error:
                self.stopReview()
                self.message(str(error))
            missing = {s.get('tool') for s in self.current.get('shapes', [])} - SUPPORTED_TOOLS
            if missing:
                self.message('Preserved but not drawn in prototype: '+', '.join(sorted(missing)))

    @Slot(str, str)
    def setText(self, key, value):
        if self.current and key in ('label', 'caption', 'ask', 'notes') and self.current.get(key, '') != value:
            self.checkpoint()
            self.current[key] = value
            self.touchCurrent()


    @Slot(float, float)
    def setTrim(self, before, after):
        if not self.current or self._busy:
            return
        try:
            candidate = set_trim(self.current, before, after, self.project['session'].get('offset', 0), self.duration)
            if candidate != self.current:
                self.checkpoint()
                self.clips[self.selected] = candidate
                self.touchCurrent()
        except (ValueError, KeyError, TypeError) as error:
            self.message(str(error))

    @Slot(str, float, float, float, float)
    def addShape(self, tool, ax, ay, bx, by):
        self.markup.setTool(tool)
        if self.markup.begin(ax, ay):
            self.markup.update(bx, by)
            self.markup.commit()

    @Slot()
    def addFreeze(self):
        if self.current:
            self._edit_timing('freezes', -1, {'at': self.position, 'hold': self._freeze_default})

    @Slot()
    def addSlow(self):
        if self.current:
            rate = self._user_rate if self._user_rate < 1 else self._slow_default
            self._edit_timing('slow', -1, {'from': self.position, 'to': min(self.duration, self.position+2), 'rate': rate})

    @Slot(str, int)
    def editTiming(self, kind, index):
        entries = self.slowRows if kind == 'slow' else self.freezeRows
        if kind in ('slow', 'freezes') and 0 <= index < len(entries):
            self._edit_timing(kind, index, entries[index])

    def _edit_timing(self, kind, index, values):
        if self._busy:
            return
        self.stopReview()
        self.player.pause()
        dialog = TimingEditor(kind, values, self.duration)
        if dialog.exec():
            self.updateTiming(kind, index, dialog.values())

    @Slot(str, int, 'QVariantMap', result=bool)
    def updateTiming(self, kind, index, values):
        if not self.current or self._busy:
            return False
        try:
            candidate = update_timing(self.current, kind, index, values,
                                      self.project['session'].get('offset', 0), self.duration)
            self.checkpoint()
            self.clips[self.selected] = candidate
            if kind == 'slow':
                self._slow_default = values['rate']
            else:
                self._freeze_default = values['hold']
            self.touchCurrent()
            self.message('Timing updated. Changes are included in clip review and export.')
            return True
        except (ValueError, KeyError, TypeError) as error:
            self.message(str(error))
            return False

    @Slot(str, int)
    def deleteTiming(self, kind, index):
        if not self.current or self._busy:
            return
        try:
            candidate = remove_timing(self.current, kind, index)
            self.checkpoint()
            self.clips[self.selected] = candidate
            self.touchCurrent()
        except ValueError as error:
            self.message(str(error))

    @Slot()
    def slowFrom(self):
        if not self.current:
            return
        try:
            start, end = clip_bounds(self.current, self.project['session'].get('offset', 0), self.duration)
            self._slow_pending = max(start, min(end-.1, self.position))
            self._slow_clip_id = self.current['id']
            self.changed.emit()
            self.message('Slow start set. Seek to the other end, then choose To here.')
        except ValueError as error:
            self.message(str(error))

    @Slot()
    def slowTo(self):
        if self.slowPending < 0:
            self.message('Set Slow from first.')
            return
        values = {'from': self.slowPending, 'to': self.position,
                  'rate': self._user_rate if self._user_rate < 1 else self._slow_default}
        if self.updateTiming('slow', -1, values):
            self.cancelSlow()

    @Slot()
    def cancelSlow(self):
        self._slow_pending = None
        self._slow_clip_id = None
        self.changed.emit()

    @Slot(bool, float, bool)
    def setFreezeSettings(self, auto_freeze, hold, burn_all):
        if not math.isfinite(hold) or not 0 <= hold <= 30:
            self.message('Global hold must be between 0 and 30 seconds.')
            return
        self.checkpoint()
        was_reviewing, paused = bool(self._review), self._review_paused
        self.project['settings'].update(autoFreeze=auto_freeze, hold=hold, burnAll=burn_all)
        if was_reviewing:
            self._begin_review(self.position)
            if paused:
                self.togglePlay()
        self.changed.emit()

    @Slot()
    def review(self):
        self._begin_review()

    def _begin_review(self, source_time=None):
        if not self.current:
            return
        try:
            self._cancel_frame_resume()
            self._loop_review = self._loop_enabled
            settings = self.project['settings']
            plan = plan_clip(self.current, self.project['session'].get('offset', 0), self.duration,
                             settings.get('hold', 3) if settings.get('autoFreeze', True) else 0)
            self._review = [replace(s, rate=self._user_rate) if s.kind == 'motion' and s.rate == 1 else s for s in plan]
            elapsed = review_offset(self._review, source_time) if source_time is not None else 0
            if elapsed >= sum(s.duration for s in self._review):
                elapsed = 0
            self._review_elapsed = elapsed
            self._review_paused = False
            self._clip_armed = True
            self._review_start = time.monotonic()-elapsed
            self._review_segment = None
            self._tick_review()
            self.changed.emit()
        except Exception as error:
            self.stopReview()
            self.message(str(error))

    @Slot()
    def stopReview(self):
        self._cancel_frame_resume()
        self._review = []
        self._review_paused = False
        self._loop_review = False
        self.player.setPlaybackRate(self._user_rate)
        self.changed.emit()

    def _tick_review(self):
        if not self._review or self._review_paused:
            return
        elapsed = time.monotonic()-self._review_start
        if elapsed >= sum(s.duration for s in self._review):
            if self._loop_review:
                self._review_start = time.monotonic()
                self._review_segment = None
                elapsed = 0
            else:
                self._source_time = self._review[-1].end
                self.player.setPosition(round(self._source_time*1000))
                self.player.pause()
                self.stopReview()
                self.positionChanged.emit()
                return
        segment, source_time = locate(self._review, elapsed)
        self._source_time = source_time
        if segment is not self._review_segment:
            self.player.setPosition(round(source_time*1000))
            self.player.setPlaybackRate(segment.rate)
            self.player.pause() if segment.kind == 'freeze' else self.player.play()
            self._review_segment = segment
            if segment.kind == 'freeze':
                self.notesSyncRequested.emit()
        self.positionChanged.emit()

    @Slot()
    def export(self):
        if not self.current or not self.source or self._busy:
            return
        name = f'Chalkline-{time.strftime("%Y%m%d-%H%M%S")}-4K.mp4'
        path, _ = QFileDialog.getSaveFileName(None, 'Export true 4K clip', str(self.root/'exports'/name), 'MP4 (*.mp4)')
        if not path:
            return
        try:
            self.worker = ExportWorker(self.root, self.source, deepcopy(self.current), self.project['session'].get('offset', 0),
                                       deepcopy(self.renderSettings), Path(path))
            self._export_mark_id = self.current['id']
            self.thread = QThread(self)
            self.worker.moveToThread(self.thread)
            self.thread.started.connect(self.worker.run)
            self.worker.progress.connect(self._export_progress)
            self.worker.finished.connect(self._export_finished)
            self.worker.finished.connect(self.thread.quit)
            self.thread.finished.connect(self.worker.deleteLater)
            self.thread.finished.connect(self._thread_finished)
            self._busy = True
            self._progress = 0
            self.exportChanged.emit()
            self.thread.start()
        except Exception as error:
            self.message(str(error))

    @Slot(float, str)
    def _export_progress(self, fraction, message):
        self._progress = fraction
        self.message(message)
        self.exportChanged.emit()

    @Slot(bool, str)
    def _export_finished(self, success, message):
        if success:
            for mark in self.clips:
                if mark['id'] == self._export_mark_id:
                    mark['exported'] = round(time.time()*1000)
                    self.dirty = True
            self.changed.emit()
        self.message(('Export complete: ' if success else '')+message)

    @Slot()
    def _thread_finished(self):
        self._busy = False
        self.exportChanged.emit()
        self.thread.deleteLater()
        self.thread = None
        self.worker = None

    @Slot()
    def cancelExport(self):
        if self.worker:
            self.worker.exporter.stop()
