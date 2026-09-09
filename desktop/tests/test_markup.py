from copy import deepcopy
from unittest.mock import patch
import unittest
from PySide6.QtCore import QPointF, QPoint, Qt, QMetaObject
from PySide6.QtTest import QTest
from chalkline.domain.markup import TOOLS, make_shape, point, edit_shape, move_shape
from chalkline.domain.project import save_project, load_project
from chalkline.rendering.annotations import check_supported, overlay_image, alpha_at
from qml_fixture import QmlStudioTestCase, descendants


class MarkupDomainTests(unittest.TestCase):
    def test_creation_geometry_and_timing_match_existing_renderer(self):
        a, b = point(.2,.3), point(.6,.7)
        for tool in TOOLS:
            shape = make_shape(tool,a,b,17,'ours',24,[a,point(.4,.2),b],'Coach')
            check_supported({'shapes':[shape]})
            self.assertEqual(shape['t'],17)
            self.assertEqual(shape['linger'],0)
            if tool == 'zone':
                self.assertEqual(len(shape['pts']),4)
            if tool == 'pen':
                self.assertEqual(len(shape['pts']),3)
        self.assertEqual(point(-1,2), {'x':0,'y':1})

    def test_edits_preserve_unknown_fields_and_keep_linger_exclusivity(self):
        shape = dict(tool='text',t=12,keep=1,text='Coach',fs=24,a=point(.2,.3),future={'x':1})
        before = deepcopy(shape)
        updated = edit_shape(shape,'linger',2,60)
        self.assertNotIn('keep',updated)
        self.assertEqual(updated['future'],shape['future'])
        self.assertEqual(alpha_at(updated,13,3,False),1)
        updated = edit_shape(updated,'keep',True,60)
        self.assertNotIn('linger',updated)
        self.assertEqual(updated['t'],12)
        self.assertEqual(shape,before)
        for key,value in [('t',61),('t',float('nan')),('linger',-1),('fs',200),('text',''),('color','invalid')]:
            with self.assertRaises(ValueError):
                edit_shape(shape,key,value,60)

    def test_movement_clamps_as_one_shape_and_keeps_keyframe_times(self):
        shape = dict(tool='ground', a=point(.9,.9), b=point(.95,.95),r=.03,
                     kf=[dict(t=10,x=.9,y=.9,future=1),dict(t=12,x=.95,y=.95)],future=True)
        result = move_shape(shape,.2,.2)
        self.assertAlmostEqual(result['a']['x'],.95)
        self.assertEqual(result['kf'][-1]['x'],1)
        self.assertEqual([k['t'] for k in result['kf']],[10,12])
        self.assertEqual(shape['a']['x'],.9)
        self.assertEqual(result['kf'][0]['future'],1)


