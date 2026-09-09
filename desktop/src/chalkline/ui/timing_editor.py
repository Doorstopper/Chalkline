from PySide6.QtWidgets import QDialog, QFormLayout, QDoubleSpinBox, QComboBox, QDialogButtonBox


class TimingEditor(QDialog):
    """One timing point per dialog, applied atomically by the controller."""
    def __init__(self, kind, values, duration):
        super().__init__()
        self.setWindowTitle('Edit freeze' if kind == 'freezes' else 'Edit slow section')
        self.setMinimumWidth(360)
        self.fields = {}
        layout = QFormLayout(self)
        fields = [('at', 'Video time (seconds)'), ('hold', 'Hold (seconds)')] if kind == 'freezes' else [
            ('from', 'Start video time (seconds)'), ('to', 'End video time (seconds)'), ('rate', 'Playback speed')]
        for key, label in fields:
            if key == 'rate':
                control = QComboBox()
                for rate in (.1, .25, .5):
                    control.addItem(f'{rate}×', rate)
                control.setCurrentIndex((.1, .25, .5).index(values.get(key, .25)))
            else:
                control = QDoubleSpinBox()
                control.setDecimals(1)
                control.setRange(.5 if key == 'hold' else 0, 30 if key == 'hold' else max(duration, values[key]))
                control.setSingleStep(.5 if key == 'hold' else .1)
                control.setValue(values[key])
            self.fields[key] = control
            layout.addRow(label, control)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def values(self):
        return {k: w.currentData() if k == 'rate' else w.value() for k, w in self.fields.items()}
