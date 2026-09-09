"""Notes regressions driven through the real QML editor and shortcuts."""
from copy import deepcopy
import unittest
from unittest.mock import patch

from qml_fixture import QmlStudioTestCase, descendants
from PySide6.QtCore import Qt, QMetaObject
from PySide6.QtGui import QInputMethodEvent
from PySide6.QtMultimedia import QMediaPlayer
from PySide6.QtTest import QTest

from chalkline.domain.project import load_project


class NotesUiTests(QmlStudioTestCase):

    def type(self, text):
        for character in text:
            QTest.keyClick(self.window, Qt.Key(ord(character.upper())))
        self.app.processEvents()

    def freeze_fixture(self):
        self.studio.current.update(shapes=[
            {'tool': 'text', '_notes': True, 'text': 'First freeze', 't': 6, 'color': 'theirs',
             'a': {'x': .04, 'y': .06}, 'fs': 19, 'linger': 0},
            {'tool': 'text', '_notes': True, 'text': 'Second freeze', 't': 8, 'color': 'space',
             'a': {'x': .04, 'y': .06}, 'fs': 19, 'linger': 0},
            {'tool': 'text', '_notes': True, 'text': 'Whole clip', 't': 3, 'color': 'ours',
             'a': {'x': .04, 'y': .06}, 'fs': 19, 'keep': 1},
        ], freezes=[{'at': t, 'hold': 2} for t in (6, 8, 10)])
        self.studio.changed.emit()

    def blur_notes(self):
        button = next(item for item in descendants(self.window.contentItem())
                      if item.inherits('QQuickAbstractButton') and item.property('text') == 'Save project')
        button.forceActiveFocus()
        self.app.processEvents()
        self.assertFalse(self.edit.hasActiveFocus())

    def click_notes_button(self, text):
        # Exercise the real QML button handler even when below the scroll viewport.
        button = next(item for item in descendants(self.window.contentItem())
                      if item.inherits('QQuickAbstractButton') and item.property('text') == text)
        self.assertTrue(QMetaObject.invokeMethod(button, 'clicked'))
        self.app.processEvents()

    def test_refresh_preserves_typed_text_and_cursor(self):
        self.type('xyz')
        QTest.keyClick(self.window, Qt.Key.Key_Left)
        cursor = self.edit.property('cursorPosition')
        self.studio.mute()
        self.app.processEvents()
        self.assertEqual(self.edit.property('text'), 'Originalxyz')
        self.assertEqual(self.edit.property('cursorPosition'), cursor)
        self.assertEqual(self.studio.current['notes'], 'Originalxyz')

    def test_switch_preserves_both_drafts_without_cross_writing(self):
        self.type('x')
        self.studio.selectClip(1)
        self.app.processEvents()
        self.assertEqual(self.edit.property('text'), 'Second')
        QTest.keyClick(self.window, Qt.Key.Key_End)
        self.type('y')
        self.studio.selectClip(0)
        self.app.processEvents()
        self.assertEqual(self.edit.property('text'), 'Originalx')
        self.assertEqual([m['notes'] for m in self.studio.clips], ['Originalx', 'Secondy'])

    def test_ctrl_s_saves_focused_draft_without_extra_save_call(self):
        destination = self.root / 'focused.chalkline'
        self.studio.document = destination
        self.type(' saved')
        self.assertTrue(self.edit.hasActiveFocus())
        QTest.keyClick(self.window, Qt.Key.Key_S, Qt.KeyboardModifier.ControlModifier)
        self.app.processEvents()
        self.assertTrue(destination.exists(), 'The actual Ctrl+S shortcut must create the file')
        self.assertEqual(load_project(destination)['session']['marks'][0]['notes'], 'Original saved')
        self.assertFalse(self.studio.dirty)
        self.type(' again')
        self.assertTrue(self.studio.dirty)
        self.studio.undo()
        self.assertEqual(self.studio.current['notes'], 'Original saved')

    def test_save_while_focused_and_cancelled_close_retain_draft(self):
        self.type(' saved')
        destination = self.root / 'direct-save.chalkline'
        self.studio.document = destination
        self.assertTrue(self.studio.save())
        self.assertEqual(load_project(destination)['session']['marks'][0]['notes'], 'Original saved')
        self.type(' unsaved')
        from PySide6.QtWidgets import QMessageBox
        with patch('chalkline.application.studio.QMessageBox.question', return_value=QMessageBox.StandardButton.Cancel):
            self.assertFalse(self.studio.canClose())
        self.assertEqual(self.studio.current['notes'], 'Original saved unsaved')

    def test_typing_is_one_project_undo_step_and_does_not_rebuild_review(self):
        with patch.object(self.studio, 'touchCurrent') as touch:
            self.type(' many letters')
        self.assertEqual(len(self.studio.history), 1)
        touch.assert_not_called()
        self.window.contentItem().forceActiveFocus()
        self.app.processEvents()
        self.studio.undo()
        self.app.processEvents()
        self.assertEqual(self.edit.property('text'), 'Original')
        self.assertEqual(self.studio.current['notes'], 'Original')

    def test_multiline_paste_and_input_method_commit_are_saved(self):
        QTest.keyClick(self.window, Qt.Key.Key_Return)
        self.app.clipboard().setText('Pasted notes')
        QTest.keyClick(self.window, Qt.Key.Key_V, Qt.KeyboardModifier.ControlModifier)
        event = QInputMethodEvent()
        event.setCommitString(' caf\u00e9')
        self.app.sendEvent(self.edit, event)
        self.app.processEvents()
        self.assertEqual(self.studio.current['notes'], 'Original\nPasted notes caf\u00e9')

    def test_editor_undo_updates_draft_and_another_edit_keeps_undo_boundary(self):
        self.type('abc')
        QTest.keyClick(self.window, Qt.Key.Key_Z, Qt.KeyboardModifier.ControlModifier)
        self.app.processEvents()
        self.assertEqual(self.studio.current['notes'], self.edit.property('text'))
        self.assertEqual(self.studio.current['notes'], 'Original')
        self.type('x')
        self.studio.setKind('highlight')
        self.type('y')
        self.studio.undo()
        self.assertEqual(self.studio.current['notes'], 'Originalx')
        self.assertEqual(self.studio.current['kind'], 'highlight')
        self.studio.undo()
        self.assertNotIn('kind', self.studio.current)

    def test_apply_and_explicit_load_update_editor_without_feedback(self):
        self.type('x')
        self.studio._source_time = 6
        self.assertTrue(self.studio.applyNotes('freeze', self.edit.property('text')))
        QTest.keyClick(self.window, Qt.Key.Key_End)
        self.type(' draft')
        self.studio.setText('notes', self.studio.noteTextAtPlayhead())
        self.app.processEvents()
        self.assertEqual(self.edit.property('text'), 'Originalx')
        self.assertEqual(self.studio.current['notes'], 'Originalx')
        self.studio.closeClip()
        self.app.processEvents()
        self.assertEqual(self.edit.property('text'), '')
        self.assertEqual(self.studio.clips[0]['notes'], 'Originalx')

    def test_seeks_load_freeze_text_without_changing_saved_draft_or_shapes(self):
        self.freeze_fixture()
        original = deepcopy(self.studio.project)
        self.blur_notes()
        self.studio.seek(6)
        self.assertEqual(self.edit.property('text'), 'First freeze')
        self.studio.mute()
        self.assertEqual(self.edit.property('text'), 'First freeze')
        self.studio.seek(7)
        self.assertEqual(self.edit.property('text'), 'First freeze')
        self.studio._position(8000)  # Playback position updates alone must not reload text.
        self.assertEqual(self.edit.property('text'), 'First freeze')
        self.studio.seek(8)
        self.assertEqual(self.edit.property('text'), 'Second freeze')
        self.assertEqual(self.studio.project, original)
        self.assertEqual(self.studio.history, [])
        self.assertFalse(self.studio.dirty)
        self.studio.document = self.root / 'navigated.chalkline'
        self.assertTrue(self.studio.save())
        self.assertEqual(load_project(self.studio.document)['session']['marks'], original['session']['marks'])

    def test_automatic_loading_preserves_focused_typing(self):
        self.freeze_fixture()
        self.type(' draft')
        self.studio.seek(6)
        self.studio._playback_state_changed(QMediaPlayer.PlaybackState.PausedState)
        self.assertEqual(self.edit.property('text'), 'Original draft')
        self.assertEqual(self.studio.current['notes'], 'Original draft')
        self.blur_notes()
        self.studio.seek(6)
        self.assertEqual(self.edit.property('text'), 'First freeze')
        self.assertEqual(self.studio.current['notes'], 'Original draft')

    def test_blank_freeze_clears_only_display_and_missing_freeze_keeps_text(self):
        self.freeze_fixture()
        self.blur_notes()
        self.studio.seek(10)
        self.assertEqual(self.edit.property('text'), '')
        self.assertEqual(self.studio.current['notes'], 'Original')
        self.studio.mute()
        self.assertEqual(self.edit.property('text'), '')
        self.studio.selectClip(1)
        self.assertEqual(self.edit.property('text'), 'Second')
        self.studio.seek(23)
        self.click_notes_button('Load text at this freeze')
        self.assertEqual(self.edit.property('text'), 'Second')
        self.assertEqual(self.studio.current['notes'], 'Second')
        self.assertEqual(self.studio.history, [])

    def test_explicit_snap_loads_colour_and_apply_targets_that_freeze(self):
        self.freeze_fixture()
        self.studio.seek(6.5)  # Focus remains in notes, so only explicit Load acts.
        self.click_notes_button('Load text at this freeze')
        self.assertEqual(self.edit.property('text'), 'First freeze')
        self.assertEqual(self.studio.current['notes'], 'Original')
        self.assertEqual(self.studio.current['shapes'][2]['color'], 'ours')
        self.assertEqual(self.studio.notesStyle['color'], 'ours')
        self.assertEqual(self.studio.history, [])
        QTest.keyClick(self.window, Qt.Key.Key_End)
        self.type(' edited')
        self.click_notes_button('Apply at freeze')
        self.assertEqual(len(self.studio.current['shapes']), 3)
        self.assertEqual(self.studio.current['shapes'][0]['t'], 6)
        self.assertEqual(self.studio.current['shapes'][0]['text'], 'First freeze edited')
        self.assertEqual(self.studio.current['shapes'][0]['color'], 'theirs')
        self.assertEqual(self.studio.current['shapes'][2]['color'], 'ours')

    def test_pause_and_review_freeze_trigger_sync_without_position_polling(self):
        self.freeze_fixture()
        self.blur_notes()
        self.studio._source_time = 8
        self.studio._playback_state_changed(QMediaPlayer.PlaybackState.PausedState)
        self.assertEqual(self.edit.property('text'), 'Second freeze')
        with patch('chalkline.application.studio.time.monotonic', return_value=100):
            self.studio.review()
        with patch('chalkline.application.studio.time.monotonic', return_value=103.1):
            self.studio._tick_review()
        self.assertTrue(self.studio.playing)  # Review still runs during its automatic hold.
        self.assertEqual(self.studio.position, 6)
        self.assertEqual(self.edit.property('text'), 'First freeze')

    def test_project_undo_restores_editor_context_after_automatic_load(self):
        self.freeze_fixture()
        self.type(' draft')
        self.blur_notes()
        self.studio.seek(6)
        self.assertEqual(self.edit.property('text'), 'First freeze')
        self.studio.undo()
        self.assertEqual(self.edit.property('text'), 'Original')
        self.assertEqual(self.studio.current['notes'], 'Original')

    def test_reselecting_same_clip_restores_its_saved_draft(self):
        self.freeze_fixture()
        self.blur_notes()
        self.studio.seek(6)
        self.assertEqual(self.edit.property('text'), 'First freeze')
        self.studio.selectClip(0)
        self.assertEqual(self.edit.property('text'), 'Original')
        self.assertEqual(self.studio.current['notes'], 'Original')
        self.assertEqual(self.studio.history, [])


if __name__ == '__main__':
    unittest.main()
