"""Native pad editor; changes are applied together only after Save."""
from copy import deepcopy
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTableWidget,
    QTableWidgetItem, QPushButton, QDialogButtonBox, QComboBox, QDoubleSpinBox,
    QMessageBox, QHeaderView)
from chalkline.domain.clips import COLORS, DEFAULT_PADS, validate_pad


class PadEditor(QDialog):
    def __init__(self, pads):
        super().__init__()
        self.setWindowTitle('Edit tag pads')
        self.resize(850, 440)
        self.original = deepcopy(pads)
        self.result_pads = None
        layout = QVBoxLayout(self)
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(['Label', 'Colour', 'Before', 'After', 'Coaching prompt'])
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table)
        actions = QHBoxLayout()
        for label, callback in [('Add pad', lambda: self.add_row({'label': 'New tag', 'color': 'ball', 'pre': 2, 'post': 7, 'ask': ''})),
                                ('Remove selected', self.remove_row), ('Reset defaults', self.reset_defaults)]:
            button = QPushButton(label)
            button.clicked.connect(callback)
            actions.addWidget(button)
        layout.addLayout(actions)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        for pad in pads:
            self.add_row(pad)

    def add_row(self, pad):
        row = self.table.rowCount()
        self.table.insertRow(row)
        item = QTableWidgetItem(pad.get('label', ''))
        item.setData(256, deepcopy(pad))
        self.table.setItem(row, 0, item)
        color = QComboBox()
        color.addItems(COLORS)
        color.setCurrentText(pad.get('color', 'ball'))
        self.table.setCellWidget(row, 1, color)
        for column, name in [(2, 'pre'), (3, 'post')]:
            seconds = QDoubleSpinBox()
            seconds.setRange(0, 3600)
            seconds.setSingleStep(.5)
            seconds.setValue(pad.get(name, 2 if name == 'pre' else 7))
            self.table.setCellWidget(row, column, seconds)
        self.table.setItem(row, 4, QTableWidgetItem(pad.get('ask', '')))

    def remove_row(self):
        if self.table.currentRow() >= 0 and self.table.rowCount() > 1:
            self.table.removeRow(self.table.currentRow())

    def reset_defaults(self):
        self.table.setRowCount(0)
        for pad in DEFAULT_PADS:
            self.add_row(pad)

    def save(self):
        try:
            pads = []
            for row in range(self.table.rowCount()):
                item = self.table.item(row, 0)
                pads.append(validate_pad({**item.data(256), 'label': item.text(),
                    'color': self.table.cellWidget(row, 1).currentText(),
                    'pre': self.table.cellWidget(row, 2).value(),
                    'post': self.table.cellWidget(row, 3).value(), 'ask': self.table.item(row, 4).text()}))
            self.result_pads = pads
            self.accept()
        except ValueError as error:
            QMessageBox.warning(self, 'Check pads', str(error))
