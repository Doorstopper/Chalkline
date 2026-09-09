from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import os
import tempfile
import unittest

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from PySide6.QtWidgets import QApplication
from PySide6.QtMultimedia import QMediaPlayer
from chalkline.application.studio import Studio
from chalkline.domain.transport import adjacent_clip, next_markup
from chalkline.domain.project import load_project, save_project


class FakePlayer:
    """Deterministic transport sink; no decoder timing in state-machine tests."""
    def __init__(self):
        self.state = QMediaPlayer.PlaybackState.PausedState
        self.position_ms = 0
        self.rate = 1

    def playbackState(self):
        return self.state

    def play(self):
        self.state = QMediaPlayer.PlaybackState.PlayingState

    def pause(self):
        self.state = QMediaPlayer.PlaybackState.PausedState

    def setPosition(self, value):
        self.position_ms = value

    def setPlaybackRate(self, value):
        self.rate = value


class TransportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.studio = Studio(Path(tempfile.gettempdir()))
        self.studio.player = FakePlayer()
        self.studio.source = Path('fixture.mp4')
        self.studio.info = SimpleNamespace(duration=60, fps=30, width=3840, height=2160)
        self.studio.project['session']['marks'] = [
            {'id': 'a', 't': 5, 'pre': 2, 'post': 3, 'shapes': [], 'freezes': [{'at': 5, 'hold': 2}]},
            {'id': 'b', 't': 30, 'pre': 2, 'post': 7, 'shapes': []}]
        self.studio.selected = 0

    def tearDown(self):
        self.studio.timer.stop()
        self.studio.frame_resume.stop()
        self.studio.deleteLater()
        self.app.processEvents()

    def test_navigation_is_chronological_filtered_and_clamped(self):
        session = {'clipSort': 'category', 'marks': [
            {'id': 'late', 't': 20, 'label': 'A', 'player': 'Jamie'},
            {'id': 'early', 't': 2, 'label': 'Z', 'players': ['Jamie', 'Alex']},
            {'id': 'other', 't': 10, 'label': 'B'}]}
        self.assertEqual(adjacent_clip(session, 'Jamie', None, 1), 'early')
        self.assertEqual(adjacent_clip(session, 'Jamie', 'early', 1), 'late')
        self.assertEqual(adjacent_clip(session, 'Jamie', 'late', 1), 'late')
        self.assertEqual(adjacent_clip(session, 'Jamie', 'early', -1), 'early')
        self.assertIsNone(adjacent_clip(session, 'Missing', None, 1))

    def test_bookmark_is_absolute_roundtrips_and_toggles_near_same_spot(self):
        studio = self.studio
        studio.project['session']['offset'] = 12
        studio._source_time = 24
        studio.markSpot()
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'bookmark.chalkline'
            save_project(studio.project, path)
            studio.project = load_project(path)
        studio._source_time = 2
        studio.resumeSpot()
        self.assertEqual(studio.position, 24)
        self.assertTrue(studio.playing)
        self.assertFalse(studio._clip_armed)
        studio._source_time = 24.5
        studio.markSpot()
        self.assertEqual(studio.bookmark, -1)

    def test_play_on_last_uses_furthest_end_not_list_order_or_filter(self):
        studio = self.studio
        studio.clips.reverse()
        studio.project['session']['offset'] = 12
        studio._player_filter = '__none'
        studio.playOn(True)
        self.assertAlmostEqual(studio.position, 49.05)
        self.assertTrue(studio.playing)
        self.assertFalse(studio._clip_armed)
        studio.selected = 1
        studio.playOn(False)
        self.assertAlmostEqual(studio.position, 20.05)
        self.assertEqual(studio.selected, -1)

    def test_pause_in_freeze_resumes_remaining_hold(self):
        studio = self.studio
        with patch('chalkline.application.studio.time.monotonic', return_value=100):
            studio.review()
        with patch('chalkline.application.studio.time.monotonic', return_value=102.75):
            studio._tick_review()
            studio.togglePlay()
        self.assertEqual(studio.position, 5)
        self.assertFalse(studio.playing)
        with patch('chalkline.application.studio.time.monotonic', return_value=200):
            studio._tick_review()
            studio.togglePlay()
        self.assertEqual(studio.position, 5)
        with patch('chalkline.application.studio.time.monotonic', return_value=201):
            studio._tick_review()
        self.assertEqual(studio.position, 5)
        with patch('chalkline.application.studio.time.monotonic', return_value=201.3):
            studio._tick_review()
        self.assertAlmostEqual(studio.position, 5.05)

    def test_loop_toggle_and_restart_preserve_pause(self):
        studio = self.studio
        studio.toggleLoop()
        with patch('chalkline.application.studio.time.monotonic', return_value=100):
            studio.review()
        with patch('chalkline.application.studio.time.monotonic', return_value=108):
            studio._tick_review()
        self.assertFalse(studio.playing)
        self.assertEqual(studio.position, 8)
        studio.restartClip()
        self.assertEqual(studio.position, 3)
        self.assertFalse(studio.playing)
        studio.toggleLoop()
        with patch('chalkline.application.studio.time.monotonic', return_value=200):
            studio.togglePlay()
        with patch('chalkline.application.studio.time.monotonic', return_value=208):
            studio._tick_review()
        self.assertTrue(studio.playing)
        self.assertEqual(studio.position, 3)

    def test_rate_survives_seek_and_slow_zone_overrides_user_rate(self):
        studio = self.studio
        studio.setRate(2)
        studio.seek(10)
        self.assertEqual(studio.player.rate, 2)
        studio.current['slow'] = [{'from': 6, 'to': 7, 'rate': .25}]
        studio.review()
        motion_rates = [s.rate for s in studio._review if s.kind == 'motion']
        self.assertEqual(motion_rates, [2, 2, .25, 2])

    def test_frame_buttons_schedule_resume_keyboard_steps_cancel_it(self):
        studio = self.studio
        studio.player.play()
        studio._source_time = 10
        studio.stepButton(1)
        studio.stepButton(1)
        self.assertAlmostEqual(studio.position, 10+2/30)
        self.assertFalse(studio.playing)
        self.assertTrue(studio.frame_resume.isActive())
        studio.step(-1)
        self.assertFalse(studio.frame_resume.isActive())
        studio._resume_after_step()
        self.assertFalse(studio.playing)

    def test_markup_cycles_absolute_times_and_skips_invalid_values(self):
        mark = {'shapes': [{'t': 12}, {'t': 18}, {'t': 18}, {'t': float('nan')}, {'t': 80}, {}]}
        self.assertEqual(next_markup(mark, 12, 60), 18)
        self.assertEqual(next_markup(mark, 18, 60), 12)

    def test_skip_outside_clip_continues_match_and_clamps_at_source_end(self):
        studio = self.studio
        studio._source_time = 7
        studio._clip_armed = True
        studio.player.play()
        studio.skip(20)
        self.assertEqual(studio.position, 27)
        self.assertTrue(studio.playing)
        self.assertFalse(studio._clip_armed)
        studio.skip(50)
        self.assertEqual(studio.position, 60)
