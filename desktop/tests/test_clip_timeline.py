from copy import deepcopy
import unittest
from PySide6.QtCore import QPoint, QPointF, Qt
from PySide6.QtTest import QTest
from chalkline.domain.clip_timeline import strip_model, trim_edge
from qml_fixture import QmlStudioTestCase, descendants


class TimelineDomainTests(unittest.TestCase):
    def setUp(self):
        self.mark = {'id':'a', 't':5, 'pre':2, 'post':7, 'future':{'keep':True},
                     'shapes':[{'tool':'text','t':18,'future':123}],
                     'freezes':[{'at':18,'hold':2}], 'slow':{'from':19,'to':21,'rate':.25,'future':True}}

    def test_trim_uses_offset_and_preserves_absolute_annotations(self):
        before = deepcopy(self.mark)
        result = trim_edge(self.mark, 'end', 20.3, 12, 60)
        self.assertEqual(result['post'], 3.5)
        for key in ('shapes','freezes','slow','future'):
            self.assertEqual(result[key], before[key])
        self.assertEqual(self.mark, before)

    def test_handles_clamp_to_source_and_keep_valid_tag_window(self):
        mark = {'id':'a','t':5,'pre':2,'post':0}
        result = trim_edge(mark, 'start', 100, 0, 60)
        self.assertGreater(result['pre'], 0)
        result = trim_edge(mark, 'start', -100, 0, 60)
        self.assertEqual(result['pre'], 5)
        result = trim_edge(mark, 'end', 100, 0, 60)
        self.assertEqual(result['post'], 55)
        with self.assertRaises(ValueError):
            trim_edge(mark, 'end', float('nan'), 0, 60)

    def test_strip_marks_outside_trim_are_dimmed_and_legacy_slow_keeps_index(self):
        trimmed = trim_edge(self.mark, 'end', 17.5, 12, 60)
        model = strip_model(trimmed,12,60,{'hold':3},window=(13,25))
        self.assertEqual(model['slow'][0]['index'], 0)
        self.assertFalse(model['slow'][0]['active'])
        self.assertFalse(model['freezes'][0]['active'])
        self.assertFalse(model['marks'][0]['active'])
        self.assertIsInstance(trimmed['slow'], dict)
        self.assertEqual(strip_model({},0,0,{}), {})


