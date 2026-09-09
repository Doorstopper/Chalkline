import argparse
import os
from pathlib import Path
import sys

from PySide6.QtCore import QTimer, QUrl, qInstallMessageHandler
from PySide6.QtQml import QQmlApplicationEngine, qmlRegisterType
from PySide6.QtWidgets import QApplication
from chalkline.application.studio import Studio
from chalkline.rendering.preview import AnnotationLayer
from chalkline.rendering.annotations import ensure_fonts


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('project', nargs='?')
    parser.add_argument('--root', type=Path)
    parser.add_argument('--video', type=Path)
    parser.add_argument('--smoke', action='store_true', help='Load UI and quit after three seconds')
    args = parser.parse_args()
    root = args.root or (Path(sys.executable).parent if getattr(sys, 'frozen', False) else Path('E:/Chalkline'))
    root.mkdir(parents=True, exist_ok=True)
    for name in ('projects', 'exports', 'logs', 'cache', 'temp'):
        (root/name).mkdir(exist_ok=True)
    def qt_message(kind, context, message):
        with (root/'logs'/'ui.log').open('a', encoding='utf-8') as log:
            log.write(message+'\n')
        if args.smoke:
            print(message, flush=True)
    qInstallMessageHandler(qt_message)
    os.environ.setdefault('QML_DISK_CACHE_PATH', str(root/'cache'/'qml'))
    os.environ.setdefault('QT_QUICK_CONTROLS_STYLE', 'Basic')
    app = QApplication(sys.argv[:1])
    ensure_fonts()
    app.setApplicationName('Chalkline Desktop Prototype')
    qmlRegisterType(AnnotationLayer, 'Chalkline', 1, 0, 'AnnotationLayer')
    studio = Studio(root)
    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty('studio', studio)
    engine.load(QUrl.fromLocalFile(str(Path(__file__).parent/'ui'/'Main.qml')))
    if not engine.rootObjects():
        return 1
    if args.video:
        studio.load_media(args.video)
    if args.project:
        QTimer.singleShot(100, lambda: studio.open_document(Path(args.project)))
    if args.smoke:
        QTimer.singleShot(3000, app.quit)
    result = app.exec()
    # Destroy QML objects while their context bindings still exist.
    del engine
    return result


if __name__ == '__main__':
    raise SystemExit(main())
