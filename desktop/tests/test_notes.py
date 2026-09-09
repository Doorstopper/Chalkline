from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
import os
import tempfile
import unittest

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from PySide6.QtWidgets import QApplication
from chalkline.application.studio import Studio
from chalkline.domain.notes import apply_notes, find_note, freeze_note_context
from chalkline.domain.project import new_project, save_project, load_project
from chalkline.rendering.annotations import ensure_fonts, overlay_image, check_supported
from chalkline.rendering.text_layout import measure_text, place_notes

STYLE = {'color': 'space', 'size': 24, 'column': 0, 'row': 0}


class NotesDataTests(unittest.TestCase):
    def setUp(self):
        self.mark = {'id': 'a', 't': 5, 'pre': 2, 'post': 7, 'shapes': [{'tool': 'scan', 't': 18, 'future': True}]}

    def test_nearby_freeze_snapping_and_reapply_preserve_manual_position(self):
        original = deepcopy(self.mark)
        self.mark['freezes'] = [{'at': 18, 'hold': 4}]
        result, index, created = apply_notes(self.mark, 'Look before receiving.  ', 'freeze', 18.4, 12, 60, 3, STYLE)
        self.assertTrue(created)
        self.assertEqual(result['shapes'][index]['t'], 18)
        self.assertEqual(result['shapes'][index]['linger'], 0)
        self.assertEqual(result['freezes'], [{'at': 18, 'hold': 4}])
        result['shapes'][index].update(a={'x': .3, 'y': .4}, future={'keep': 'me'}, w=.2)
        updated, again, created = apply_notes(result, 'Scan early.', 'freeze', 18.2, 12, 60, 3, STYLE)
        self.assertFalse(created)
        self.assertEqual(again, index)
        self.assertEqual(updated['shapes'][again]['a'], {'x': .3, 'y': .4})
        self.assertEqual(updated['shapes'][again]['future'], {'keep': 'me'})
        self.assertNotIn('w', updated['shapes'][again])
        self.assertEqual(updated['shapes'][0], original['shapes'][0])

    def test_whole_clip_and_different_freezes_coexist_and_roundtrip(self):
        mark, _, _ = apply_notes(self.mark, 'Whole match idea', 'clip', 20, 12, 60, 3, STYLE)
        mark, _, _ = apply_notes(mark, 'First freeze', 'freeze', 18, 12, 60, 3, STYLE)
        mark, _, _ = apply_notes(mark, 'Second freeze', 'freeze', 21, 12, 60, 0, STYLE)
        self.assertEqual(mark['shapes'][find_note(mark)]['t'], 15)
        self.assertEqual(mark['shapes'][find_note(mark, 21)]['text'], 'Second freeze')
        self.assertEqual(mark['freezes'][-1], {'at': 21, 'hold': 3})
        project = new_project()
        project['session']['marks'] = [mark]
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'notes.chalkline'
            save_project(project, path)
            self.assertEqual(load_project(path)['session']['marks'], [mark])

    def test_outside_clip_uses_offset_tag_moment_and_blank_is_rejected(self):
        mark, index, _ = apply_notes(self.mark, 'Note', 'freeze', 50, 12, 60, 3, STYLE)
        self.assertEqual(mark['shapes'][index]['t'], 17)
        with self.assertRaises(ValueError):
            apply_notes(self.mark, ' \n ', 'freeze', 18, 12, 60, 3, STYLE)

    def test_context_distinguishes_blank_freeze_and_uses_explicit_snap(self):
        mark = {'id': 'a', 't': 5, 'pre': 2, 'post': 7,
                'freezes': [{'at': 6, 'hold': 2}, {'at': 8, 'hold': 2}],
                'shapes': [{'tool': 'text', '_notes': True, 't': 6,
                            'text': 'Scan', 'color': 'space'}]}
        before = deepcopy(mark)
        self.assertEqual(freeze_note_context(mark, 6.1, 0, 60, 3)['text'], 'Scan')
        self.assertIsNone(freeze_note_context(mark, 6.4, 0, 60, 3))
        self.assertEqual(freeze_note_context(mark, 6.5, 0, 60, 3, snap=True)['at'], 6)
        self.assertIsNone(freeze_note_context(mark, 6.5001, 0, 60, 3, snap=True))
        self.assertEqual(freeze_note_context(mark, 8, 0, 60, 3)['text'], '')
        self.assertIsNone(freeze_note_context(mark, 9, 0, 60, 3, snap=True))
        self.assertEqual(mark, before)

    def test_context_uses_absolute_times_merged_stops_and_legacy_filters(self):
        mark = {'id': 'a', 't': 5, 'pre': 2, 'post': 7,
                'freezes': [{'at': 18, 'hold': 2}, {'at': 18.1, 'hold': 3},
                            {'at': 15, 'hold': 3}, {'at': 20, 'hold': 0}],
                'shapes': [{'tool': 'ground', 't': 21},
                           {'tool': 'text', '_notes': True, 't': 18.1, 'text': 'Look up'},
                           {'tool': 'text', '_notes': True, 't': 15, 'keep': 1, 'text': 'Whole'}]}
        context = freeze_note_context(mark, 18.4, 12, 60, 0, snap=True)
        self.assertEqual(context['at'], 18)
        self.assertEqual(context['text'], 'Look up')
        for at in (15, 20, 21):
            self.assertIsNone(freeze_note_context(mark, at, 12, 60, 0))


class NotesRenderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        ensure_fonts()

    def test_wrap_newlines_and_nine_positions_use_measured_dimensions(self):
        shape = {'tool': 'text', 'text': 'Scan before the ball arrives. '*8+'\nKeep your body open.', 'fs': 24, 'a': {'x': .04, 'y': .06}}
        layout = measure_text(shape, 900)
        self.assertGreater(len(layout.lines), 2)
        self.assertLessEqual(layout.width, 600)
        anchors = []
        for row in range(3):
            for col in range(3):
                note = deepcopy(shape)
                place_notes(note, col, row, 900, 506)
                anchors.append(note['a'])
                self.assertGreaterEqual(note['a']['x'], .01)
                self.assertLessEqual(note['a']['x']+measure_text(note, 900).width/900, .98)
        self.assertLess(anchors[0]['x'], anchors[1]['x'])
        self.assertLess(anchors[1]['x'], anchors[2]['x'])
        self.assertLess(anchors[0]['y'], anchors[3]['y'])
        self.assertLess(anchors[3]['y'], anchors[6]['y'])

    def test_4k_freeze_note_renders_at_beat_and_whole_clip_note_stays(self):
        mark = {'id': 'a', 't': 5, 'pre': 2, 'post': 7, 'shapes': []}
        frozen, index, _ = apply_notes(mark, 'Scan before receiving.', 'freeze', 6, 0, 60, 3, STYLE)
        place_notes(frozen['shapes'][index], 0, 0, 3840, 2160)
        check_supported(frozen)
        empty = overlay_image(3840, 2160, mark, 6, {})
        visible = overlay_image(3840, 2160, frozen, 6, {}, freezing=True)
        self.assertNotEqual(visible, empty)
        self.assertEqual(overlay_image(3840, 2160, frozen, 8, {}), empty)
        self.assertGreater(visible.pixelColor(154, 130).alpha(), 0)
        self.assertEqual(visible.pixelColor(3000, 1800).alpha(), 0)
        whole, _, _ = apply_notes(mark, 'Keep your body open.', 'clip', 6, 0, 60, 3, STYLE)
        self.assertNotEqual(overlay_image(3840, 2160, whole, 11, {}), empty)

    def test_preset_resize_roundtrip_matches_fresh_placement(self):
        for width, height in ((900, 506), (3840, 2160)):
            note = {'tool': 'text', 'text': 'Keep space', 'fs': 19,
                    'a': {'x': .04, 'y': .06}, 'future': {'preserve': True}}
            place_notes(note, 2, 0, width, height)
            small_anchor = deepcopy(note['a'])
            note['fs'] = 48
            place_notes(note, 2, 0, width, height)
            fresh = {**note, 'a': {'x': .04, 'y': .06}}
            place_notes(fresh, 2, 0, width, height)
            self.assertEqual(measure_text(note, width).lines, ['Keep space'])
            self.assertEqual(note['a'], fresh['a'])
            note['fs'] = 19
            place_notes(note, 2, 0, width, height)
            self.assertEqual(note['a'], small_anchor)
            self.assertEqual(note['future'], {'preserve': True})

    def test_all_presets_ignore_old_anchor_and_preserve_explicit_width(self):
        for width, height in ((900, 506), (3840, 2160)):
            for explicit in ({}, {'w': .4}):
                shape = {'tool': 'text', 'text': 'Keep space before receiving. '*4+'\nThen look up.',
                         'fs': 32, 'a': {'x': .04, 'y': .06}, **explicit}
                expected_lines = measure_text(shape, width).lines
                for row in range(3):
                    for column in range(3):
                        stale = {**shape, 'a': {'x': .89, 'y': .7}}
                        fresh = deepcopy(shape)
                        place_notes(stale, column, row, width, height)
                        place_notes(fresh, column, row, width, height)
                        self.assertEqual(stale['a'], fresh['a'])
                        self.assertEqual(measure_text(stale, width).lines, expected_lines)
                        if explicit:
                            self.assertEqual(stale['w'], .4)

    def test_manually_placed_text_keeps_right_edge_wrapping(self):
        note = {'tool': 'text', 'text': 'Keep space', 'fs': 48, 'a': {'x': .85, 'y': .4}}
        before = deepcopy(note)
        self.assertEqual(measure_text(note, 900).lines, ['Keep', 'space'])
        self.assertEqual(note, before)

    def test_controller_applies_once_and_undo_restores_shapes(self):
        studio = Studio(Path(tempfile.gettempdir()))
        studio.info = SimpleNamespace(duration=60, fps=30, width=3840, height=2160)
        studio.project['session']['marks'] = [{'id': 'a', 't': 5, 'pre': 2, 'post': 7, 'shapes': []}]
        studio.selected = 0
        studio._source_time = 6
        self.assertTrue(studio.applyNotes('freeze', 'Look up.'))
        self.assertEqual(studio.noteTextAtPlayhead(), 'Look up.')
        self.assertTrue(studio.applyNotes('freeze', 'Look up early.'))
        self.assertEqual(len(studio.current['shapes']), 1)
        studio.undo()
        self.assertEqual(studio.current['shapes'][0]['text'], 'Look up.')
        studio.undo()
        self.assertEqual(studio.current['shapes'], [])
        studio.timer.stop()
        studio.frame_resume.stop()
        studio.deleteLater()
        self.app.processEvents()
