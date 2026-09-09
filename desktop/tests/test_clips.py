from copy import deepcopy
from pathlib import Path
import os
import tempfile
import unittest
from types import SimpleNamespace

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from PySide6.QtWidgets import QApplication
from chalkline.application.studio import Studio
from chalkline.domain.clips import (DEFAULT_PADS, make_mark, clip_rows, delete_marks,
                                    players_of, set_players, validate_pad)
from chalkline.domain.project import new_project, save_project, load_project
from chalkline.ui.pad_editor import PadEditor


class TagTests(unittest.TestCase):
    def test_lag_applies_only_during_playback_before_offset(self):
        session = {'offset': 12, 'defaultPlayer': '  Jamie '}
        moving = make_mark(session, DEFAULT_PADS[0], 0, .25, True, 1)
        paused = make_mark(session, DEFAULT_PADS[0], 0, .25, False, 1)
        self.assertEqual(moving['t'], -12)
        self.assertEqual(paused['t'], -11.75)
        self.assertEqual(moving['player'], 'Jamie')
        self.assertEqual(moving['ask'], DEFAULT_PADS[0]['ask'])

    def test_multiple_players_deduplicate_and_replace_legacy(self):
        mark = {'player': 'Old'}
        set_players(mark, [' Jamie ', 'jamie', 'Alex', ''])
        self.assertEqual(players_of(mark), ['Jamie', 'Alex'])
        self.assertNotIn('player', mark)

    def test_sort_filter_keep_ids_and_chronological_numbers(self):
        session = {'clipSort': 'kind', 'marks': [
            {'id': 'later', 't': 20, 'kind': 'highlight', 'players': ['Jamie', 'Alex']},
            {'id': 'first', 't': 2, 'player': 'Jamie'}, {'id': 'team', 't': 8}]}
        before = deepcopy(session)
        rows = clip_rows(session, 'jamie')
        self.assertEqual([(r['id'], r['number']) for r in rows], [('later', 3), ('first', 1)])
        self.assertEqual([r['id'] for r in clip_rows(session, '__none')], ['team'])
        self.assertEqual(session, before)

    def test_pad_validation_and_project_defaults_are_independent(self):
        a, b = new_project(), new_project()
        a['session']['pads'][0]['label'] = 'Changed'
        self.assertEqual(b['session']['pads'][0]['label'], 'On the ball')
        for value in [float('nan'), -1, float('inf')]:
            with self.assertRaises(ValueError):
                validate_pad({**DEFAULT_PADS[0], 'pre': value})

    def test_deletions_persist_without_touching_survivor_data(self):
        project = new_project()
        project['session']['marks'] = [{'id': 'a', 't': 1}, {'id': 'b', 't': 2, 'future': [1, 2]}]
        project['session']['tomb'] = ['old']
        delete_marks(project['session'], ['a', 'a'])
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'test.chalkline'
            save_project(project, path)
            session = load_project(path)['session']
        self.assertEqual(session['tomb'], ['old', 'a'])
        self.assertEqual(session['marks'], [{'id': 'b', 't': 2, 'future': [1, 2]}])


class StudioClipTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.studio = Studio(Path(tempfile.gettempdir()))
        self.studio.info = SimpleNamespace(duration=60, fps=30, width=3840, height=2160)
        self.studio.project['session']['marks'] = [
            {'id': 'a', 't': 2, 'label': 'A', 'pre': 1, 'post': 3, 'shapes': [{'tool': 'scan', 't': 2}]},
            {'id': 'b', 't': 8, 'label': 'B', 'pre': 2, 'post': 7, 'kind': 'highlight'}]

    def tearDown(self):
        self.studio.timer.stop()
        self.studio.deleteLater()
        self.app.processEvents()

    def test_selection_delete_and_undo_use_identity_after_sort(self):
        studio = self.studio
        studio.sortClips('kind')
        studio.selectClipId(studio.clipRows[0]['id'])
        self.assertEqual(studio.current['id'], 'b')
        studio.deleteCurrent()
        self.assertEqual([m['id'] for m in studio.clips], ['a'])
        self.assertEqual(studio.project['session']['tomb'], ['b'])
        studio.undo()
        self.assertEqual([m['id'] for m in studio.clips], ['a', 'b'])
        self.assertEqual(studio.project['session']['tomb'], [])

    def test_recategorizing_keeps_trim_and_unsupported_shapes(self):
        studio = self.studio
        studio.selectClipId('a')
        shapes = deepcopy(studio.current['shapes'])
        studio.recategorize(6)
        self.assertEqual(studio.current['label'], 'Attacking')
        self.assertEqual((studio.current['pre'], studio.current['post']), (1, 3))
        self.assertEqual(studio.current['shapes'], shapes)
        previous = studio.current['u']
        studio.setPlayers('Jamie, Alex, jamie')
        self.assertGreater(studio.current['u'], previous)

    def test_tag_without_auto_edit_keeps_selection_and_playhead(self):
        studio = self.studio
        studio.source = Path('fixture.mp4')
        studio.selected = 0
        studio._source_time = 20
        studio.setTagSettings(1, False, 'Jamie')
        studio.tagPad(1)
        self.assertEqual(studio.current['id'], 'a')
        self.assertEqual(studio.position, 20)
        self.assertEqual(studio.clips[-1]['label'], 'Off the ball')
        self.assertEqual(studio.clips[-1]['player'], 'Jamie')
        self.assertFalse(studio._review)

    def test_pad_dialog_cancel_is_lossless_save_preserves_unknown_fields(self):
        pads = [{**DEFAULT_PADS[0], 'future': {'value': 1}}]
        dialog = PadEditor(pads)
        dialog.table.item(0, 0).setText('Renamed')
        dialog.reject()
        self.assertEqual(pads[0]['label'], 'On the ball')
        self.assertIsNone(dialog.result_pads)
        dialog.save()
        self.assertEqual(dialog.result_pads[0]['label'], 'Renamed')
        self.assertEqual(dialog.result_pads[0]['future'], {'value': 1})
        dialog.deleteLater()


if __name__ == '__main__':
    unittest.main()
