from utils.browse import browse
from utils.ui.BaseUI import CollapsibleWidget
from rongzai.algSvc.instrument.diffraction import calculate_neutron_data
from PyQt5 import QtWidgets, QtCore
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QDoubleValidator
from matplotlib.backends.backend_qt5agg import (
    FigureCanvasQTAgg as FigureCanvas,
    NavigationToolbar2QT as NavigationToolbar
)
from matplotlib.figure import Figure
from PyQt5.QtCore import QTimer
from utils.browse_dialog import UtilsSelectionDialog
from PyQt5.QtWidgets import QMessageBox,QTableWidgetItem,QWidget, QHBoxLayout, QLineEdit, QSlider, QHeaderView,QCheckBox
import copy
import traceback


class substraction_multiScale(CollapsibleWidget):
    def __init__(self, name, parent):
        super(substraction_multiScale, self).__init__(name, "utils/ui/substraction_multiScale.ui", parent)
        self.parent = parent

        self.validator = QDoubleValidator(-float('inf'), float('inf'), 8,
                                          self)  # 创建一个浮点数验证器，限制输入范围在 [0.0, +∞)，且最多允许 8 位小数
        self.validator.setNotation(QDoubleValidator.StandardNotation)  # 强制使用标准十进制表示法（避免科学计数法）

        # 初始化浏览功能
        self.browse_run = browse()
        self.samload_button.clicked.connect(lambda: self._on_samload_clicked([data['name'] for data in self.parent.data_list]))
        self.bkgload_button.clicked.connect(self._on_bkgload_clicked)

        self.delete_button.clicked.connect(self.delete_selected_rows)
        self.delete_all_button.clicked.connect(self.delete_all_rows)

        self.checkboxes = []  # 存储复选框引用

        self.updating = False

    def add_slideAndLineEdit(self, row, scaleValue):
        # 创建容器控件
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(5, 0, 5, 0)
        layout.setSpacing(8)

        # 数值标签
        value_line_edit = QLineEdit(f"{scaleValue:.2f}")
        value_line_edit.setValidator(self.validator)
        value_line_edit.setFixedWidth(70)
        layout.addWidget(value_line_edit)

        # 创建滑块控件
        slider = QSlider(Qt.Horizontal)  # 需正确导入Qt.Horizontal
        slider.setFixedWidth(120)  # 控制滑块宽度

        # 设置滑块范围
        slider.setRange(0, 200)
        slider.setValue(int(scaleValue * 100))

        # 连接信号（使用弱引用避免内存泄漏）
        slider.valueChanged.connect(lambda val, le=value_line_edit: self.update_label(val, le))
        value_line_edit.textChanged.connect(lambda text, s=slider, min=0, max=200: self.update_scale(text, s, min, max))

        # 滑块移动时，绘图数据跟着变化
        slider.valueChanged.connect(self._notify_parent)

        # 禁用鼠标滚轮对 slider 的调整
        try:
            slider.installEventFilter(self)
        except Exception:
            pass

        layout.addWidget(slider)
        container.setLayout(layout)

        # 将容器控件加入表格
        self.tableWidget.setCellWidget(row, 1, container)

        # 动态调整列宽
        self.tableWidget.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeToContents  # 设置目标列调整模式:ml-citation{ref="5" data="citationList"}
        )
        self.tableWidget.resizeColumnToContents(1)  # 立即触发调整:ml-citation{ref="1" data="citationList"}


    def _on_samload_clicked(self, files, parent=None):
        """处理样品加载按钮点击"""
        data_dict = {item['name']: item for item in self.parent.data_list}
        detector_dialog = UtilsSelectionDialog(files, window_title="Select Files", parent=parent)
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

                    self.add_slideAndLineEdit(row_position, 1)

                    checkbox_widget = QWidget()
                    checkbox_layout = QHBoxLayout()
                    checkbox_layout.setContentsMargins(0, 0, 0, 0)
                    check_box = QCheckBox()
                    checkbox_layout.addWidget(check_box)
                    checkbox_layout.setAlignment(Qt.AlignCenter)  # 居中对齐
                    checkbox_widget.setLayout(checkbox_layout)
                    self.tableWidget.setCellWidget(row_position, 2, checkbox_widget)
                    self.checkboxes.append((row_position, check_box))  # 保存复选框的引用



    def _on_bkgload_clicked(self):
        """处理背景加载按钮点击"""
        self.browse_run.select_utils(
            self.bkgload_text,
            [data['name'] for data in self.parent.data_list]
        )

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

            # 删除表格行和结构
            for row in rows_to_remove:
                self.tableWidget.removeRow(row)

            # 更新复选框引用，重建剩余复选框的列表
            new_checkboxes = []
            for row in range(self.tableWidget.rowCount()):
                checkbox = self.tableWidget.cellWidget(row, 2).layout().itemAt(0).widget()
                new_checkboxes.append((row, checkbox))
            self.checkboxes = new_checkboxes

        except Exception as e:
            print(f'Reason: {e}')
            import traceback
            traceback.print_exc()  # 打印异常的堆栈跟踪

    def delete_all_rows(self):
        try:
            rows_to_remove = []
            # 第一次通过checkboxes记录要删除的数据的标志
            for row, checkbox in self.checkboxes:
                rows_to_remove.append(row)
            # 按降序排序以避免删除行时影响其他待删除行的索引
            rows_to_remove.sort(reverse=True)
            # 删除表格行
            for row in rows_to_remove:
                self.tableWidget.removeRow(row)
            # 更新复选框引用
            self.checkboxes = []
        except Exception as e:
            print(f'Reason: {e}')
            import traceback
            traceback.print_exc()  # 打印异常的堆栈跟踪

    def update_label(self, slider_value, label):
        """更新缩放比例标签"""
        if not self.updating:
            self.updating = True
            try:
                actual_value = slider_value / 100.0
                label.setText(f"{actual_value:.2f}")
            finally:
                self.updating = False

    def update_scale(self, text, s, min_val, max_val):
        if not self.updating:
            self.updating = True
            try:
                new_value = float(text)
                new_val_scaled = int(new_value * 100)
                new_val_scaled = max(min(new_val_scaled, max_val), min_val)
                s.setValue(new_val_scaled)
            except ValueError:
                pass  # 可以选择向用户显示错误
            finally:
                self.updating = False

    def _show_error_message(self, message):
        """显示错误信息"""
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        ax.text(0.5, 0.5, f"Error: {message}",
                fontsize=8, ha='center', va='center',
                transform=ax.transAxes)
        self.canvas.draw()

    def get_parameters_list(self):
        sam_list, scale_list = [], []
        for row, checkbox in self.checkboxes:
            sam_name = self.tableWidget.item(row, 0).text()
            sam_list.append(sam_name)
            container = self.tableWidget.cellWidget(row, 1)
            value_label = container.findChild(QLineEdit)
            value = float(value_label.text())
            scale_list.append(value)
        return sam_list, scale_list


    def run(self):
        """执行计算但不更新图形"""
        try:
            if self.toggle_button.isChecked():
                sam_list, scale_list = self.get_parameters_list()
                bkg_list = [b for b in self.bkgload_text.text().split('; ') if b]
                data_dict = {item['name']: item for item in self.parent.data_list}
                if self.check_load_text(sam_list, data_dict, "sam") is False:
                    return
                if self.check_load_text(bkg_list, data_dict, "Sample Bkg") is False:
                    return
                if sam_list and bkg_list:
                    for i, sam in enumerate(sam_list):
                        for bkg in bkg_list:
                            if bkg in data_dict.keys():
                                if data_dict[bkg]["detector"] == data_dict[sam]["detector"]:
                                    backup = copy.deepcopy(data_dict[bkg]["detector_focused"])
                                    scale = scale_list[i]
                                    data_dict[bkg]["detector_focused"]["histogram"].values *= scale
                                    data_dict[bkg]["detector_focused"]["error"].values *= scale
                                    data_dict[sam]["detector_focused"] = calculate_neutron_data(
                                        'subtract',
                                        data_dict[sam]["detector_focused"],
                                        data_dict[bkg]["detector_focused"]
                                    )
                                    data_dict[bkg]["detector_focused"] = backup
                                    data_dict[sam]["record"]["subtraction_self"] = data_dict[bkg]['name']
                                    data_dict[sam]["record"]["subtraction_scale"] = scale
        except Exception as e:
            print(f"Error in run(): {e}")
            traceback.print_exc()

    def check_load_text(self,name_list,data_dict, data_class):
        for name in name_list:
            if name not in data_dict:
                QMessageBox().warning(self, "warning in Subtraction",
                                f"There exists {data_class} data not loaded, please Check ")
                return False
        return True

    def _notify_parent(self):
        """通知父窗口数据已更新"""
        if hasattr(self.parent, 'module_value_changed'):
            self.parent.module_value_changed(self)

    def plot_data(self):
        if self.toggle_button.isChecked():
            plot_data = []
            sam_list, _ = self.get_parameters_list()
            for data in self.parent.data_list:
                if "detector_focused" in data:
                    if data['name'] in sam_list:
                        plot_data.append({"name": f"{data['name']}",
                                          "data": [copy.deepcopy(data["detector_focused"]["xvalue"].values[0]),
                                                   copy.deepcopy(data["detector_focused"]["histogram"].values[0]),
                                                   copy.deepcopy(data["detector_focused"]["error"].values[0])],
                                          "x_label": "d (Å)",
                                          "y_label": "Intensity (a.u.)"})
            return plot_data
        else:
            return []

    def eventFilter(self, obj, event):
        """拦截滑块的滚轮事件，防止鼠标滚轮改变滑块值。"""
        try:
            # 使用 QtCore.QEvent.Wheel 来判断滚轮事件
            if isinstance(event, object) and event.type() == QtCore.QEvent.Wheel:
                # 如果目标是表格内的 slider（或任何 slider），且被安装了过滤器，则拦截
                # 直接返回 True 表示事件已处理，不再向下传递
                return True
        except Exception:
            pass
        return super(substraction_multiScale, self).eventFilter(obj, event)

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
                    container = self.tableWidget.cellWidget(row, col)
                    value_label = container.findChild(QLineEdit)
                    if isinstance(value_label, QtWidgets.QLineEdit):
                        row_data.append({"type": "line_edit", "value": value_label.text()})
                    else:
                        row_data.append({"type": "line_edit", "value": ""})  # 默认值
                elif col == 2:  # 处理 QCheckBox
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
            self.checkboxes = []  # 存储复选框引用
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
                        scale_value = float(cell_data["value"])
                        self.add_slideAndLineEdit(row, scale_value)
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
                        self.checkboxes.append((row, check_box))  # 保存复选框的引用
        except FileNotFoundError:
            print("Table data file not found!")
        except Exception as e:
            print(f"Error loading table data: {e}")

    def get_config(self):
        """获取当前配置"""
        return {
            "bkgload_text": self.bkgload_text.text(),
            "sam_info": self.save_table(),
            "plot": self.plot.isChecked(),
            "is_use": self.toggle_button.isChecked()
        }

    def set_config(self, config):
        """设置配置"""
        self.bkgload_text.setText(config.get("bkgload_text", ""))
        self.load_table(config.get("sam_info", []))
        self.plot.setChecked(config.get("plot", False))
        self.toggle_button.setChecked(config.get("is_use", False))
