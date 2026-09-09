"""Collect only Chalkline's native QML families.

PyInstaller's default QtQml hook collects every installed QML plugin, including
unused QtWebEngine and its 200 MB Chromium library. Module exclusions alone do
not stop that binary dependency collection.
"""
from pathlib import Path
from PyInstaller.utils.hooks.qt import add_qt6_dependencies, pyside6_library_info

hiddenimports, binaries, datas = add_qt6_dependencies(__file__)
qml_binaries, qml_datas = pyside6_library_info.collect_qtqml_files()
qml_root = Path(pyside6_library_info.location['QmlImportsPath']).resolve()


def native_family(entry):
    relative = Path(entry[0]).resolve().relative_to(qml_root)
    return relative.parts[0] in {'QtCore', 'QtQml', 'QtQuick', 'QtMultimedia'} or relative.parts[:2] == ('Qt', 'labs')


binaries += [entry for entry in qml_binaries if native_family(entry)]
datas += [entry for entry in qml_datas if native_family(entry)]
