## Patch

The confirmed defect is the declarative binding `text: studio.current.notes || ""`: it is re-evaluated on **every** `changed` emission, so `mute()` (and play/pause, loop, seek, selection, export progress…) reassigns the field and destroys an uncommitted draft. The fix makes the field's text a draft that is assigned only when the clip or its stored notes genuinely change.

```diff
--- a/desktop/src/chalkline/ui/NotesPanel.qml
+++ b/desktop/src/chalkline/ui/NotesPanel.qml
@@ -8,10 +8,25 @@
     Label { text: "NOTES"; color: "#9DAFC2"; font.pixelSize: 11 }
     TextArea {
         id: notes
-        text: studio.current.notes || ""; placeholderText: "Write coaching notes…"
+        // The field holds a draft the coach owns. Reload it only when the clip
+        // or its stored notes really change: a plain binding was reevaluated on
+        // every changed signal (mute, play, seek) and wiped typing in progress.
+        property string clipId: studio.current.id || ""
+        property string stored: studio.current.notes || ""
+        function reload() { text = studio.current.notes || "" }
+        function commit() { studio.setText("notes",text) }
+        placeholderText: "Write coaching notes…"
         Layout.fillWidth: true; wrapMode: TextEdit.Wrap
         enabled: studio.selection>=0
-        onActiveFocusChanged: if (!activeFocus) studio.setText("notes",text)
+        Component.onCompleted: reload()
+        onClipIdChanged: reload()
+        onStoredChanged: reload()
+        onActiveFocusChanged: if (!activeFocus) commit()
+        // Ctrl+S / Ctrl+Shift+S never move focus, so flush the draft here and
+        // leave the event unaccepted so Main.qml's save shortcut still runs.
+        Keys.onShortcutOverride: function (event) {
+            if (event.key === Qt.Key_S && (event.modifiers & Qt.ControlModifier)) commit()
+        }
     }
     RowLayout {
         ComboBox {
@@ -44,5 +44,5 @@
     }
     Button { text: "Apply at freeze"; Layout.fillWidth: true; enabled: studio.selection>=0 && !studio.busy; onClicked: studio.applyNotes("freeze",notes.text) }
     Button { text: "Apply to whole clip"; Layout.fillWidth: true; enabled: studio.selection>=0 && !studio.busy; onClicked: studio.applyNotes("clip",notes.text) }
-    Button { text: "Load text at this freeze"; Layout.fillWidth: true; enabled: studio.selection>=0; onClicked: studio.setText("notes",studio.noteTextAtPlayhead()) }
+    Button { text: "Load text at this freeze"; Layout.fillWidth: true; enabled: studio.selection>=0; onClicked: { studio.setText("notes",studio.noteTextAtPlayhead()); notes.reload() } }
 }
```

