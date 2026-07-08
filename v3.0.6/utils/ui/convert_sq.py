from PyQt5.uic import loadUi
from PyQt5 import QtWidgets,QtCore
import traceback
from PyQt5.QtGui import QDoubleValidator
# from rongzai.algSvc.instrument.diffraction import calculate_material_property
from rongzai.algSvc.base import interpolate,cal_integral_normlization
from PyQt5.QtWidgets import QTableWidgetItem, QLineEdit, QCheckBox, QWidget, QHBoxLayout,QMessageBox
from utils.browse_dialog import UtilsSelectionDialog
from utils.ui.BaseUI import CollapsibleWidget
from rongzai.utils import generate_x
from rongzai.utils import get_all_from_detector
from rongzai.algSvc.base import get_sample_properties
from rongzai.utils import chebyshev
from rongzai.algSvc.base import fit_chebyshev
import numpy as np
import copy

class convert_sq(CollapsibleWidget):
    def __init__(self, name, parent):
        super(convert_sq, self).__init__(name, "utils/ui/convert_sq.ui", parent)
        self.parent = parent

        self.select_button.clicked.connect(
            lambda: self.select_data(self.select_text, [data['name'] for data in self.parent.data_list]))

        self.checkboxes = []  # 存储复选框引用
        self.delete_button.clicked.connect(self.delete_selected_rows)

        self.validator = QDoubleValidator()


    def select_data(self, lineEdit, files, parent=None):
        try:
            data_dict = {item['name']: item for item in self.parent.data_list}
            detector_dialog = UtilsSelectionDialog(files,window_title="Select Files", parent=parent)
            if detector_dialog.exec_() == QtWidgets.QDialog.Accepted:
                selected_files = detector_dialog.selectedFiles()
                lineEdit.setText('; '.join(selected_files))  # 更新 QLineEdit 控件的文本
                detectors = list(set(data_dict[file]['detector'] for file in selected_files))

                for detector in detectors:
                    # 检查文件是否已经存在于 tableWidget 中
                    file_exists = False
                    for row in range(self.tableWidget.rowCount()):
                        existing_file_item = self.tableWidget.item(row, 0)
                        if existing_file_item and existing_file_item.text() == detector:
                            file_exists = True
                            break

                    # 如果文件不存在，则添加新行
                    if not file_exists:
                        row_position = self.tableWidget.rowCount()
                        self.tableWidget.insertRow(row_position)
                        # 第1列: 文件名
                        file_item = QTableWidgetItem(detector)
                        self.tableWidget.setItem(row_position, 0, file_item)

                        group, _ = get_all_from_detector(detector, self.parent.config['base']['group_info'],
                                                         self.parent.config['base']['bank_info'])
                        # 第2-4列: 可以输入正整数的 QLineEdit
                        for col in range(1, 4):
                            int_edit = QLineEdit()
                            int_edit.setValidator(self.validator)  # 仅允许输入浮点数
                            int_edit.setText(str(self.parent.config["base"]["q_rebin"][group][col - 1]))
                            self.tableWidget.setCellWidget(row_position, col, int_edit)
                        # 第5列: 复选框
                        checkbox_widget = QWidget()
                        checkbox_layout = QHBoxLayout()
                        checkbox_layout.setContentsMargins(0, 0, 0, 0)
                        check_box = QCheckBox()
                        checkbox_layout.addWidget(check_box)
                        checkbox_layout.setAlignment(QtCore.Qt.AlignCenter)  # 居中对齐
                        checkbox_widget.setLayout(checkbox_layout)
                        self.tableWidget.setCellWidget(row_position, 4, checkbox_widget)
                        self.checkboxes.append((row_position, check_box))
        except Exception as e:
            print(f'Reason: {e}')
            import traceback
            traceback.print_exc()  # 打印异常的堆栈跟踪

    def delete_selected_rows(self):
        try:
            rows_to_remove = []

            # 第一次通过checkboxes记录要删除的数据的标志
            for row, checkbox in self.checkboxes:
                if checkbox.isChecked():
                    # 将将要删除的数据标记放入集合中
                    rows_to_remove.append(row)

            # 按降序排序以避免删除行时影响其他待删除行的索引
            rows_to_remove.sort(reverse=True)

            # 删除表格行
            for row in rows_to_remove:
                self.tableWidget.removeRow(row)

            # 更新复选框引用，重建剩余复选框的列表
            new_checkboxes = []
            for row in range(self.tableWidget.rowCount()):
                checkbox = self.tableWidget.cellWidget(row, 4).layout().itemAt(0).widget()
                new_checkboxes.append((row, checkbox))
            self.checkboxes = new_checkboxes
        except Exception as e:
            print(f'Reason: {e}')
            import traceback
            traceback.print_exc()  # 打印异常的堆栈跟踪

    def run(self):
        try:
            if self.toggle_button.isChecked():
                data_list = self.select_text.text().split('; ')
                if data_list[0] != "":
                    data_dict = {item['name']: item for item in self.parent.data_list}
                    self.check_load_text(data_list, data_dict, "Sample")
                    qrebin = self.extract_qrebin_from_table()
                    for data in data_list:
                        x, y, e = data_dict[data]["detector_focused"]["xvalue"].values[0], data_dict[data]["detector_focused"]["histogram"].values[0], data_dict[data]["detector_focused"]["error"].values[0]
                        q = 2 * np.pi / x
                        q, iq, e = q[::-1], y[::-1], e[::-1] #由于d-q是反比关系，因此转q后将数据倒序
                        q_new = generate_x(qrebin[data_dict[data]["detector"]][0], qrebin[data_dict[data]["detector"]][1],
                                           int(qrebin[data_dict[data]["detector"]][2]), "uniform") #获得rebin后的q
                        iq_new, e_new = interpolate(q, iq, e, q_new) #用插值的方法处理iq到rebin后的分布（这种做法是否合理？）

                        if "correction_info" in data_dict[data]:
                            sample_info = get_sample_properties(data_dict[data]["correction_info"])
                        else:
                            QMessageBox.warning(self, "warning in Convert S(Q)", f"the data {data} didn't make the carpenter correction, please Check! ")
                            return
                        if "v_correction" in data_dict[data]:
                            v_info = get_sample_properties(data_dict[data]["v_correction"])
                            factor = v_info["v_factor"] / sample_info["atom_num"] #这里为什么要乘V_factor
                        else:
                            QMessageBox.warning(self, "warning in Convert S(Q)", f"the data used as V in Calibration didn't make the carpenter correction, please Check! ")
                            return
                        iq_new *= factor
                        # bsqa = sample_info["b_sqrd_avg"]
                        # basq = sample_info["b_avg_sqrd"]
                        # laue = bsqa / basq
                        # iq_new = iq_new * (1 / basq) - laue + 1
                        norm = cal_integral_normlization(q_new, iq_new)
                        sq = iq_new / norm
                        err = e_new / norm
                        # if True:
                        #     qiq = (sq - 1) * q_new
                        #     cheby, npuse = chebyshev(q_new, q_new[-1],4)
                        #     qiq_cheby, y_fit = fit_chebyshev(q_new, qiq, q_new[0], cheby)
                        #     sq_cheby = (qiq_cheby / q_new) + 1
                        data_dict[data]["sq_data"] = [q_new,sq,err]
        except Exception as e:
            print(f'Reason: {e}')
            traceback.print_exc()  # 打印异常的堆栈跟踪

    def check_load_text(self,name_list,data_dict, data_class):
        for name in name_list:
            if name not in data_dict:
                QMessageBox().warning(self, "warning in Convert S(Q)",
                                f"There exists {data_class} data not loaded, please Check ")
                return
        return

    def plot_data(self):
        if self.toggle_button.isChecked():
            plot_data = []
            for data in self.parent.data_list:
                if "sq_data" in data:
                    plot_data.append({"name": f"{data['name']}",
                                      "data": copy.deepcopy(data["sq_data"]),
                                      "x_label": r'Q (Å$^{-1}$)',
                                      "y_label": "Intensity (a.u.)"
                                      })
            return plot_data
        else:
            return []

    def extract_qrebin_from_table(self):
        qrebin = {}
        num_rows = self.tableWidget.rowCount()
        for row in range(num_rows):
            # 获取第一列的文件名作为字典的 key
            detector_name = self.tableWidget.item(row, 0).text()

            # 获取第2至第4列的数值
            for col in range(1, 4):
                edit = self.tableWidget.cellWidget(row, col)
                if edit is not None:
                    try:
                        if col == 1:
                            qstart = float(edit.text())
                        elif col == 2:
                            qend = float(edit.text())
                        elif col == 3:
                            qnumber = float(edit.text())
                    except ValueError:
                        self.show_error_message(
                            f"Invalid input at row {row + 1}, column {col + 1}. Please enter a valid number.")
                        return  # Exit the function if input is invalid

            # 将值添加到字典中
            if detector_name not in qrebin:
                qrebin[detector_name] = [qstart,qend,qnumber]

        return qrebin

    def show_error_message(self, message):
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Critical)
        msg.setWindowTitle("Input Error")
        msg.setText(message)
        msg.setStandardButtons(QMessageBox.Ok)
        msg.exec_()  # Show the message box

    def save_table(self):
        """保存表格数据到 JSON 文件"""
        table_data = []
        for row in range(self.tableWidget.rowCount()):
            row_data = []
            for col in range(self.tableWidget.columnCount()):
                if col == 0:  # 处理 QTableWidgetItem
                    item = self.tableWidget.item(row, col)
                    if item is not None:
                        row_data.append({"type": "item", "value": item.text()})
                    else:
                        row_data.append({"type": "item", "value": ""})  # 空单元格
                elif col in (1, 2, 3):  # 处理 QLineEdit (第2-4列)
                    widget = self.tableWidget.cellWidget(row, col)
                    if isinstance(widget, QtWidgets.QLineEdit):
                        row_data.append({"type": "line_edit", "value": widget.text()})
                    else:
                        row_data.append({"type": "line_edit", "value": ""})  # 默认值
                elif col == 4:  # 处理 QCheckBox (第6列)
                    widget = self.tableWidget.cellWidget(row, col)
                    if isinstance(widget, QtWidgets.QWidget):  # 因为QCheckBox在QWidget容器中
                        checkbox = widget.findChild(QtWidgets.QCheckBox)
                        if checkbox:
                            row_data.append({"type": "checkbox", "value": checkbox.isChecked()})
                        else:
                            row_data.append({"type": "checkbox", "value": False})
                    else:
                        row_data.append({"type": "checkbox", "value": False})  # 默认值
            table_data.append(row_data)
        return table_data

    def load_table(self, table_data):
        """从 JSON 文件加载表格数据"""
        try:
            self.checkboxes = []
            # 设置表格的行数和列数
            self.tableWidget.setRowCount(len(table_data))
            if len(table_data) > 0:
                self.tableWidget.setColumnCount(len(table_data[0]))
            # 填充数据
            for row, row_data in enumerate(table_data):
                for col, cell_data in enumerate(row_data):
                    if cell_data["type"] == "item":  # 处理 QTableWidgetItem
                        item = QtWidgets.QTableWidgetItem(cell_data["value"])
                        self.tableWidget.setItem(row, col, item)
                    elif cell_data["type"] == "line_edit":  # 处理 QLineEdit
                        line_edit = QtWidgets.QLineEdit(cell_data["value"])
                        line_edit.setValidator(self.validator)  # 设置验证器
                        self.tableWidget.setCellWidget(row, col, line_edit)
                    elif cell_data["type"] == "checkbox":  # 处理 QCheckBox
                        checkbox_widget = QtWidgets.QWidget()
                        checkbox_layout = QtWidgets.QHBoxLayout()
                        checkbox_layout.setContentsMargins(0, 0, 0, 0)
                        check_box = QtWidgets.QCheckBox()
                        check_box.setChecked(cell_data["value"])
                        checkbox_layout.addWidget(check_box)
                        checkbox_layout.setAlignment(QtCore.Qt.AlignCenter)
                        checkbox_widget.setLayout(checkbox_layout)
                        self.tableWidget.setCellWidget(row, col, checkbox_widget)
                        self.checkboxes.append((row, check_box))
        except FileNotFoundError:
            print("Table data file not found!")
        except Exception as e:
            print(f"Error loading table data: {e}")

    def get_config(self):
        return {
            "plot": self.plot.isChecked(),
            "select_text": self.select_text.text(),
            "rebin_info": self.save_table(),
            "is_use": self.toggle_button.isChecked()
        }

    def set_config(self,config):
        """根据配置更新模块状态"""
        self.plot.setChecked(config.get("plot", False))
        self.select_text.setText(config.get("select_text", ""))
        self.load_table(config.get("rebin_info", []))
        self.toggle_button.setChecked(config.get("is_use", False))

