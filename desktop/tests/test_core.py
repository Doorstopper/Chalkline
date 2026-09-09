from pathlib import Path
import json
import tempfile
import unittest
import zipfile
from chalkline.domain.project import import_legacy, load_project, save_project, resolve_media
from chalkline.domain.timeline import clip_bounds, plan_clip, locate, freeze_stops


class ProjectTests(unittest.TestCase):
    def test_legacy_roundtrip_preserves_unknown_fields_and_absolute_times(self):
        legacy = {'offset': 12, 'pads': [], 'tomb': ['deleted'], 'futureField': {'x': [1, 2]},
                  'marks': [{'id': 'm1', 't': 5, 'pre': 2, 'post': 7,
                             'shapes': [{'tool': 'scan', 't': 17, 'spread': 1.5, '_notes': True}],
                             'slow': [{'from': 18, 'to': 20, 'rate': .25}]}]}
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'match.chalkline'
            save_project(import_legacy(legacy), path)
            self.assertEqual(load_project(path)['session'], legacy)

    def test_media_relative_path_survives_folder_move(self):
        with tempfile.TemporaryDirectory() as folder:
            first = Path(folder)/'first'
            first.mkdir()
            video = first/'match.mp4'
            video.write_bytes(b'fixture')
            project = import_legacy({'marks': []})
            project['media']['path'] = str(video)
            save_project(project, first/'match.chalkline')
            second = Path(folder)/'second'
            first.rename(second)
            self.assertEqual(resolve_media(load_project(second/'match.chalkline'), second/'match.chalkline'), (second/'match.mp4').resolve())

    def test_unknown_version_rejected_without_writing(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'future.chalkline'
            with zipfile.ZipFile(path, 'w') as archive:
                archive.writestr('project.json', json.dumps({'format':'chalkline', 'schemaVersion':999}))
            original = path.read_bytes()
            with self.assertRaises(ValueError):
                load_project(path)
            self.assertEqual(path.read_bytes(), original)


class TimelineTests(unittest.TestCase):
    def test_offset_only_applies_to_tag_time(self):
        mark = {'t':5, 'pre':2, 'post':3, 'freezes':[{'at':17, 'hold':2}],
                'slow':[{'from':18, 'to':20, 'rate':.5}]}
        self.assertEqual(clip_bounds(mark, 12, 100), (15,20))
        plan = plan_clip(mark,12,100)
        self.assertEqual([s.start for s in plan if s.kind=='freeze'], [17])
        self.assertAlmostEqual(sum(s.duration for s in plan),9)
        self.assertEqual(locate(plan,3)[1],17)
        self.assertAlmostEqual(locate(plan,6)[1],18.5)

    def test_nearby_freezes_merge_longest_hold(self):
        mark={'t':5, 'shapes':[{'tool':'arrow','t':5,'keep':1}], 'freezes':[{'at':5.1,'hold':4}]}
        self.assertEqual(freeze_stops(mark,0,10,3),[(5,4)])

    def test_disabled_auto_freeze_keeps_manual_freezes(self):
        mark={'t':5,'pre':2,'post':3,'shapes':[{'tool':'arrow','t':4}], 'freezes':[{'at':6,'hold':1}]}
        self.assertEqual([s.start for s in plan_clip(mark,0,20,0) if s.kind=='freeze'],[6])

    def test_ground_keyframes_do_not_create_freezes(self):
        self.assertEqual(freeze_stops({'t':5,'shapes':[{'tool':'ground','t':5}]},0,10,3),[])

    def test_invalid_rate_rejected(self):
        with self.assertRaises(ValueError):
            plan_clip({'t':5,'pre':2,'post':2,'slow':[{'from':3,'to':4,'rate':0}]},0,20)

    def test_clip_clamps_to_source(self):
        self.assertEqual(clip_bounds({'t':1,'pre':4,'post':20},0,10),(0,10))

    def test_fractional_boundaries_preserved(self):
        plan=plan_clip({'t':1.001,'pre':.1,'post':.1},0,10)
        self.assertAlmostEqual(sum(s.duration for s in plan),.2)


if __name__ == '__main__':
    unittest.main()
