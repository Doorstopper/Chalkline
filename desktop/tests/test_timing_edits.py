from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
import os
import tempfile
import unittest

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from PySide6.QtWidgets import QApplication
from chalkline.application.studio import Studio
from chalkline.domain.timing_edits import update_timing, remove_timing, slow_zones
from chalkline.domain.timeline import freeze_stops, plan_clip
from chalkline.domain.project import save_project, load_project, new_project
from chalkline.ui.timing_editor import TimingEditor


class TimingEditTests(unittest.TestCase):
    def setUp(self):
        self.mark = {'id': 'a', 't': 5, 'pre': 2, 'post': 3, 'shapes': [{'tool': 'scan', 't': 17, 'future': True}]}

    def test_freeze_edit_is_absolute_snapped_clamped_and_preserves_fields(self):
        original = deepcopy(self.mark)
        added = update_timing(self.mark, 'freezes', -1, {'at': 17.26, 'hold': 2.3}, 12, 60)
        self.assertEqual(added['freezes'], [{'at': 17.3, 'hold': 2.5}])
        self.assertEqual(self.mark, original)
        added['freezes'][0]['future'] = {'x': 1}
        edited = update_timing(added, 'freezes', 0, {'at': 50, 'hold': 4}, 12, 60)
        self.assertEqual(edited['freezes'][0], {'at': 20, 'hold': 4, 'future': {'x': 1}})
        self.assertEqual(edited['shapes'], original['shapes'])

    def test_reversed_slow_endpoints_sort_and_legacy_single_zone_survives(self):
        self.mark['slow'] = {'from': 15, 'to': 16, 'rate': .5, 'future': 42}
        added = update_timing(self.mark, 'slow', -1, {'from': 19, 'to': 17, 'rate': .1}, 12, 60)
        self.assertEqual(added['slow'][0]['future'], 42)
        self.assertEqual(added['slow'][1], {'from': 17, 'to': 19, 'rate': .1})
        edited = update_timing(self.mark, 'slow', 0, {'from': 15, 'to': 17, 'rate': .25}, 12, 60)
        self.assertEqual(edited['slow'][0]['future'], 42)

    def test_delete_last_removes_field_and_roundtrips_other_timing(self):
        mark = update_timing(self.mark, 'slow', -1, {'from': 16, 'to': 18, 'rate': .25}, 12, 60)
        mark = update_timing(mark, 'freezes', -1, {'at': 18, 'hold': 2}, 12, 60)
        removed = remove_timing(mark, 'slow', 0)
        self.assertNotIn('slow', removed)
        project = new_project()
        project['session']['marks'] = [removed]
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'timing.chalkline'
            save_project(project, path)
            self.assertEqual(load_project(path)['session']['marks'], [removed])

    def test_invalid_or_too_short_edits_leave_input_unchanged(self):
        original = deepcopy(self.mark)
        for kind, values in [('slow', {'from': 16, 'to': 16.01, 'rate': .25}),
                             ('slow', {'from': 16, 'to': 18, 'rate': 0}),
                             ('freezes', {'at': float('nan'), 'hold': 2}),
                             ('freezes', {'at': 17, 'hold': 31})]:
            with self.assertRaises(ValueError):
                update_timing(self.mark, kind, -1, values, 12, 60)
        self.assertEqual(self.mark, original)

    def test_freezes_merge_before_clip_edge_filter_like_pwa(self):
        mark = {'shapes': [{'tool': 'arrow', 't': 3.05}], 'freezes': [{'at': 3.16, 'hold': 4}]}
        self.assertEqual(freeze_stops(mark, 3, 8, 3), [])
        mark['shapes'][0]['t'] = 4
        mark['freezes'][0]['at'] = 4.1
        self.assertEqual(freeze_stops(mark, 3, 8, 0), [(4, 4)])

    def test_sorted_overlap_keeps_first_zone_precedence_and_manual_hold(self):
        mark = update_timing(self.mark, 'slow', -1, {'from': 17, 'to': 19, 'rate': .5}, 12, 60)
        mark = update_timing(mark, 'slow', -1, {'from': 16, 'to': 18, 'rate': .25}, 12, 60)
        mark = update_timing(mark, 'freezes', -1, {'at': 18, 'hold': 2}, 12, 60)
        plan = plan_clip(mark, 12, 60, 0)
        self.assertEqual(next(s.rate for s in plan if s.start == 17 and s.kind == 'motion'), .25)
        self.assertEqual([(s.start, s.hold) for s in plan if s.kind == 'freeze'], [(18, 2)])


class TimingControllerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.studio = Studio(Path(tempfile.gettempdir()))
        self.studio.info = SimpleNamespace(duration=60, fps=30, width=3840, height=2160)
        self.studio.project['session']['marks'] = [{'id': 'a', 't': 5, 'pre': 2, 'post': 7, 'shapes': []}]
        self.studio.selected = 0

    def tearDown(self):
        self.studio.timer.stop()
        self.studio.frame_resume.stop()
        self.studio.deleteLater()
        self.app.processEvents()

    def test_in_out_rate_and_cancel_when_changing_clips(self):
        studio = self.studio
        studio._source_time = 8
        studio.slowFrom()
        studio.seek(5)
        studio.setRate(.1)
        studio.slowTo()
        self.assertEqual(studio.slowRows, [{'from': 5, 'to': 8, 'rate': .1}])
        self.assertEqual(studio.slowPending, -1)
        studio.slowFrom()
        studio.selectClip(0)
        self.assertEqual(studio.slowPending, -1)

    def test_failed_edit_creates_no_undo_entry_delete_is_undoable(self):
        studio = self.studio
        self.assertFalse(studio.updateTiming('freezes', -1, {'at': 5, 'hold': -2}))
        self.assertEqual(studio.history, [])
        self.assertTrue(studio.updateTiming('freezes', -1, {'at': 5, 'hold': 4}))
        studio.deleteTiming('freezes', 0)
        self.assertEqual(studio.freezeRows, [])
        studio.undo()
        self.assertEqual(studio.freezeRows, [{'at': 5, 'hold': 4}])

    def test_global_settings_preserve_manual_freezes_and_are_undoable(self):
        studio = self.studio
        studio.current.update(shapes=[{'tool': 'arrow', 't': 5}], freezes=[{'at': 7, 'hold': 2}])
        studio.setFreezeSettings(False, 4, True)
        studio.review()
        self.assertEqual([s.start for s in studio._review if s.kind == 'freeze'], [7])
        self.assertTrue(studio.renderSettings['burnAll'])
        studio.undo()
        self.assertTrue(studio.renderSettings['autoFreeze'])
        self.assertEqual(studio.renderSettings['hold'], 3)

    def test_native_editor_cancel_does_not_mutate_input(self):
        values = {'from': 3, 'to': 6, 'rate': .25}
        dialog = TimingEditor('slow', values, 60)
        dialog.fields['from'].setValue(4)
        dialog.fields['rate'].setCurrentIndex(2)
        self.assertEqual(dialog.values(), {'from': 4, 'to': 6, 'rate': .5})
        dialog.reject()
        self.assertEqual(values, {'from': 3, 'to': 6, 'rate': .25})
        dialog.deleteLater()
