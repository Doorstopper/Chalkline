"""Shared native window fixture for QML interaction regressions."""
from pathlib import Path
from types import SimpleNamespace
import os
import tempfile
import unittest

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
os.environ.setdefault('QT_QUICK_BACKEND', 'software')
os.environ.setdefault('QT_QUICK_CONTROLS_STYLE', 'Basic')
from PySide6.QtCore import Qt, QUrl
from PySide6.QtQml import QQmlApplicationEngine, qmlRegisterType
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
import shiboken6

from chalkline.application.studio import Studio
from chalkline.rendering.annotations import ensure_fonts
from chalkline.rendering.preview import AnnotationLayer


def descendants(item):
    yield item
    for child in item.childItems():
        yield from descendants(child)


class QmlStudioTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        ensure_fonts()
        qmlRegisterType(AnnotationLayer, 'Chalkline', 1, 0, 'AnnotationLayer')

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.studio = Studio(self.root)
        self.studio.timer.stop()
        self.studio.info = SimpleNamespace(duration=60, fps=30, width=3840, height=2160)
        self.studio.project['session']['marks'] = [
            {'id': 'a', 't': 5, 'pre': 2, 'post': 7, 'label': 'A', 'notes': 'Original', 'shapes': []},
            {'id': 'b', 't': 20, 'pre': 2, 'post': 7, 'label': 'B', 'notes': 'Second', 'shapes': []},
        ]
        self.studio.selected = 0
        self.engine = QQmlApplicationEngine()
        self.engine.rootContext().setContextProperty('studio', self.studio)
        self.engine.load(QUrl.fromLocalFile(str(Path(__file__).resolve().parents[1] / 'src/chalkline/ui/Main.qml')))
        self.assertTrue(self.engine.rootObjects())
        self.window = self.engine.rootObjects()[0]
        self.edit = next(item for item in descendants(self.window.contentItem())
                         if str(item.property('placeholderText')).startswith('Write coaching'))
        self.window.requestActivate()
        self.edit.forceActiveFocus()
        self.app.processEvents()
        QTest.keyClick(self.window, Qt.Key.Key_End)

    def tearDown(self):
        self.studio.timer.stop()
        self.studio.frame_resume.stop()
        shiboken6.delete(self.engine)  # Context/Studio must outlive QML destruction.
        shiboken6.delete(self.studio)
        self.app.processEvents()
        self.temp.cleanup()

