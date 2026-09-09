from copy import deepcopy
import unittest
from unittest.mock import patch
from PySide6.QtCore import QPoint, QPointF, Qt
from PySide6.QtTest import QTest
from chalkline.domain.clip_timeline import strip_model
from chalkline.domain.timing_edits import drag_timing
from chalkline.domain.timeline import plan_clip
from chalkline.domain.project import save_project, load_project
from qml_fixture import QmlStudioTestCase, descendants


class TimingDragDomainTests(unittest.TestCase):
    def setUp(self):
        self.mark = dict(id='a',t=5,pre=2,post=7, future={'keep':1},
                         freezes=[dict(at=18,hold=2,future='manual'),dict(at=20,hold=1)],
                         slow=[dict(**{'from':16,'to':19,'rate':.25},future='zone'),
                               {'from':20,'to':22,'rate':.5}],
                         shapes=[dict(tool='text',t=18,text='Stay here',future=True),
                                 dict(tool='ground',t=18,kf=[dict(t=18,x=.2,y=.3)])])

    def test_freeze_moves_only_its_time_with_offset_snap_and_no_sort(self):
        before = deepcopy(self.mark)
        moved = drag_timing(self.mark,'freezes',0,'at',21.26,12,60)
        self.assertEqual(moved['freezes'][0],dict(at=21.3,hold=2,future='manual'))
        self.assertEqual(moved['freezes'][1],before['freezes'][1])
        self.assertEqual(moved['shapes'],before['shapes'])
        self.assertEqual(moved['slow'],before['slow'])
        self.assertEqual(moved['future'],before['future'])
        self.assertEqual(self.mark,before)
        self.assertEqual(drag_timing(self.mark,'freezes',0,'at',0,12,60)['freezes'][0]['at'],15)
        self.assertEqual(drag_timing(self.mark,'freezes',0,'at',100,12,60)['freezes'][0]['at'],24)

    def test_slow_edges_do_not_cross_or_change_other_endpoint_rate_or_order(self):
        moved = drag_timing(self.mark,'slow',0,'from',21,12,60)
        self.assertEqual(moved['slow'][0],dict(**{'from':18.9,'to':19,'rate':.25},future='zone'))
        moved = drag_timing(self.mark,'slow',0,'to',0,12,60)
        self.assertAlmostEqual(moved['slow'][0]['to'],16.1)
        self.assertEqual(moved['slow'][1],self.mark['slow'][1])
        self.assertEqual(moved['shapes'],self.mark['shapes'])

    def test_legacy_dictionary_and_partial_off_clip_endpoints_survive(self):
        self.mark['slow']=dict(**{'from':14,'to':19,'rate':.25},future='legacy')
        moved=drag_timing(self.mark,'slow',0,'to',17.12,12,60)
        self.assertIsInstance(moved['slow'],dict)
        self.assertEqual(moved['slow'],dict(**{'from':14,'to':17.1,'rate':.25},future='legacy'))

    def test_invalid_handles_nonfinite_and_impossible_intervals_are_rejected(self):
        before=deepcopy(self.mark)
        for kind,index,edge,at in [('freezes',-1,'at',18),('slow',3,'from',18),
                                   ('slow',True,'to',18),('freezes',0,'to',18),
                                   ('slow',0,'from',float('nan'))]:
            with self.assertRaises(ValueError):
                drag_timing(self.mark,kind,index,edge,at,12,60)
        self.assertEqual(self.mark,before)
        self.mark['slow'][0]['to']=14
        with self.assertRaises(ValueError):
            drag_timing(self.mark,'slow',0,'from',16,12,60)

    def test_manual_points_stay_addressable_when_playback_merges_nearby_beats(self):
        self.mark['freezes'][1]['at']=18.05
        model=strip_model(self.mark,12,60,{'hold':3})
        self.assertEqual([f['index'] for f in model['freezes']],[0,1])
        self.assertEqual(model['slow'][0]['sourceFrom'],16)
        self.assertEqual(len([s for s in plan_clip(self.mark,12,60) if s.kind=='freeze']),1)


