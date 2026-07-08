from PyQt5 import QtWidgets,QtCore,QtGui
from utils.ui.BaseUI import CollapsibleWidget
from utils.browse_dialog import UtilsSelectionDialog
from PyQt5.QtWidgets import QTableWidgetItem, QLineEdit, QCheckBox, QWidget, QHBoxLayout
from rongzai.algSvc.neutron import smooth_neutron_data
from rongzai.utils import get_all_from_detector
import numpy as np
import traceback
import copy

class smooth(CollapsibleWidget):
    def __init__(self, name, parent=None):
        super(smooth, self).__init__(name, "utils/ui/smooth.ui", parent)
        self.parent = parent

        self.add_smooth_button.clicked.connect(self.add_smooth)
        self.add_defaultSmooth_button.clicked.connect(self.add_defaultSmooth)

        self.checkboxes = []  # 存储复选框引用
        self.delete_button.clicked.connect(self.delete_selected_rows)

    def run(self):
        try:
            if self.toggle_button.isChecked():
                smooth = self.extract_smooth_from_table()
                for data in self.parent.data_list:
                    if data['detector'] in smooth.keys():
                        data['detector_focused'] = smooth_neutron_data(data['detector_focused'],
                                                                        smooth[f"{data['detector']}"]['npoint'],
                                                                        smooth[f"{data['detector']}"]['order'])
                        data['detector_focused']['error'].values = np.zeros(data['detector_focused']["error"].values.shape)
        except Exception as e:
            print(f'Reason: {e}')
            import traceback
            traceback.print_exc()  # 打印异常的堆栈跟踪

    def extract_smooth_from_table(self):
        smooth = {}
        num_rows = self.tableWidget.rowCount()
        for row in range(num_rows):
            # 获取第一列的文件名作为字典的 key
            detector_name = self.tableWidget.item(row, 0).text()

            # 获取第2至第3列的数值
            for col in range(1, 3):
                edit = self.tableWidget.cellWidget(row, col)
                if edit is not None:
                    try:
                        if col == 1:
                            npoint = int(edit.text())
                        elif col == 2 or col == 3:
                            order = int(edit.text())
                    except ValueError:
                        npoint = 1  # 如果转换失败，使用默认值，比如 0.0
                        order = 1

            # 将值添加到字典中
            if detector_name not in smooth:
                smooth[detector_name] = {"npoint": npoint, "order": order}

        return smooth

    def plot_data(self):
        if self.toggle_button.isChecked():
            plot_data = []
            for data in self.parent.data_list:
                if "detector_focused" in data:
                    plot_data.append({"name": f"{data['name']}_{data['detector']}",
                                      "data": [copy.deepcopy(data["detector_focused"]["xvalue"].values[0]),
                                               copy.deepcopy(data["detector_focused"]["histogram"].values[0]),
                                               copy.deepcopy(data["detector_focused"]["error"].values[0])],
                                      "x_label": "d (Å)",
                                      "y_label": "Intensity (a.u.)"})
            return plot_data
        else:
            return []

    def add_smooth(self):
        detector_set = set()
        # 使用 for 循环将每个 data['detector'] 添加到集合，集合会自动去重
        for data in self.parent.data_list:
            detector_set.add(data['detector'])
        # 将集合转换为列表
        detectors = list(detector_set)
        self.select_detectors(detectors)

    def add_defaultSmooth(self):
        try:
            selected_items = self.select_defaultSmoothGroup()
            if len(selected_items) != 0:
                selected_detectors = self.select_detectors_from_data()
                for detector_item in selected_items:
                    for detector in selected_detectors:
                        group, modules = get_all_from_detector(detector, self.parent.config['base']['group_info'],
                                                            self.parent.config['base']['bank_info'])
                        npoint = self.parent.config['base']["default_smooth"][detector_item][group]["npoint"]
                        order = self.parent.config['base']["default_smooth"][detector_item][group]["order"]
                        # 检查探测器是否已经存在于 tableWidget 中
                        item_exists = False
                        for row in range(self.tableWidget.rowCount()):
                            existing_item = self.tableWidget.item(row, 0)
                            if existing_item and existing_item.text() == detector:
                                item_exists = True
                                item_row = row

                        if item_exists:
                            for col in range(1, 3):
                                linEdit = self.tableWidget.cellWidget(item_row, col)
                                if col == 1:
                                    linEdit.setText(str(npoint))
                                elif col == 2:
                                    linEdit.setText(str(order))
                        else:
                            row_position = self.tableWidget.rowCount()
                            self.tableWidget.insertRow(row_position)
                            # 第1列: 探测器名
                            item = QTableWidgetItem(detector)
                            self.tableWidget.setItem(row_position, 0, item)
                            # 第2-3列: 可以输入正整数的 QLineEdit
                            for col in range(1, 3):
                                int_edit = QLineEdit()
                                int_validator = QtGui.QIntValidator()  # 创建整数验证器
                                int_validator.setBottom(1)  # 设置最小值为 1，确保输入为正整数
                                int_edit.setValidator(int_validator)  # 仅允许输入正整数
                                if col == 1:
                                    int_edit.setText(str(npoint))
                                elif col == 2:
                                    int_edit.setText(str(order))
                                self.tableWidget.setCellWidget(row_position, col, int_edit)
                            # 第4列: 复选框
                            checkbox_widget = QWidget()
                            checkbox_layout = QHBoxLayout()
                            checkbox_layout.setContentsMargins(0, 0, 0, 0)
                            check_box = QCheckBox()
                            checkbox_layout.addWidget(check_box)
                            checkbox_layout.setAlignment(QtCore.Qt.AlignCenter)  # 居中对齐
                            checkbox_widget.setLayout(checkbox_layout)
                            self.tableWidget.setCellWidget(row_position, 3, checkbox_widget)
                            self.checkboxes.append((row_position, check_box))
        except Exception as e:
            print(f'Reason: {e}')
            traceback.print_exc()  # 打印异常的堆栈跟踪

    def select_defaultSmoothGroup(self):
        items = [item for item in self.parent.config['base']["default_smooth"].keys()]
        detector_dialog = UtilsSelectionDialog(items, window_title="Select Default Smooths", parent=None)
        if detector_dialog.exec_() == QtWidgets.QDialog.Accepted:
            selected_items = detector_dialog.selectedFiles()
            return selected_items
        else:
            return []

    def select_detectors_from_data(self):
        detector_set = set()
        # 使用 for 循环将每个 data['detector'] 添加到集合，集合会自动去重
        for data in self.parent.data_list:
            detector_set.add(data['detector'])
        # 将集合转换为列表
        detectors = list(detector_set)
        # 弹出窗口让用户选择detectors
        detector_dialog = UtilsSelectionDialog(detectors, window_title="Select Detectors", parent=None)
        if detector_dialog.exec_() == QtWidgets.QDialog.Accepted:
            selected_detectors = detector_dialog.selectedFiles()
            return selected_detectors
        else:
            return []

    def select_detectors(self, detectors, parent=None):
        detector_dialog = UtilsSelectionDialog(detectors,window_title="Select Detectors", parent=parent)
        if detector_dialog.exec_() == QtWidgets.QDialog.Accepted:
            selected_files = detector_dialog.selectedFiles()
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
                    # 第2-3列: 可以输入正整数的 QLineEdit
                    for col in range(1, 3):
                        int_edit = QLineEdit()
                        int_validator = QtGui.QIntValidator()  # 创建整数验证器
                        int_validator.setBottom(1)  # 设置最小值为 1，确保输入为正整数
                        int_edit.setValidator(int_validator)  # 仅允许输入正整数
                        self.tableWidget.setCellWidget(row_position, col, int_edit)
                    # 第5列: 复选框
                    checkbox_widget = QWidget()
                    checkbox_layout = QHBoxLayout()
                    checkbox_layout.setContentsMargins(0, 0, 0, 0)
                    check_box = QCheckBox()
                    checkbox_layout.addWidget(check_box)
                    checkbox_layout.setAlignment(QtCore.Qt.AlignCenter)  # 居中对齐
                    checkbox_widget.setLayout(checkbox_layout)
                    self.tableWidget.setCellWidget(row_position, 3, checkbox_widget)
                    self.checkboxes.append((row_position, check_box))

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
                checkbox = self.tableWidget.cellWidget(row, 3).layout().itemAt(0).widget()
                new_checkboxes.append((row, checkbox))
            self.checkboxes = new_checkboxes
        except Exception as e:
            print(f'Reason: {e}')
            import traceback
            traceback.print_exc()  # 打印异常的堆栈跟踪

    def get_config(self):
        return {
            "plot": self.plot.isChecked(),
            "smooth_info": self.save_table(),
            "is_use": self.toggle_button.isChecked()
        }

    def set_config(self,config):
        """根据配置更新模块状态"""
        self.plot.setChecked(config.get("plot", False))
        self.load_table(config.get("smooth_info", []))
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
                elif col == 1:  # 处理 QLineEdit
                    widget = self.tableWidget.cellWidget(row, col)
                    if isinstance(widget, QtWidgets.QLineEdit):
                        row_data.append({"type": "line_edit", "value": widget.text()})
                    else:
                        row_data.append({"type": "line_edit", "value": ""})  # 默认值
                elif col == 2:  # 处理 QLineEdit
                    widget = self.tableWidget.cellWidget(row, col)
                    if isinstance(widget, QtWidgets.QLineEdit):
                        row_data.append({"type": "line_edit", "value": widget.text()})
                    else:
                        row_data.append({"type": "line_edit", "value": ""})  # 默认值
                elif col == 3:  # 处理 QCheckBox
                    widget = self.tableWidget.cellWidget(row, col).layout().itemAt(0).widget()
                    if isinstance(widget, QtWidgets.QCheckBox):
                        row_data.append({"type": "checkbox", "value": widget.isChecked()})
                    else:
                        row_data.append({"type": "checkbox", "value": False})  # 默认值
            table_data.append(row_data)
        return table_data

    def load_table(self,table_data):
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
                        self.tableWidget.setCellWidget(row, col, line_edit)
                    elif cell_data["type"] == "checkbox":  # 处理 QCheckBox
                        checkbox_widget = QWidget()
                        checkbox_layout = QHBoxLayout()
                        checkbox_layout.setContentsMargins(0, 0, 0, 0)
                        check_box = QCheckBox()
                        check_box.setChecked(cell_data["value"])
                        checkbox_layout.addWidget(check_box)
                        checkbox_layout.setAlignment(QtCore.Qt.AlignCenter)  # 居中对齐
                        checkbox_widget.setLayout(checkbox_layout)
                        self.tableWidget.setCellWidget(row, col, checkbox_widget)
                        self.checkboxes.append((row, check_box))
        except FileNotFoundError:
            print("Table data file not found!")
        except Exception as e:
            print(f"Error loading table data: {e}")