```diff
--- /dev/null
+++ b/desktop/tests/test_notes_ui.py
@@ -0,0 +1,125 @@
+"""QML notes checks: real key input into the panel, offscreen, no media.
+
+A draft in the notes field must survive unrelated changed signals, must never
+follow the user to another clip, and must reach the document when Ctrl+S fires
+while the field still holds focus.
+"""
+from pathlib import Path
+from types import SimpleNamespace
+import os
+import tempfile
+import unittest
+
+os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
+os.environ.setdefault('QT_QUICK_BACKEND', 'software')
+os.environ.setdefault('QT_QUICK_CONTROLS_STYLE', 'Basic')
+from PySide6.QtCore import Qt, QUrl
+from PySide6.QtQml import QQmlApplicationEngine, qmlRegisterType
+from PySide6.QtTest import QTest
+from PySide6.QtWidgets import QApplication
+import chalkline
+from chalkline.application.studio import Studio
+from chalkline.domain.project import load_project
+from chalkline.rendering.annotations import ensure_fonts
+from chalkline.rendering.preview import AnnotationLayer
+
+MAIN_QML = Path(chalkline.__file__).resolve().parent/'ui'/'Main.qml'
+
+
+def descendants(item):
+    yield item
+    for child in item.childItems():
+        yield from descendants(child)
+
+
+class NotesDraftTests(unittest.TestCase):
+    """The panel owns the unsaved draft; the document owns committed notes."""
+
+    @classmethod
+    def setUpClass(cls):
+        cls.app = QApplication.instance() or QApplication([])
+        ensure_fonts()
+        qmlRegisterType(AnnotationLayer, 'Chalkline', 1, 0, 'AnnotationLayer')
+
+    def setUp(self):
+        self.folder = tempfile.TemporaryDirectory()
+        self.root = Path(self.folder.name)
+        self.studio = Studio(self.root)
+        self.studio.timer.stop()  # no wall-clock review ticks in a UI test
+        self.studio.info = SimpleNamespace(duration=60, fps=30, width=3840, height=2160)
+        self.studio.project['session']['marks'] = [
+            {'id': 'a', 't': 5, 'pre': 2, 'post': 7, 'label': 'A', 'notes': 'Original', 'shapes': []},
+            {'id': 'b', 't': 30, 'pre': 2, 'post': 7, 'label': 'B', 'notes': 'Second', 'shapes': []}]
+        self.studio.selected = 0
+        self.engine = QQmlApplicationEngine()
+        self.engine.rootContext().setContextProperty('studio', self.studio)
+        self.engine.load(QUrl.fromLocalFile(str(MAIN_QML)))
+        self.window = self.engine.rootObjects()[0]
+        self.app.processEvents()
+        self.notes = self.field('Write coaching')
+
+    def tearDown(self):
+        self.studio.timer.stop()
+        self.studio.frame_resume.stop()
+        self.studio.player.stop()
+        self.notes = self.window = None
+        self.engine = None  # QML objects must go before the studio they bind to
+        self.app.processEvents()
+        self.studio.deleteLater()
+        self.app.processEvents()
+        self.folder.cleanup()
+
+    def field(self, placeholder):
+        return next(item for item in descendants(self.window.contentItem())
+                    if str(item.property('placeholderText')).startswith(placeholder))
+
+    def type_draft(self):
+        """Type one real key into the focused notes field, as a coach would."""
+        self.notes.forceActiveFocus()
+        self.window.requestActivate()
+        self.app.processEvents()
+        QTest.keyClick(self.window, Qt.Key.Key_End)
+        QTest.keyClick(self.window, Qt.Key.Key_X)
+        self.app.processEvents()
+        self.assertEqual(self.notes.property('text'), 'Originalx')
+
+    def test_unrelated_refresh_keeps_the_draft_and_focus_loss_stores_it(self):
+        self.type_draft()
+        self.studio.mute()
+        self.studio.toggleLoop()
+        self.app.processEvents()
+        self.assertEqual(self.notes.property('text'), 'Originalx')
+        self.assertEqual(self.studio.current['notes'], 'Original')
+        self.field('Clip label').forceActiveFocus()
+        self.app.processEvents()
+        self.assertEqual(self.studio.current['notes'], 'Originalx')
+
+    def test_switching_clips_reloads_and_never_leaks_the_draft(self):
+        self.type_draft()
+        self.studio.selectClipId('b')
+        self.app.processEvents()
+        self.assertEqual(self.notes.property('text'), 'Second')
+        self.field('Clip label').forceActiveFocus()
+        self.app.processEvents()
+        self.assertEqual(self.studio.clips[1]['notes'], 'Second')
+        self.assertEqual(self.studio.clips[0]['notes'], 'Original')
+
+    def test_model_changes_such_as_load_at_playhead_reach_the_field(self):
+        self.notes.forceActiveFocus()
+        self.window.requestActivate()
+        self.app.processEvents()
+        self.studio.setText('notes', 'Loaded at the freeze')
+        self.app.processEvents()
+        self.assertEqual(self.notes.property('text'), 'Loaded at the freeze')
+
+    def test_ctrl_s_while_focused_flushes_and_saves_the_draft(self):
+        self.studio.document = self.root/'notes.chalkline'
+        self.type_draft()
+        QTest.keyClick(self.window, Qt.Key.Key_S, Qt.KeyboardModifier.ControlModifier)
+        self.app.processEvents()
+        # The panel flushes on the shortcut override; Main.qml still owns the save.
+        self.assertEqual(self.studio.current['notes'], 'Originalx')
+        self.assertEqual(self.notes.property('text'), 'Originalx')
+        self.assertTrue(self.studio.save())
+        saved = load_project(self.studio.document)
+        self.assertEqual(saved['session']['marks'][0]['notes'], 'Originalx')
```

## Why this shape

- **`stored`/`clipId` intermediaries.** Both stay bound to the model, but a QML property only emits its change signal when the value actually differs. `mute()` re-evaluates both bindings to the same strings, so no handler runs and the draft (and cursor position) is untouched. When notes really change — undo, Apply, Load, a clip switch — `reload()` assigns the model value. Both handlers read `studio.current` directly rather than the sibling property, so binding evaluation order can't matter.
- **Cursor/typing behaviour.** Typing never touches the model, so nothing reassigns `text`. After `commit()`, `stored` changes and `reload()` assigns an identical string; `QQuickTextEdit::setText` returns early on equal text, so the cursor and selection survive a Ctrl+S mid-sentence.
- **Ctrl+S.** Window `Shortcut` items don't move focus, so focus-out alone would let Save write stale notes. `Keys.onShortcutOverride` is delivered to the focus item *before* shortcut matching; committing there and leaving `event.accepted` false lets `Main.qml:50` run `studio.save()` on the already-committed text. Matching on `Qt.Key_S` + `Qt.ControlModifier` covers Ctrl+S and Ctrl+Shift+S in one condition.
- **Load button.** Now that the field no longer follows the model unconditionally, `setText` alone is invisible when the loaded text equals what is already stored, so the button explicitly calls `reload()`. Behaviour is otherwise unchanged (including the pre-existing empty-result clearing, which belongs to the separate finding).
- **No Studio change.** Everything above is reachable from the panel, so I didn't propose one.

## Residual, deliberately not fixed here

Clicking a clip in the strip does not move focus (`Main.qml:128` is a plain `MouseArea`), so an uncommitted draft is discarded when the selection changes — the last assertion in `test_switching_clips_reloads_and_never_leaks_the_draft` pins that down. It is not corrupted or written to the wrong clip, which is the requirement you set. Preserving it needs a `setTextForClip(id, key, value)` slot on `Studio` so the panel can flush to the clip it was editing; that is the follow-up, outside this task.

I did not run the tests, the QML, or any command — the patch above is proposed only.
