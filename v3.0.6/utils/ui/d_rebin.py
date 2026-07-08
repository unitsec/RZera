from PyQt5.uic import loadUi
from PyQt5 import QtWidgets,QtCore
from PyQt5.QtGui import QDoubleValidator
from utils.ui.BaseUI import CollapsibleWidget
from utils.browse_dialog import UtilsSelectionDialog
from PyQt5.QtWidgets import QTableWidgetItem, QLineEdit, QCheckBox, QWidget, QHBoxLayout, QComboBox
from rongzai.algSvc.neutron import rebin_neutron_data
from rongzai.utils import generate_x
from rongzai.utils import get_all_from_detector
import copy,traceback

class d_rebin(CollapsibleWidget):
    def __init__(self, parent):
        super(d_rebin, self).__init__("d Rebin", "utils/ui/d_rebin.ui", parent)
        self.parent = parent

        self.add_button.clicked.connect(self.add_rebin)
        self.add_default.clicked.connect(self.add_default_rebin)

        self.checkboxes = []  # 存储复选框引用
        self.delete_button.clicked.connect(self.delete_selected_rows)

        self.validator = QDoubleValidator()

    def run(self):
        try:
            if self.toggle_button.isChecked():
                drebin,rebin_mode = self.extract_drebin_from_table()
                for data in self.parent.data_list:
                    if data['detector'] in drebin.keys():
                        if rebin_mode[data['detector']] == "deltaX_X":
                            dvalue = generate_x(float(drebin[data['detector']][0]), float(drebin[data['detector']][1]),
                                                float(drebin[data['detector']][2]), rebin_mode[data['detector']])
                        else:
                            dvalue = generate_x(float(drebin[data['detector']][0]), float(drebin[data['detector']][1]),
                                                int(drebin[data['detector']][2]), rebin_mode[data['detector']])
                        data['detector_focused'] = rebin_neutron_data(data['detector_focused'], dvalue)
                        data["record"]["d_rebin"] = drebin[data['detector']]
        except Exception as e:
            print(f'Reason: {e}')
            import traceback
            traceback.print_exc()  # 打印异常的堆栈跟踪

    def plot_data(self):
        if self.toggle_button.isChecked():
            plot_data = []
            for data in self.parent.data_list:
                if "detector_focused" in data:
                    plot_data.append({"name": f"{data['name']}",
                                      "data": [copy.deepcopy(data["detector_focused"]["xvalue"].values[0]),
                                               copy.deepcopy(data["detector_focused"]["histogram"].values[0]),
                                               copy.deepcopy(data["detector_focused"]["error"].values[0])],
                                      "x_label": "d (Å)",
                                      "y_label": "Intensity (a.u.)"})
            return plot_data
        else:
            return []

    def extract_drebin_from_table(self):
        drebin = {}
        combobox_choices = {}  # 新增的字典，用于存储ComboBox选择
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
                            dstart = float(edit.text())
                        elif col == 2:
                            dend = float(edit.text())
                        elif col == 3:
                            dnumber = float(edit.text())
                    except ValueError:
                        self.show_error_message(
                            f"Invalid input at row {row + 1}, column {col + 1}. Please enter a valid number.")
                        return None, None  # 返回两个None表示出错

            # 获取第5列的ComboBox选择（列索引4）
            combo_box = self.tableWidget.cellWidget(row, 4)
            if combo_box is not None:
                combo_choice = combo_box.currentText()
            else:
                combo_choice = "uniform"  # 默认值

            # 将值添加到字典中
            if detector_name not in drebin:
                drebin[detector_name] = [dstart, dend, dnumber]
                combobox_choices[detector_name] = combo_choice

        return drebin, combobox_choices  # 返回两个字典

    def add_rebin(self):
        try:
            detector_set = set()
            # 使用 for 循环将每个 data['detector'] 添加到集合，集合会自动去重
            for data in self.parent.data_list:
                detector_set.add(data['detector'])
            # 将集合转换为列表
            detectors = list(detector_set)
            selected_detectors = self.select_detectors(detectors)
            self.add_row(selected_detectors)
        except Exception as e:
            print(f'Reason: {e}')
            traceback.print_exc()  # 打印异常的堆栈跟踪

    def add_default_rebin(self):
        try:
            detector_set = set()
            # 使用 for 循环将每个 data['detector'] 添加到集合，集合会自动去重
            for data in self.parent.data_list:
                detector_set.add(data['detector'])
            # 将集合转换为列表
            detectors = list(detector_set)
            selected_detectors = self.select_detectors(detectors)
            self.add_default_rows(selected_detectors)
        except Exception as e:
            print(f'Reason: {e}')
            traceback.print_exc()  # 打印异常的堆栈跟踪

    def select_detectors(self, detectors, parent=None):
        detector_dialog = UtilsSelectionDialog(detectors, window_title="Select Detectors", parent=parent)
        if detector_dialog.exec_() == QtWidgets.QDialog.Accepted:
            selected_files = detector_dialog.selectedFiles()
            return selected_files
        else:
            return []

    def add_row(self, selected_files):
        for file in selected_files:
            # 检查文件是否已经存在于 tableWidget 中
            file_exists = False
            for row in range(self.tableWidget.rowCount()):
                existing_file_item = self.tableWidget.item(row, 0)
                if existing_file_item and existing_file_item.text() == file:
                    file_exists = True
                    break

            # 如果文件不存在，则添加新行
            if not file_exists:
                row_position = self.tableWidget.rowCount()
                self.tableWidget.insertRow(row_position)

                # 第1列: 文件名
                file_item = QTableWidgetItem(file)
                self.tableWidget.setItem(row_position, 0, file_item)

                # 第2-4列: 可以输入浮点数的 QLineEdit
                for col in range(1, 4):
                    int_edit = QLineEdit()
                    int_edit.setValidator(self.validator)  # 仅允许输入浮点数
                    self.tableWidget.setCellWidget(row_position, col, int_edit)

                # 第5列: ComboBox
                combo_box = QComboBox()
                combo_box.addItems(["uniform", "log_10", "log_e", "deltaX_X"])
                combo_box.setCurrentIndex(0)  # 默认选择第一个选项
                # 存储combo box的引用以便后续访问
                # self.combo_boxes.append((row_position, combo_box))
                self.tableWidget.setCellWidget(row_position, 4, combo_box)

                # 第6列: 复选框
                checkbox_widget = QWidget()
                checkbox_layout = QHBoxLayout()
                checkbox_layout.setContentsMargins(0, 0, 0, 0)
                check_box = QCheckBox()
                checkbox_layout.addWidget(check_box)
                checkbox_layout.setAlignment(QtCore.Qt.AlignCenter)  # 居中对齐
                checkbox_widget.setLayout(checkbox_layout)
                self.tableWidget.setCellWidget(row_position, 5, checkbox_widget)
                self.checkboxes.append((row_position, check_box))  # 存储复选框引用

    def add_default_rows(self, selected_files):
        for file in selected_files:
            # 检查文件是否已经存在于 tableWidget 中
            file_exists = False
            for row in range(self.tableWidget.rowCount()):
                existing_file_item = self.tableWidget.item(row, 0)
                if existing_file_item and existing_file_item.text() == file:
                    file_exists = True
                    break

            # 如果文件不存在，则添加新行
            if not file_exists:
                row_position = self.tableWidget.rowCount()
                self.tableWidget.insertRow(row_position)

                # 第1列: 文件名
                file_item = QTableWidgetItem(file)
                self.tableWidget.setItem(row_position, 0, file_item)

                group, _ = get_all_from_detector(file, self.parent.config['base']['group_info'],
                                                       self.parent.config['base']['bank_info'])
                # 第2-4列: 可以输入浮点数的 QLineEdit
                for col in range(1, 4):
                    int_edit = QLineEdit()
                    int_edit.setValidator(self.validator)  # 仅允许输入浮点数
                    try:
                        int_edit.setText(str(self.parent.config["base"]["d_rebin"][file][col-1]))
                    except:
                        int_edit.setText(str(self.parent.config["base"]["d_rebin"][group][col - 1]))
                    self.tableWidget.setCellWidget(row_position, col, int_edit)

                # 第5列: ComboBox
                combo_box = QComboBox()
                combo_box.addItems(["uniform", "log_10", "log_e", "deltaX_X"])
                try:
                    combo_box.setCurrentText(self.parent.config["base"]["d_rebin"]["mode"])  # 默认选择第一个选项
                except:
                    combo_box.setCurrentIndex(0)  # 默认选择第一个选项
                # 存储combo box的引用以便后续访问
                # self.combo_boxes.append((row_position, combo_box))
                self.tableWidget.setCellWidget(row_position, 4, combo_box)

                # 第6列: 复选框
                checkbox_widget = QWidget()
                checkbox_layout = QHBoxLayout()
                checkbox_layout.setContentsMargins(0, 0, 0, 0)
                check_box = QCheckBox()
                checkbox_layout.addWidget(check_box)
                checkbox_layout.setAlignment(QtCore.Qt.AlignCenter)  # 居中对齐
                checkbox_widget.setLayout(checkbox_layout)
                self.tableWidget.setCellWidget(row_position, 5, checkbox_widget)
                self.checkboxes.append((row_position, check_box))  # 存储复选框引用

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
                checkbox = self.tableWidget.cellWidget(row, 5).layout().itemAt(0).widget()
                new_checkboxes.append((row, checkbox))
            self.checkboxes = new_checkboxes
        except Exception as e:
            print(f'Reason: {e}')
            import traceback
            traceback.print_exc()  # 打印异常的堆栈跟踪

    def get_config(self):
        return {
            "is_use": self.toggle_button.isChecked(),
            "plot": self.plot.isChecked(),
            "rebin_info": self.save_table(),
        }

    def set_config(self,config):
        """根据配置更新模块状态"""
        self.plot.setChecked(config.get("plot", False))
        self.load_table(config.get("rebin_info", []))
        self.toggle_button.setChecked(config.get("is_use", False))

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
                elif col == 4:  # 处理 QComboBox (第5列)
                    widget = self.tableWidget.cellWidget(row, col)
                    if isinstance(widget, QtWidgets.QComboBox):
                        row_data.append({
                            "type": "combobox",
                            "value": widget.currentText(),
                            "options": [widget.itemText(i) for i in range(widget.count())]
                        })
                    else:
                        row_data.append({
                            "type": "combobox",
                            "value": "uniform",
                            "options": ["uniform", "log_10", "log_e", "deltaX_X"]
                        })  # 默认值
                elif col == 5:  # 处理 QCheckBox (第6列)
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
                    elif cell_data["type"] == "combobox":  # 处理 QComboBox
                        combo = QtWidgets.QComboBox()
                        combo.addItems(cell_data["options"])
                        # 设置当前选中的项
                        index = combo.findText(cell_data["value"])
                        if index >= 0:
                            combo.setCurrentIndex(index)
                        self.tableWidget.setCellWidget(row, col, combo)
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