class TimelineUiTests(QmlStudioTestCase):
    def item(self, name):
        return next(i for i in descendants(self.window.contentItem()) if i.objectName()==name)

    def point(self, item, x=None, y=None):
        p = item.mapToScene(item.boundingRect().center()) if x is None else item.mapToScene(QPointF(x,y))
        return QPoint(round(p.x()),round(p.y()))

    def begin_drag(self):
        self.app.processEvents()
        self.track = self.item('clipTimelineTrack')
        handle = self.item('trim-end')
        self.origin = self.point(handle)
        self.target = self.origin-QPoint(round(self.track.width()*.1),0)
        self.assertGreater(self.track.width(),100)
        self.assertLess(self.origin.y(),self.window.height())
        QTest.mousePress(self.window,Qt.MouseButton.LeftButton,Qt.KeyboardModifier.NoModifier,self.origin)
        self.assertTrue(self.studio.clipTimeline.dragging)
        QTest.mouseMove(self.window,self.target)
        self.app.processEvents()

    def test_mouse_drag_holds_scale_and_commits_one_lossless_undo_step(self):
        self.studio.current.update(shapes=[{'tool':'arrow','t':8,'a':{'x':.1,'y':.1},'b':{'x':.2,'y':.2}}],
                                   freezes=[{'at':8,'hold':2}], slow={'from':9,'to':11,'rate':.25})
        self.studio.changed.emit()
        before = deepcopy(self.studio.current)
        model = self.studio.clipTimeline.model
        self.begin_drag()
        self.assertEqual(self.studio.current,before)
        self.assertEqual(self.studio.history,[])
        self.assertEqual(self.studio.clipTimeline.model['left'],model['left'])
        self.assertEqual(self.studio.clipTimeline.model['right'],model['right'])
        QTest.mouseRelease(self.window,Qt.MouseButton.LeftButton,Qt.KeyboardModifier.NoModifier,self.target)
        self.assertFalse(self.studio.clipTimeline.dragging)
        self.assertLess(self.studio.current['post'],before['post'])
        self.assertEqual(len(self.studio.history),1)
        for key in ('shapes','freezes','slow'):
            self.assertEqual(self.studio.current[key],before[key])
        self.studio.undo()
        self.assertEqual(self.studio.current,before)

    def test_escape_cancels_drag_without_closing_clip(self):
        before = deepcopy(self.studio.current)
        self.begin_drag()
        QTest.keyClick(self.window,Qt.Key.Key_Escape)
        self.app.processEvents()
        QTest.mouseRelease(self.window,Qt.MouseButton.LeftButton,Qt.KeyboardModifier.NoModifier,self.target)
        self.assertFalse(self.studio.clipTimeline.dragging)
        self.assertEqual(self.studio.selection,0)
        self.assertEqual(self.studio.current,before)
        self.assertEqual(self.studio.history,[])

    def test_selection_change_during_drag_cannot_write_to_either_clip(self):
        before = deepcopy(self.studio.clips)
        self.begin_drag()
        self.studio.selectClip(1)
        QTest.mouseRelease(self.window,Qt.MouseButton.LeftButton,Qt.KeyboardModifier.NoModifier,self.target)
        self.assertEqual(self.studio.clips,before)
        self.assertFalse(self.studio.clipTimeline.dragging)

    def test_other_edit_and_busy_state_cancel_pending_trim(self):
        timeline = self.studio.clipTimeline
        timeline.begin('end')
        timeline.preview(9)
        self.studio.setKind('highlight')
        self.assertFalse(timeline.commit())
        self.assertEqual(self.studio.current['post'],7)
        self.assertEqual(self.studio.current['kind'],'highlight')
        timeline.begin('start')
        self.studio._busy=True
        self.studio.exportChanged.emit()
        self.assertFalse(timeline.dragging)
        self.assertFalse(timeline.begin('end'))

    def test_track_click_seeks_without_reselecting_and_panels_are_grouped(self):
        self.app.processEvents()
        track = self.item('clipTimelineTrack')
        model = self.studio.clipTimeline.model
        point = self.point(track,track.width()*.75,track.height()-2)
        QTest.mouseClick(self.window,Qt.MouseButton.LeftButton,Qt.KeyboardModifier.NoModifier,point)
        expected = model['left']+.75*(model['right']-model['left'])
        self.assertAlmostEqual(self.studio.position,expected,delta=.06)
        self.assertEqual(self.studio.selection,0)
        titles = {i.property('title') for i in descendants(self.window.contentItem()) if i.inherits('QQuickGroupBox')}
        self.assertEqual(titles,{'Clip details','Coaching notes','Freeze & slow motion','Drawing tools','Export'})

    def test_document_replacement_cancels_drag_and_nudge_is_undoable(self):
        timeline = self.studio.clipTimeline
        timeline.begin('end')
        timeline.preview(9)
        self.studio.project = deepcopy(self.studio.project)
        self.studio.changed.emit()
        self.assertFalse(timeline.commit())
        timeline.nudge('end',-.5)
        self.assertEqual(self.studio.current['post'],6.5)
        self.studio.undo()
        self.assertEqual(self.studio.current['post'],7)


    def test_numeric_trim_rejects_empty_clip_and_noop_without_undo(self):
        before = deepcopy(self.studio.current)
        self.studio.setTrim(0,0)
        self.assertEqual(self.studio.current,before)
        self.studio.setTrim(2,7)
        self.assertEqual(self.studio.history,[])

    def test_minimum_window_keeps_grouped_controls_inside_and_more_preserves_video(self):
        self.window.setWidth(1050)
        self.window.setHeight(720)
        QTest.qWait(100)
        for name in ('playbackPanel', 'clipTimeline', 'clipInspector'):
            panel = self.item(name)
            origin = panel.mapToScene(QPointF(0, 0))
            self.assertGreaterEqual(origin.x(), 0, name)
            self.assertLessEqual(origin.x() + panel.width(), self.window.width(), name)
        viewport = self.item('videoViewport')
        height = viewport.height()
        self.assertGreater(height, 70)
        self.item('playbackPanel').setProperty('expanded', True)
        QTest.qWait(100)
        self.assertEqual(viewport.height(), height)


if __name__ == '__main__':
    unittest.main()
