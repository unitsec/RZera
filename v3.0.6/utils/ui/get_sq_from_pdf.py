import numpy as np
from PyQt5 import QtWidgets
import traceback
import copy
from PyQt5.QtGui import QDoubleValidator, QIntValidator
from rongzai.algSvc.instrument.pdf import calculate_sq_from_PDF
from PyQt5.QtWidgets import QMessageBox
from utils.browse_dialog import UtilsSelectionDialog
from utils.ui.BaseUI import CollapsibleWidget
from rongzai.utils import generate_x


class get_sq_from_pdf(CollapsibleWidget):
    def __init__(self, parent):
        super(get_sq_from_pdf, self).__init__("Get S(Q) From PDF", "utils/ui/get_sq_from_pdf.ui", parent)
        self.parent = parent

        self.double_validator = QDoubleValidator()
        self.start.setValidator(self.double_validator)
        self.end.setValidator(self.double_validator)
        self.self_term.setValidator(self.double_validator)
        self.int_validator = QIntValidator()
        self.number.setValidator(self.int_validator)

    def select_baseData(self, lineEdit, files, parent=None):
        try:
            detector_dialog = UtilsSelectionDialog(files,window_title="Select Files", parent=parent, single_selection=True)
            if detector_dialog.exec_() == QtWidgets.QDialog.Accepted:
                selected_files = detector_dialog.selectedFiles()
                lineEdit.setText('; '.join(selected_files))  # 更新 QLineEdit 控件的文本
        except Exception as e:
            print(f'Reason: {e}')
            import traceback
            traceback.print_exc()  # 打印异常的堆栈跟踪

    def run(self):
        try:
            if self.toggle_button.isChecked():
                try:
                    q = generate_x(float(self.start.text()), float(self.end.text()), int(self.number.text()))
                except:
                    QMessageBox.warning(self, "warning", "Please check the q rebin in Get S(q) from PDF!")
                    return
                for data in self.parent.data_list:
                    if 'pdf_data' in data:
                        [r,dr] = data['pdf_data']
                        qiq = calculate_sq_from_PDF(r, dr, q)
                        sq = qiq / q + float(self.self_term.text())
                        data['sq_data'] = [q, sq, np.zeros_like(sq)]
        except Exception as e:
            print(f'Reason: {e}')
            traceback.print_exc()  # 打印异常的堆栈跟踪

    def plot_data(self):
        if self.toggle_button.isChecked():
            plot_data = []
            for data in self.parent.data_list:
                if 'pdf_data' in data and 'sq_data' in data:
                    plot_data.append({"name":f"{data['name']}",
                                      "data":copy.deepcopy(data["sq_data"]),
                                      "x_label": r'Q (Å$^{-1}$)',
                                      "y_label": "Intensity (a.u.)"
                                      })
            return plot_data
        else:
            return []

    def get_config(self):
        return {
            "is_use": self.toggle_button.isChecked(),
            "plot": self.plot.isChecked(),
            "start": self.start.text(),
            "end": self.end.text(),
            "number": self.number.text(),
            "self_term": self.self_term.text()
        }

    def set_config(self,config):
        """根据配置更新模块状态"""
        self.toggle_button.setChecked(config.get("is_use", False))
        self.plot.setChecked(config.get("plot", False))
        self.start.setText(config.get("start", ""))
        self.end.setText(config.get("end", ""))
        self.number.setText(config.get("number", ""))
        self.self_term.setText(config.get("self_term", []))

