from typing import List
from PyQt5 import QtWidgets,QtCore
import traceback,copy
from PyQt5.QtGui import QDoubleValidator, QIntValidator
from PyQt5.QtWidgets import QTableWidgetItem, QLineEdit, QCheckBox, QWidget, QHBoxLayout,QMessageBox
from utils.browse_dialog import UtilsSelectionDialog
from rongzai.utils import generate_x
from rongzai.algSvc.instrument.pdf import stitch_modules
from utils.ui.BaseUI import CollapsibleWidget



class merge_sq(CollapsibleWidget):
    def __init__(self, parent):
        super(merge_sq, self).__init__("Merge S(Q)", "utils/ui/merge_sq.ui", parent)
        self.parent = parent

        self.load_button.clicked.connect(
            lambda: self.select_baseData(self.load_text, [data['name'] for data in self.parent.data_list]))

        self.add_button.clicked.connect(lambda: self.add_mergeData([data['name'] for data in self.parent.data_list]))
        self.checkboxes = []  # 存储复选框引用
        self.delete_button.clicked.connect(self.delete_selected_rows)

        self.double_validator = QDoubleValidator()
        self.start.setValidator(self.double_validator)
        self.end.setValidator(self.double_validator)
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


    def add_mergeData(self, files, parent=None):
        try:
            detector_dialog = UtilsSelectionDialog(files, window_title="Select Files", parent=parent, single_selection=True)
            if detector_dialog.exec_() == QtWidgets.QDialog.Accepted:
                selected = detector_dialog.selectedFiles()
                if selected:
                    mergeData = selected[0]
                    # 检查是否已经存在于 tableWidget 中
                    data_exists = False
                    for row in range(self.tableWidget.rowCount()):
                        existing_item = self.tableWidget.item(row, 0)
                        if existing_item and existing_item.text() == mergeData:
                            data_exists = True
                            break
                    # 如果文件不存在，则添加新行
                    if not data_exists:
                        row_position = self.tableWidget.rowCount()
                        self.tableWidget.insertRow(row_position)
                        # 第1列: 文件名
                        item = QTableWidgetItem(mergeData)
                        self.tableWidget.setItem(row_position, 0, item)
                        # 第2-4列: 可以输入浮点数的 QLineEdit
                        for col in range(1, 3):
                            float_edit = QLineEdit()
                            float_edit.setValidator(self.double_validator)  # 仅允许输入浮点数
                            self.tableWidget.setCellWidget(row_position, col, float_edit)
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
                checkbox = self.tableWidget.cellWidget(row, 3).layout().itemAt(0).widget()
                new_checkboxes.append((row, checkbox))
            self.checkboxes = new_checkboxes
        except Exception as e:
            print(f'Reason: {e}')
            import traceback
            traceback.print_exc()  # 打印异常的堆栈跟踪

    def run(self):
        try:
            if self.toggle_button.isChecked():
                runno_list = []
                base_name = self.load_text.text()
                data_dict = {item['name']: item for item in self.parent.data_list}
                merge_list, overlap = self.extract_info_from_table()
                x,y,e = data_dict[base_name]['sq_data'][0],data_dict[base_name]['sq_data'][1],data_dict[base_name]['sq_data'][2]
                runno_list.append(data_dict[base_name]['runno'])
                mergedata_list = [(x,y,e)]
                correction_list = [data_dict[base_name]["correction_info"]]
                for merge_name in merge_list:
                    x, y, e = data_dict[merge_name]['sq_data'][0], data_dict[merge_name]['sq_data'][1],data_dict[merge_name]['sq_data'][2]
                    correction_list.append(data_dict[merge_name]["correction_info"])
                    runno_list.append(data_dict[merge_name]['runno'])
                    mergedata_list.append((x, y, e))
                if not all(d == correction_list[0] for d in correction_list):
                    QMessageBox.critical(None, "warning", "the correction information of the merged data is not same！chose the one from base data.")
                q = generate_x(float(self.start.text()), float(self.end.text()), int(self.number.text()))
                q, sq, e = stitch_modules(mergedata_list, q, {"overlap":overlap})
                runno = self.unique_join(runno_list)
                self.parent.data_list.append({"name": "merged_data","runno": runno, "sq_data":[q,sq,e], "correction_info":correction_list[0]})
        except Exception as e:
            print(f'Reason: {e}')
            traceback.print_exc()  # 打印异常的堆栈跟踪

    def plot_data(self):
        if self.toggle_button.isChecked():
            plot_data = []
            for data in self.parent.data_list:
                if data['name'] == 'merged_data':
                    plot_data.append({"name":"mergedData",
                                      "data":copy.deepcopy(data["sq_data"]),
                                      "x_label": r'Q (Å$^{-1}$)',
                                      "y_label": "Intensity (a.u.)"
                                      })
            return plot_data
        else:
            return []

    def extract_info_from_table(self):
        mergename_list = []
        overlap = []
        num_rows = self.tableWidget.rowCount()
        for row in range(num_rows):
            # 获取第一列的文件名作为字典的 key
            merge_name = self.tableWidget.item(row, 0).text()

            # 获取第2至第3列的数值
            for col in range(1, 3):
                edit = self.tableWidget.cellWidget(row, col)
                if edit is not None:
                    try:
                        if col == 1:
                            overlap_left = float(edit.text())
                        elif col == 2:
                            overlap_right = float(edit.text())
                    except ValueError:
                        self.show_error_message(
                            f"Invalid input at row {row + 1}, column {col + 1}. Please enter a valid number.")
                        return  # Exit the function if input is invalid

            mergename_list.append(merge_name)
            overlap.append([overlap_left,overlap_right])

        return mergename_list,overlap

    def show_error_message(self, message):
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Critical)
        msg.setWindowTitle("Input Error")
        msg.setText(message)
        msg.setStandardButtons(QMessageBox.Ok)
        msg.exec_()  # Show the message box

    def unique_join(self, strings: List[str], sep: str = "_", ignore_case: bool = False, sort_result: bool = False) -> str:
        """
        从字符串列表中挑选不同的字符串，用下划线（或自定义分隔符）拼接后返回。
        
        参数:
            strings: 输入字符串列表
            sep: 拼接用分隔符，默认 "_"
            ignore_case: 是否忽略大小写进行去重，默认 False
            sort_result: 是否对去重后的结果排序（按字母序）。
                        若为 True，则在保留“首次出现的原样”的前提下排序。
        
        返回:
            去重并拼接后的字符串
        """
        seen = set()
        out = []
        for s in strings:
            key = s.casefold() if ignore_case else s
            if key not in seen:
                seen.add(key)
                out.append(s)
        if sort_result:
            out = sorted(out, key=(str.casefold if ignore_case else None))
        return sep.join(out)

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
                elif col in (1, 2):  # 处理 QLineEdit (第2-3)
                    widget = self.tableWidget.cellWidget(row, col)
                    if isinstance(widget, QtWidgets.QLineEdit):
                        row_data.append({"type": "line_edit", "value": widget.text()})
                    else:
                        row_data.append({"type": "line_edit", "value": ""})  # 默认值
                elif col == 3:  # 处理 QCheckBox (第4列)
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
                        line_edit.setValidator(self.double_validator)  # 设置验证器
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
            "is_use": self.toggle_button.isChecked(),
            "plot": self.plot.isChecked(),
            "load_text": self.load_text.text(),
            "start": self.start.text(),
            "end": self.end.text(),
            "number": self.number.text(),
            "merge_info": self.save_table(),
        }

    def set_config(self,config):
        """根据配置更新模块状态"""
        self.toggle_button.setChecked(config.get("is_use", False))
        self.plot.setChecked(config.get("plot", False))
        self.load_text.setText(config.get("load_text", ""))
        self.start.setText(config.get("start", ""))
        self.end.setText(config.get("end", ""))
        self.number.setText(config.get("number", ""))
        self.load_table(config.get("merge_info", []))

