"""Failure-path checks for staged document switching and atomic saves."""
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import os
import tempfile
import unittest

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from PySide6.QtWidgets import QApplication
from chalkline.application.studio import Studio
from chalkline.domain.project import new_project, save_project, load_project, validate_project


class DocumentSwitchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.root = Path(self.folder.name)
        self.studio = Studio(self.root)
        self.studio.project['session']['marks'] = [{'id': 'old', 't': 10, 'shapes': [{'tool': 'scan', 't': 10}]}]
        self.studio.document = self.root/'working.chalkline'
        self.studio.source = self.root/'working.mp4'
        self.studio.selected = 0
        self.studio.dirty = True
        self.studio.history = [new_project()]
        self.before = deepcopy(self.studio.project)
        self.incoming = new_project()
        self.incoming['media']['path'] = str(self.root/'incoming.mp4')
        self.incoming_path = self.root/'incoming.chalkline'
        save_project(self.incoming, self.incoming_path)
        (self.root/'incoming.mp4').write_bytes(b'fixture')

    def tearDown(self):
        self.studio.timer.stop()
        self.studio.player.stop()
        self.studio.deleteLater()
        self.app.processEvents()
        self.folder.cleanup()

    def assert_work_preserved(self):
        self.assertEqual(self.studio.project, self.before)
        self.assertEqual(self.studio.document, self.root/'working.chalkline')
        self.assertEqual(self.studio.source, self.root/'working.mp4')
        self.assertEqual(self.studio.selected, 0)
        self.assertTrue(self.studio.dirty)
        self.assertEqual(len(self.studio.history), 1)

    def test_probe_failure_never_asks_to_discard_work(self):
        with patch.object(self.studio, '_prepare_media', side_effect=ValueError('Cannot decode source')), \
             patch.object(self.studio, 'canClose') as close:
            self.assertFalse(self.studio.open_document(self.incoming_path))
            close.assert_not_called()
        self.assert_work_preserved()
        self.assertIn('Cannot decode source', self.studio.status)

    def test_new_match_probe_failure_preserves_project(self):
        with patch('chalkline.application.studio.QFileDialog.getOpenFileName', return_value=(str(self.root/'incoming.mp4'), '')), \
             patch.object(self.studio, '_prepare_media', side_effect=ValueError('Invalid video')), \
             patch.object(self.studio, 'canClose') as close:
            self.studio.openVideo()
            close.assert_not_called()
        self.assert_work_preserved()

    def test_cancel_after_successful_probe_preserves_work(self):
        prepared = (self.incoming, self.root/'incoming.mp4', SimpleNamespace(duration=60))
        with patch.object(self.studio, '_prepare_media', return_value=prepared), \
             patch.object(self.studio, 'canClose', return_value=False):
            self.assertFalse(self.studio.open_document(self.incoming_path))
        self.assert_work_preserved()

    def test_failed_save_as_does_not_change_current_document(self):
        with patch('chalkline.application.studio.QFileDialog.getSaveFileName', return_value=(str(self.root/'copy.chalkline'), '')), \
             patch('chalkline.application.studio.save_project', side_effect=OSError('Disk full')):
            self.assertFalse(self.studio.saveAs())
        self.assert_work_preserved()

    def test_prepare_is_detached_and_removes_old_relative_reference(self):
        project = deepcopy(self.incoming)
        project['media']['relativePath'] = 'old.mp4'
        before = deepcopy(project)
        info = SimpleNamespace(width=3840, height=2160, fps=30)
        with patch('chalkline.application.studio.probe', return_value=info), \
             patch('chalkline.application.studio.find_tool', return_value=Path('ffprobe.exe')):
            candidate, source, actual_info = self.studio._prepare_media(project, self.root/'incoming.mp4')
        self.assertEqual(project, before)
        self.assertNotIn('relativePath', candidate['media'])
        self.assertEqual(candidate['media']['size'], 7)
        self.assertEqual(source, (self.root/'incoming.mp4').resolve())
        self.assertIs(actual_info, info)


class DocumentValidationTests(unittest.TestCase):
    def test_duplicate_ids_and_nonfinite_times_rejected(self):
        for marks in ([{'id': 'same', 't': 1}, {'id': 'same', 't': 2}],
                      [{'id': 'a', 't': float('nan')}], [{'id': 'a', 't': 2, 'pre': -1}]):
            document = new_project()
            document['session']['marks'] = marks
            with self.assertRaises(ValueError):
                validate_project(document)

    def test_failed_atomic_replace_keeps_existing_file_and_cleans_temp(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'match.chalkline'
            original = new_project()
            save_project(original, path)
            before = path.read_bytes()
            changed = deepcopy(original)
            changed['session']['defaultPlayer'] = 'Jamie'
            with patch('chalkline.domain.project.os.replace', side_effect=OSError('Disk full')):
                with self.assertRaises(OSError):
                    save_project(changed, path)
            self.assertEqual(path.read_bytes(), before)
            self.assertEqual(load_project(path), original)
            self.assertEqual(list(Path(folder).glob('.chalkline-save-*')), [])