class TimingDragUiTests(QmlStudioTestCase):
    def setUp(self):
        super().setUp()
        self.studio.current.update(freezes=[dict(at=4.5,hold=2,future=7),dict(at=9,hold=1)],
                                   slow=[{'from':7,'to':9,'rate':.25,'future':8}, {'from':10,'to':11,'rate':.5}],
                                   shapes=[{'tool':'text','t':8,'text':'Fixed time','fs':24,'a':{'x':.2,'y':.3}}])
        self.studio.changed.emit()
        self.app.processEvents()

    def item(self,name):
        return next(i for i in descendants(self.window.contentItem()) if i.objectName()==name)

    def point(self,at,lane):
        model=self.studio.clipTimeline.model
        track=self.item('clipTimelineTrack')
        p=track.mapToScene(QPointF((at-model['left'])/(model['right']-model['left'])*track.width(),lane*25+12))
        return QPoint(round(p.x()),round(p.y()))

    def press(self,at,lane):
        QTest.mousePress(self.window,Qt.MouseButton.LeftButton,Qt.KeyboardModifier.NoModifier,self.point(at,lane))

    def release(self,at,lane):
        QTest.mouseRelease(self.window,Qt.MouseButton.LeftButton,Qt.KeyboardModifier.NoModifier,self.point(at,lane))

    def test_real_freeze_drag_keeps_pointer_across_preview_rebuilds_one_undo(self):
        before=deepcopy(self.studio.current)
        model=self.studio.clipTimeline.model
        self.press(4.5,1)
        self.assertTrue(self.studio.clipTimeline.dragging)
        for at in (5,6,7,9.3):
            QTest.mouseMove(self.window,self.point(at,1))
            self.app.processEvents()
            self.assertTrue(self.studio.clipTimeline.dragging)
            self.assertTrue(self.item('timelineTimingSurface').property('pressed'))
            self.assertEqual(self.studio.current,before)
            self.assertEqual(self.studio.clipTimeline.model['left'],model['left'])
        self.release(9.3,1)
        self.assertFalse(self.studio.clipTimeline.dragging)
        self.assertAlmostEqual(self.studio.current['freezes'][0]['at'],9.3,delta=.1)
        self.assertEqual(self.studio.current['shapes'],before['shapes'])
        self.assertEqual(self.studio.current['freezes'][1],before['freezes'][1])
        self.assertEqual(len(self.studio.history),1)
        path=self.root/'Timing.chalkline'
        save_project(self.studio.project,path)
        self.assertEqual(load_project(path)['session']['marks'][0],self.studio.current)
        self.studio.undo()
        self.assertEqual(self.studio.current,before)

    def test_slow_left_and_right_handles_clamp_without_swapping_and_legacy_roundtrips(self):
        self.studio.current['slow']=self.studio.current['slow'][0]
        self.studio.changed.emit()
        self.app.processEvents()
        self.press(7,2)
        self.assertTrue(self.studio.clipTimeline.dragging)
        QTest.mouseMove(self.window,self.point(10,2))
        self.release(10,2)
        self.assertIsInstance(self.studio.current['slow'],dict)
        self.assertAlmostEqual(self.studio.current['slow']['from'],8.9)
        self.assertEqual(self.studio.current['slow']['to'],9)
        self.assertEqual(self.studio.current['slow']['future'],8)
        self.studio.undo()
        self.app.processEvents()
        self.press(9,2)
        QTest.mouseMove(self.window,self.point(6,2))
        self.release(6,2)
        self.assertAlmostEqual(self.studio.current['slow']['to'],7.1)
        self.assertEqual(self.studio.current['slow']['from'],7)

    def test_click_without_movement_is_noop_and_automatic_beat_is_not_draggable(self):
        self.studio.current['freezes'][0]['at']=4.53
        self.studio.changed.emit()
        self.app.processEvents()
        self.press(4.53,1)
        self.release(4.53,1)
        self.assertEqual(self.studio.current['freezes'][0]['at'],4.53)
        self.assertEqual(self.studio.history,[])
        self.press(8,1)
        self.assertFalse(self.studio.clipTimeline.dragging)
        self.release(8,1)
        self.assertEqual(len(self.studio.current['freezes']),2)

    def test_escape_and_selection_switch_do_not_commit_or_seek_new_clip(self):
        before=deepcopy(self.studio.clips)
        self.press(4.5,1)
        QTest.mouseMove(self.window,self.point(6,1))
        QTest.keyClick(self.window,Qt.Key.Key_Escape)
        self.release(6,1)
        self.assertEqual(self.studio.selection,0)
        self.assertEqual(self.studio.clips,before)
        self.press(4.5,1)
        target=self.point(6,1)
        self.studio.selectClip(1)
        position=self.studio.position
        QTest.mouseRelease(self.window,Qt.MouseButton.LeftButton,Qt.KeyboardModifier.NoModifier,target)
        self.assertEqual(self.studio.clips,before)
        self.assertEqual(self.studio.position,position)

    def test_other_edits_document_export_invalidate_transactions(self):
        timeline=self.studio.clipTimeline
        for invalidate in (lambda:self.studio.setKind('highlight'),
                           lambda:setattr(self.studio,'project',deepcopy(self.studio.project)),
                           lambda:setattr(self.studio,'_busy',True)):
            self.assertTrue(timeline.beginTiming('slow',0,'to'))
            timeline.preview(8)
            invalidate()
            self.studio.changed.emit()
            self.assertFalse(timeline.commit())
            self.assertEqual(self.studio.current['slow'][0]['to'],9)

    def test_double_click_opens_existing_editor_without_rounding_point(self):
        self.studio.current['freezes'][0]['at']=4.53
        self.studio.changed.emit()
        self.app.processEvents()
        with patch.object(self.studio,'editTiming') as edit:
            QTest.mouseDClick(self.window,Qt.MouseButton.LeftButton,Qt.KeyboardModifier.NoModifier,self.point(4.53,1))
            edit.assert_called_once_with('freezes',0)
        self.assertEqual(self.studio.history,[])
        self.assertFalse(self.studio.clipTimeline.dragging)
        self.assertEqual(self.studio.current['freezes'][0]['at'],4.53)


if __name__=='__main__':
    unittest.main()
