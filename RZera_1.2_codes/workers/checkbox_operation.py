from PyQt5.QtCore import Qt


class checkbox_operation:
    def check_set(self, checkbox, pushbutton, lineedit, use_combobox, combobox=None):
        pushbutton.setEnabled(checkbox.isChecked())
        lineedit.setEnabled(checkbox.isChecked())
        if use_combobox and combobox is None:
            raise ValueError("when use_combobox is True，combobox must be provided")
        if use_combobox:
            combobox.setEnabled(checkbox.isChecked())

    def check_operation(self, lineedit, filePath):
        lineedit.setText('')
        filePath.clear()

    def scale_use_check(self, hold_check, v_check, sample_hold_text, v_hold_text):
        if hold_check.checkState() == Qt.Checked:
            sample_hold_text.setEnabled(True)
            sample_hold_text.setText('0.5')
            if v_check.checkState() == Qt.Checked:
                v_hold_text.setEnabled(True)
                v_hold_text.setText('0.5')
            else:
                v_hold_text.setEnabled(False)
                v_hold_text.setText('')
        else:
            sample_hold_text.setEnabled(False)
            sample_hold_text.setText('')
            v_hold_text.setEnabled(False)
            v_hold_text.setText('')