class MarkupUiTests(QmlStudioTestCase):
    def item(self, name):
        return next(i for i in descendants(self.window.contentItem()) if i.objectName()==name)

    def source_point(self, x, y):
        surface = self.item('markupSurface')
        p = surface.mapToScene(QPointF(surface.width()*x,surface.height()*y))
        return QPoint(round(p.x()),round(p.y()))

    def begin_stroke(self, tool='pen'):
        self.studio.markup.setTool(tool)
        self.app.processEvents()
        QTest.mousePress(self.window,Qt.MouseButton.LeftButton,Qt.KeyboardModifier.NoModifier,self.source_point(.2,.3))
        QTest.mouseMove(self.window,self.source_point(.4,.6))
        QTest.mouseMove(self.window,self.source_point(.6,.4))

    def test_real_stroke_is_transient_and_commits_once_with_pen_points(self):
        before = deepcopy(self.studio.current)
        self.begin_stroke()
        self.assertTrue(self.studio.markup.drawing)
        self.assertEqual(self.studio.current,before)
        self.assertEqual(self.studio.history,[])
        self.assertEqual(len(self.studio.markup.preview['shapes']),1)
        QTest.mouseRelease(self.window,Qt.MouseButton.LeftButton,Qt.KeyboardModifier.NoModifier,self.source_point(.6,.4))
        shape = self.studio.current['shapes'][0]
        self.assertEqual(shape['tool'],'pen')
        self.assertGreaterEqual(len(shape['pts']),3)
        self.assertEqual(len(self.studio.history),1)
        self.studio.undo()
        self.assertEqual(self.studio.current,before)
        self.assertEqual(self.studio.markup.selection,-1)

    def test_escape_cancels_without_closing_clip_and_selection_switch_cannot_cross_write(self):
        before = deepcopy(self.studio.clips)
        self.begin_stroke('arrow')
        QTest.keyClick(self.window,Qt.Key.Key_Escape)
        QTest.mouseRelease(self.window,Qt.MouseButton.LeftButton,Qt.KeyboardModifier.NoModifier,self.source_point(.6,.4))
        self.assertEqual(self.studio.selection,0)
        self.assertEqual(self.studio.clips,before)
        self.begin_stroke('zone')
        self.studio.selectClip(1)
        QTest.mouseRelease(self.window,Qt.MouseButton.LeftButton,Qt.KeyboardModifier.NoModifier,self.source_point(.6,.4))
        self.assertEqual(self.studio.clips,before)

    def test_seek_document_edit_and_export_cancel_stale_strokes(self):
        editor = self.studio.markup
        editor.setTool('line')
        for invalidate in (
            lambda: self.studio.seek(6),
            lambda: self.studio.setKind('highlight'),
            lambda: setattr(self.studio,'project',deepcopy(self.studio.project)),
            lambda: setattr(self.studio,'_busy',True),
        ):
            editor.begin(.1,.2)
            editor.update(.5,.6)
            invalidate()
            self.studio.changed.emit()
            editor.commit()
            self.assertEqual(self.studio.current['shapes'],[])
            self.assertFalse(editor.drawing)

    def test_selected_edit_duplicate_delete_and_roundtrip_preserve_other_shapes(self):
        original = dict(tool='text',t=5,text='Original',fs=24,a=point(.2,.3),linger=0,future={'keep':1})
        unsupported = dict(tool='specialist',future=True,t=8)
        self.studio.current['shapes']=[original,unsupported]
        self.studio.changed.emit()
        editor = self.studio.markup
        editor.select(0)
        editor.setColor('theirs')
        editor.edit('linger',4)
        editor.setSize(30)
        with patch('chalkline.application.markup.QInputDialog.getMultiLineText',return_value=('Edited',True)):
            editor.editText()
        editor.move(.1,0)
        selected = deepcopy(editor.selected)
        self.assertEqual(selected['future'],original['future'])
        self.assertEqual(selected['t'],5)
        self.assertAlmostEqual(selected['a']['x'],.3)
        self.assertTrue(QMetaObject.invokeMethod(self.item('markupDuplicate'),'clicked'))
        self.assertEqual(self.studio.current['shapes'][-1],selected)
        self.assertTrue(QMetaObject.invokeMethod(self.item('markupDelete'),'clicked'))
        self.assertEqual(len(self.studio.current['shapes']),2)
        self.assertEqual(self.studio.current['shapes'][1],unsupported)
        destination = self.root/'Markup.chalkline'
        save_project(self.studio.project,destination)
        self.assertEqual(load_project(destination)['session']['marks'][0],self.studio.current)
        with self.assertRaises(ValueError):
            check_supported(self.studio.current)

    def test_text_cancel_is_lossless_and_late_dialog_cannot_write_to_new_clip(self):
        editor = self.studio.markup
        editor.setTool('text')
        editor.begin(.2,.2)
        with patch('chalkline.application.markup.QInputDialog.getMultiLineText',return_value=('',False)):
            editor.commit()
        self.assertEqual(self.studio.history,[])
        editor.begin(.2,.2)
        def switch(*args):
            self.studio.selectClip(1)
            return 'Late text',True
        with patch('chalkline.application.markup.QInputDialog.getMultiLineText',side_effect=switch):
            editor.commit()
        self.assertTrue(all(m['shapes']==[] for m in self.studio.clips))

    def test_all_palette_tools_create_renderable_shapes_at_4k_and_weight_undo(self):
        editor = self.studio.markup
        for tool in TOOLS:
            self.assertTrue(QMetaObject.invokeMethod(self.item('markup-tool-'+tool),'clicked'))
            self.assertEqual(editor.tool,tool)
            editor.begin(.2,.3)
            editor.update(.6,.7)
            with patch('chalkline.application.markup.QInputDialog.getMultiLineText',return_value=('Coach',True)):
                editor.commit()
            shape = self.studio.current['shapes'][-1]
            check_supported({'shapes':[shape]})
            image = overlay_image(3840,2160,{'shapes':[shape]},shape['t'],self.studio.renderSettings,True)
            self.assertFalse(image.isNull())
            # Pixel alpha proves each tool actually drew, rather than merely allocating an image.
            self.assertTrue(any(image.pixelColor(x,y).alpha()>0 for x in range(700,2500,4) for y in range(550,1600,4)))
        editor.setWeight(2)
        self.assertEqual(self.studio.renderSettings['lineWt'],2)
        self.studio.undo()
        self.assertEqual(self.studio.renderSettings['lineWt'],1)

    def test_fullscreen_surface_retains_pan_without_creating_markup(self):
        self.studio.markup.setTool('arrow')
        self.window.setProperty('immersive',True)
        self.window.setProperty('zoom',2)
        self.app.processEvents()
        QTest.mousePress(self.window,Qt.MouseButton.LeftButton,Qt.KeyboardModifier.NoModifier,self.source_point(.5,.5))
        QTest.mouseMove(self.window,self.source_point(.6,.5))
        QTest.mouseRelease(self.window,Qt.MouseButton.LeftButton,Qt.KeyboardModifier.NoModifier,self.source_point(.6,.5))
        self.assertNotEqual(self.window.property('panX'),0)
        self.assertEqual(self.studio.current['shapes'],[])


if __name__ == '__main__':
    unittest.main()
