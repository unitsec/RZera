from PyQt5.QtCore import Qt
import traceback

class checkbox_operation:
    def check_set(self, checkbox, pushbutton=None, lineedit=None, combobox=None, checkbox2=None, radiobutton=None):
        try:
            # 设置指定控件可用状态与复选框的勾选状态相同
            if pushbutton is not None:
                pushbutton.setEnabled(checkbox.isChecked())
            if lineedit is not None:
                lineedit.setEnabled(checkbox.isChecked())
                if not checkbox.isChecked():  # 如果复选框没有被选中
                    lineedit.clear()  # 将lineedit设为空
            if combobox is not None:
                combobox.setEnabled(checkbox.isChecked())
                combobox.setCurrentIndex(0)
            if radiobutton is not None:
                radiobutton.setEnabled(checkbox.isChecked())
            if checkbox2 is not None:
                checkbox2.setEnabled(checkbox.isChecked())
                if checkbox.isChecked() is False:
                    checkbox2.setChecked(False)
        except:
            traceback.print_exc()

    def check_operation(self, lineedit, filePath):
        lineedit.setText('')
        filePath.clear()

    def sync_checkboxes(self, check1, check2):
        # 获取当前状态
        check1_state = check1.isChecked()
        check2_state = check2.isChecked()

        # 同步状态
        if check1_state != check2_state:
            check1.blockSignals(True)
            check2.blockSignals(True)
            check2.setChecked(check1_state)
            check1.blockSignals(False)
            check2.blockSignals(False)

    def set_bank(self, checkbox, combo_box, lineedit, use_pushbutton=False, use_combobox=False, pushbutton=None,  combobox=None, config=None):
        lineedit.setEnabled(checkbox.isChecked()) # 设置文本输入框的可用状态与复选框的勾选状态相同
        try:
            if lineedit.isEnabled() and config is not None:
                # selected_text = combo_box.currentText()
                selected_text = 'groupBS'
                object_name = lineedit.objectName()
                if object_name.endswith('start'):
                    lineedit.setText(str(config['d_rebin'][selected_text][0]))
                elif object_name.endswith('end'):
                    lineedit.setText(str(config['d_rebin'][selected_text][1]))
                elif object_name.endswith('number'):
                    lineedit.setText(str(config['d_rebin'][selected_text][2]))
            else:
                lineedit.setText('')

            if use_pushbutton and pushbutton is None:
                raise ValueError("when use_pushbutton is True，pushbutton must be provided")
            if use_pushbutton:
                pushbutton.setEnabled(checkbox.isChecked())
            if use_combobox and combobox is None:
                raise ValueError("when use_combobox is True，combobox must be provided")
            if use_combobox:
                combobox.setEnabled(checkbox.isChecked())
        except Exception as e:
            print(f"An error occurred: {e}")
            traceback.print_exc()  # 打印异常的堆栈跟踪

    def scale_use_check(self, sambkg_check, sam_bkg_text):
        if sambkg_check.checkState() == Qt.Checked:
            sam_bkg_text.setEnabled(True)
            sam_bkg_text.setText('0.5')
            # if v_check.checkState() == Qt.Checked:
            #     v_hold_text.setEnabled(True)
            #     v_hold_text.setText('0.5')
            # else:
            #     v_hold_text.setEnabled(False)
            #     v_hold_text.setText('')
        else:
            sam_bkg_text.setEnabled(False)
            sam_bkg_text.setText('0')
            # v_hold_text.setEnabled(False)
            # v_hold_text.setText('0')