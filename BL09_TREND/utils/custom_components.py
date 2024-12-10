# 自定义的下拉多选框控件

from PyQt5.QtWidgets import QComboBox, QListWidget, QCheckBox, QListWidgetItem, QLineEdit, QWidget
from PyQt5.QtCore import Qt, pyqtSignal


# self defined controlbox: multi-check combobox
class XComboBox(QComboBox):
    itemChecked = pyqtSignal(list)
    _checks = []

    def __init__(self, parent) -> None:
        super().__init__(parent)
        listwgt = QListWidget(self)
        self.setView(listwgt)
        self.setModel(listwgt.model())

        lineEdit = QLineEdit(self)
        lineEdit.setReadOnly(True)
        self.setLineEdit(lineEdit)

        self.add_item('All')

    def add_item(self, text: str):
        check = QCheckBox(text, self.view())
        check.stateChanged.connect(self.on_state_changed)
        self._checks.append(check)

        item = QListWidgetItem(self.view())

        self.view().addItem(item)
        self.view().setItemWidget(item, check)

    def add_items(self, texts: list):
        for text in texts:
            self.add_item(text)

    def clear(self):
        self.view().clear()

    def get_selected(self):
        sel_data = []
        for chk in self._checks:
            if self._checks[0] == chk:
                continue
            if chk.checkState() == Qt.Checked:
                sel_data.append(chk.text())
        return sel_data

    def set_all_state(self, state):
        for chk in self._checks:
            chk.blockSignals(True)
            chk.setCheckState(Qt.CheckState(state))
            chk.blockSignals(False)

    def on_state_changed(self, state):
        if self.sender() == self._checks[0]:
            self.set_all_state(state)

        sel_data = self.get_selected()
        self.itemChecked.emit(sel_data)
        self.lineEdit().setText(';'.join(sel_data))

    def get_item_names(self):
        """
        获取所有已存在的项目名称
        :return: 项目名称列表
        """
        item_names = [chk.text() for chk in self._checks]
        return item_names