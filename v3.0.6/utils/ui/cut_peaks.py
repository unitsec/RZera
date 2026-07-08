from PyQt5 import QtWidgets,QtCore,QtGui
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QDoubleValidator
from PyQt5.QtWidgets import QSlider,QHeaderView
from utils.ui.BaseUI import CollapsibleWidget
from utils.browse_dialog import UtilsSelectionDialog
from PyQt5.QtWidgets import QTableWidgetItem, QLineEdit, QCheckBox, QWidget, QHBoxLayout
from rongzai.algSvc.neutron import strip_peaks_neutron_data
from rongzai.utils import get_all_from_detector
from pymatgen.core import Structure,Lattice
from pymatgen.analysis.diffraction.xrd import XRDCalculator
from pymatgen.symmetry.analyzer import SpacegroupAnalyzer
import numpy as np
import matplotlib.pyplot as plt
import traceback,math
import copy

class cut_peaks(CollapsibleWidget):
    def __init__(self, name, parent):
        super(cut_peaks, self).__init__(name, "utils/ui/cut_peaks.ui", parent)
        self.parent = parent

        self.validator = QDoubleValidator(-float('inf'), float('inf'), 8, self)  # 创建一个浮点数验证器，限制输入范围在 [0.0, +∞)，且最多允许 8 位小数
        self.validator.setNotation(QDoubleValidator.StandardNotation)  # 强制使用标准十进制表示法（避免科学计数法）

        #配置cif相关
        self.structures = []
        self.cif_checkboxes = []
        self.crystal_systems = []  # 存储每个结构的晶系信息
        self.add_cif.clicked.connect(self.add_cif_file)
        self.cif_delete.clicked.connect(self.delete_cif_files)
        self.add_peaks_from_cif.clicked.connect(self.add_cif_peaks)

        self.add_peak_button.clicked.connect(self.add_peak)
        self.add_defaultPeak_button.clicked.connect(self.add_defaultPeak)

        self.checkboxes = []  # 存储复选框引用
        self.delete_button.clicked.connect(self.delete_selected_rows)
        self.delete_all_button.clicked.connect(self.delete_all_rows)

        self.updating = False

    def get_crystal_system(self, struct):
        """根据结构的空间群确定晶系"""
        analyzer = SpacegroupAnalyzer(struct)
        spacegroup_number = analyzer.get_space_group_number()
        
        # 根据空间群编号确定晶系
        if 1 <= spacegroup_number <= 2:
            return "triclinic"  # 三斜晶系
        elif 3 <= spacegroup_number <= 15:
            return "monoclinic"  # 单斜晶系
        elif 16 <= spacegroup_number <= 74:
            return "orthorhombic"  # 正交晶系
        elif 75 <= spacegroup_number <= 142:
            return "tetragonal"  # 四方晶系
        elif 143 <= spacegroup_number <= 167:
            return "trigonal"  # 三角晶系
        elif 168 <= spacegroup_number <= 194:
            return "hexagonal"  # 六方晶系
        elif 195 <= spacegroup_number <= 230:
            return "cubic"  # 立方晶系
        else:
            return "unknown"
    
    def get_crystal_system_constraints(self, crystal_system):
        """获取晶系对应的参数约束规则
        返回字典: {col: {"editable": bool, "sync_cols": [list of cols]}}
        列号: 1-6 对应 a,b,c,alpha,beta,gamma
        """
        constraints = {
            "cubic": {
                1: {"editable": True, "sync_cols": [2, 3]},  # a: 可编辑，b,c跟随
                2: {"editable": False, "sync_cols": []},     # b: 不可编辑
                3: {"editable": False, "sync_cols": []},     # c: 不可编辑
                4: {"editable": False, "sync_cols": []},     # alpha=90，不可编辑
                5: {"editable": False, "sync_cols": []},     # beta=90，不可编辑
                6: {"editable": False, "sync_cols": []},     # gamma=90，不可编辑
            },
            "tetragonal": {
                1: {"editable": True, "sync_cols": [2]},     # a: 可编辑，b跟随
                2: {"editable": False, "sync_cols": []},     # b: 不可编辑
                3: {"editable": True, "sync_cols": []},      # c: 可编辑
                4: {"editable": False, "sync_cols": []},     # alpha=90，不可编辑
                5: {"editable": False, "sync_cols": []},     # beta=90，不可编辑
                6: {"editable": False, "sync_cols": []},     # gamma=90，不可编辑
            },
            "hexagonal": {
                1: {"editable": True, "sync_cols": [2]},     # a: 可编辑，b跟随
                2: {"editable": False, "sync_cols": []},     # b: 不可编辑
                3: {"editable": True, "sync_cols": []},      # c: 可编辑
                4: {"editable": False, "sync_cols": []},     # alpha=90，不可编辑
                5: {"editable": False, "sync_cols": []},     # beta=90，不可编辑
                6: {"editable": False, "sync_cols": []},     # gamma=120，不可编辑
            },
            "trigonal": {
                1: {"editable": True, "sync_cols": [2]},     # a: 可编辑，b跟随
                2: {"editable": False, "sync_cols": []},     # b: 不可编辑
                3: {"editable": True, "sync_cols": []},      # c: 可编辑
                4: {"editable": False, "sync_cols": []},     # alpha: 不可编辑（通常=90）
                5: {"editable": False, "sync_cols": []},     # beta: 不可编辑
                6: {"editable": False, "sync_cols": []},     # gamma: 不可编辑（通常=120）
            },
            "orthorhombic": {
                1: {"editable": True, "sync_cols": []},      # a: 可编辑
                2: {"editable": True, "sync_cols": []},      # b: 可编辑
                3: {"editable": True, "sync_cols": []},      # c: 可编辑
                4: {"editable": False, "sync_cols": []},     # alpha=90，不可编辑
                5: {"editable": False, "sync_cols": []},     # beta=90，不可编辑
                6: {"editable": False, "sync_cols": []},     # gamma=90，不可编辑
            },
            "monoclinic": {
                1: {"editable": True, "sync_cols": []},      # a: 可编辑
                2: {"editable": True, "sync_cols": []},      # b: 可编辑
                3: {"editable": True, "sync_cols": []},      # c: 可编辑
                4: {"editable": False, "sync_cols": []},     # alpha=90，不可编辑
                5: {"editable": True, "sync_cols": []},      # beta: 可编辑
                6: {"editable": False, "sync_cols": []},     # gamma=90，不可编辑
            },
            "triclinic": {
                1: {"editable": True, "sync_cols": []},      # a: 可编辑
                2: {"editable": True, "sync_cols": []},      # b: 可编辑
                3: {"editable": True, "sync_cols": []},      # c: 可编辑
                4: {"editable": True, "sync_cols": []},      # alpha: 可编辑
                5: {"editable": True, "sync_cols": []},      # beta: 可编辑
                6: {"editable": True, "sync_cols": []},      # gamma: 可编辑
            },
        }
        return constraints.get(crystal_system, constraints["triclinic"])

    def add_cif_peaks(self):
        try:
            if not self.any_cif_selected():
                return
            selected_detectors = self.select_detectors_from_data()
            d_positions_dict = self.get_peaks_from_cif()
            curr_peaks = self.extract_peaks_from_table()
            for cif_name,d_positions in d_positions_dict.items():
                for detector in selected_detectors:
                    group, modules = get_all_from_detector(detector, self.parent.config['base']['group_info'],
                                                           self.parent.config['base']['bank_info'])
                    for i, d_position in enumerate(d_positions):
                        peak = [d_position[0]-d_position[1],d_position[0]+d_position[2]]
                        if detector in curr_peaks.keys():
                            if peak in curr_peaks[detector]:
                                continue
                        if not self.check_peak_boundary(peak,group):
                            continue
                        row_position = self.tableWidget.rowCount()
                        self.tableWidget.insertRow(row_position)

                        # 第1列: 探测器名
                        _item = QTableWidgetItem(detector)
                        self.tableWidget.setItem(row_position, 0, _item)
                        self.adjust_colWidth(0)

                        # 第2-3列: 可以输入浮点数的 QLineEdit
                        for col in range(1, 3):
                            float_edit = QLineEdit()
                            float_edit.setValidator(QtGui.QDoubleValidator())  # 仅允许输入浮点数
                            if col == 1:
                                float_edit.setText(f"{peak[0]:.5f}")
                            if col == 2:
                                float_edit.setText(f"{peak[1]:.5f}")
                            self.tableWidget.setCellWidget(row_position, col, float_edit)
                            self.adjust_colWidth(col)

                        # 第4列: 复选框
                        checkbox_widget = QWidget()
                        checkbox_layout = QHBoxLayout()
                        checkbox_layout.setContentsMargins(0, 0, 0, 0)
                        check_box = QCheckBox()
                        checkbox_layout.addWidget(check_box)
                        checkbox_layout.setAlignment(QtCore.Qt.AlignCenter)  # 居中对齐
                        checkbox_widget.setLayout(checkbox_layout)
                        self.tableWidget.setCellWidget(row_position, 3, checkbox_widget)
                        self.checkboxes.append((row_position, check_box))  # 保存复选框的引用
                        self.adjust_colWidth(3)

        except Exception as e:
            print(f'Reason: {e}')
            traceback.print_exc()  # 打印异常的堆栈跟踪

    def check_peak_boundary(self,peak,group):
        """该函数用于在为特定detector添加用于扣峰的peak范围时，确实该范围是否在该detector所属group的d_rebin范围内"""
        d_left,d_right = self.parent.config["base"]["d_rebin"][group][0], self.parent.config["base"]["d_rebin"][group][1]
        peak_left,peak_right=peak[0],peak[1]
        judge = True
        if peak_right <= d_left or peak_left >= d_right:
            judge = False
        return judge

    # def check_cif(self, state):
    #     # 遍历复选框列表，找到状态改变的那个
    #     for row, checkbox in self.cif_checkboxes:
    #         if checkbox is self.sender():
    #             if state == Qt.Checked:
    #                 d_positions_dict = self.get_peaks_from_cif()
    #             else:
    #
    #             break

    def check_cif(self):
        # if not self.any_cif_selected():
        #     return
        d_positions_dict = self.get_peaks_from_cif()
        self.plot_d_positions(d_positions_dict)


    def any_cif_selected(self):
        has_check = False
        for row, checkbox in self.cif_checkboxes:
            if checkbox.isChecked():
                has_check = True
        return has_check

    def plot_d_positions(self,d_positions_dict):
        if not hasattr(self.parent, 'plot_win'):
            self.parent.execute_previous_modules(self.objectName())
            # 勾选所有条目
            for index in range(1, self.parent.plot_win.listWidget.count()):  # 从 1 开始，跳过 "ALL" 条目
                item = self.parent.plot_win.listWidget.item(index)
                # self.parent.plot_win.listWidget.blockSignals(True)
                item.setCheckState(Qt.Checked)
                # self.parent.plot_win.listWidget.blockSignals(False)

        else:
            self.parent.plot_win.show()
        # 获取默认颜色循环和定义线条样式
        colors = plt.rcParams['axes.prop_cycle'].by_key()['color']
        linestyles = ['-', '--', '-.', ':']

        # 更新绘图数据以清除图上现有的d_position
        self.parent.plot_win.update_plot_data(self.parent.plot_win.plot_dict)
        # 绘制垂直线
        for i, (name, d_positions) in enumerate(d_positions_dict.items()):
            linestyle = linestyles[i % len(linestyles)]
            for j, peak in enumerate(d_positions):
                color = colors[j % len(colors)]
                # 绘制左边界线
                self.parent.plot_win.ax.axvline(
                    x=float(peak[0]) - peak[1],
                    linestyle=linestyle,
                    color=color,
                    linewidth=0.5,
                    label=f'{name}' if j == 0 else ""
                )
                # 绘制右边界线
                self.parent.plot_win.ax.axvline(
                    x=float(peak[0]) + peak[2],
                    linestyle=linestyle,
                    color=color,
                    linewidth=0.5,
                    label=""
                )
        if self.parent.plot_win.legend_visible:
            self.parent.plot_win.ax.legend()
        # 重绘画布
        self.parent.plot_win.canvas.draw()

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

    def get_peaks_from_cif(self):
        # 第一次通过checkboxes记录要删除的数据的标志
        d_positions_dict = {}
        for row, checkbox in self.cif_checkboxes:
            if checkbox.isChecked():
                parameters,name = self.get_parameters_list(row)
                cal_peaks = self.calculate_dspacing_peaks(self.structures[row], parameters)
                d_positions = [peak[3] for peak in cal_peaks]
                position_range = []
                for position in d_positions:
                    if parameters[6] + parameters[7] * position ** 2 > 0:
                        # 根据d Min和d Max过滤峰
                        if parameters[8] <= position <= parameters[9]:
                            position_range.append([position, 1.51745 * np.sqrt(parameters[6] + parameters[7] * position ** 2), 1.51745 * np.sqrt(parameters[6] + parameters[7] * position ** 2)])
                d_positions_dict[name] = position_range
        return d_positions_dict

    def get_parameters_list(self, row_position):
        parameters = []
        # 获取第一列的文件名作为字典的 key
        struct_name = self.table_cif.item(row_position, 0).text()
        for col in range(1, 11):
            container = self.table_cif.cellWidget(row_position, col)
            if container:
                # 获取容器中的第一个子控件（QLabel）
                value_label = container.findChild(QLineEdit)
                if value_label:
                    # 从标签文本中提取数值
                    value = float(value_label.text())
                    parameters.append(value)
        return parameters, struct_name

    def add_cif_file(self):
        try:
            # 打开文件选择对话框
            options = QtWidgets.QFileDialog.Options()
            cif_path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Select Cif File", "",
                                                                        "CIF Files (*.cif)", options=options)
            if cif_path:
                struct = Structure.from_file(cif_path)
                # print(struct)
                self.add_struct(struct)
        except Exception as e:
            print(f'Reason: {e}')
            traceback.print_exc()  # 打印异常的堆栈跟踪

    def delete_cif_files(self):
        try:
            rows_to_remove = []

            # 第一次通过checkboxes记录要删除的数据的标志
            for row, checkbox in self.cif_checkboxes:
                if checkbox.isChecked():
                    # 将将要删除的数据标记放入集合中
                    rows_to_remove.append(row)

            # 按降序排序以避免删除行时影响其他待删除行的索引
            rows_to_remove.sort(reverse=True)

            # 删除表格行和结构
            for row in rows_to_remove:
                self.table_cif.removeRow(row)
                del self.structures[row]
                del self.crystal_systems[row]

            # 更新复选框引用，重建剩余复选框的列表
            new_checkboxes = []
            for row in range(self.table_cif.rowCount()):
                checkbox = self.table_cif.cellWidget(row, 11).layout().itemAt(0).widget()
                new_checkboxes.append((row, checkbox))
            self.cif_checkboxes = new_checkboxes

        except Exception as e:
            print(f'Reason: {e}')
            import traceback
            traceback.print_exc()  # 打印异常的堆栈跟踪

    def add_struct(self,struct):
        name = struct.formula
        # print(name)
        a = struct.lattice.a
        b = struct.lattice.b
        c = struct.lattice.c
        alpha = struct.lattice.alpha
        beta = struct.lattice.beta
        gamma = struct.lattice.gamma
        self.structures.append(struct)
        
        # 获取晶系和约束规则
        crystal_system = self.get_crystal_system(struct)
        constraints = self.get_crystal_system_constraints(crystal_system)
        self.crystal_systems.append((crystal_system, constraints))
        
        A = 0.00001
        B = 0.00005
        d_min = 1.0
        d_max = 100.0
        d_range_validator = QDoubleValidator(0.0, float('inf'), 3, self)
        d_range_validator.setNotation(QDoubleValidator.StandardNotation)

        # 添加一行到 table_cif
        row_position = self.table_cif.rowCount()
        self.table_cif.insertRow(row_position)
        # 第1列: 结构名
        name_item = QTableWidgetItem(f"{name} ({crystal_system})")
        name_item.setTextAlignment(Qt.AlignCenter) #居中对齐
        self.table_cif.setItem(row_position, 0, name_item)

        # 晶胞参数列（1-6对应a,b,c,alpha,beta,gamma）和d Min/Max
        parameters = [a, b, c, alpha, beta, gamma, A, B, d_min, d_max]
        for col in range(1, 11):
            current_value = parameters[col - 1]

            # 创建容器控件
            container = QWidget()
            layout = QHBoxLayout(container)
            layout.setContentsMargins(5, 0, 5, 0)
            layout.setSpacing(8)

            # 数值标签
            if col in range(1, 7):
                value_line_edit = QLineEdit(f"{current_value:.2f}")

            elif col in range(7, 9):
                value_line_edit = QLineEdit(f"{current_value:.5f}")

            elif col in range(9, 11):
                value_line_edit = QLineEdit(f"{current_value:.3f}")

            if col in range(9, 11):
                value_line_edit.setValidator(d_range_validator)
                value_line_edit.textChanged.connect(self.check_cif)
            else:
                value_line_edit.setValidator(self.validator)
            value_line_edit.setFixedWidth(70)
            
            # 根据晶系约束设置编辑性
            if col in range(1, 7):
                constraint = constraints.get(col, {})
                if not constraint.get("editable", True):
                    value_line_edit.setReadOnly(True)
                    value_line_edit.setStyleSheet("background-color: #e0e0e0; color: #666666;")
            
            layout.addWidget(value_line_edit)

            # d Min/d Max仅需要输入框，不需要滑块
            if col <= 8:
                slider = QSlider(Qt.Horizontal)  # 需正确导入Qt.Horizontal
                slider.setFixedWidth(120)  # 控制滑块宽度

                # 设置滑块范围
                if col in range(1,7):
                    min_val = int((current_value - 1) * 100)
                    max_val = int((current_value + 1) * 100)
                    slider.setRange(min_val, max_val)
                    slider.setValue(int(current_value * 100))
                    # 根据约束设置滑块的禁用状态
                    constraint = constraints.get(col, {})
                    if not constraint.get("editable", True):
                        slider.setEnabled(False)
                elif col == 7:
                    min_val = int((current_value - 5e-4) * 1e5)
                    max_val = int((current_value + 5e-4) * 1e5)
                    slider.setRange(min_val, max_val)
                    slider.setValue(int(current_value * 1e5))
                elif col == 8:
                    min_val = int((current_value - current_value) * 1e5)
                    max_val = int((current_value + 1e-3) * 1e5)
                    slider.setRange(min_val, max_val)
                    slider.setValue(int(current_value * 1e5))

                # 连接信号（使用弱引用避免内存泄漏）
                slider.valueChanged.connect(
                    lambda val, c=col, le=value_line_edit, row=row_position:
                    self._update_slider_value(val, c, le, row)
                )

                value_line_edit.textChanged.connect(lambda text, s=slider, min=min_val, max=max_val, c=col, row=row_position:
                                                    self._on_line_edit_change(text, s, min, max, c, row))
                # 滑块移动时，图中的竖线跟着移动
                slider.valueChanged.connect(self.check_cif)

                layout.addWidget(slider)
            container.setLayout(layout)

            # 将容器控件加入表格
            self.table_cif.setCellWidget(row_position, col, container)

            # 动态调整列宽
            self.table_cif.horizontalHeader().setSectionResizeMode(
                col, QHeaderView.ResizeToContents  # 设置目标列调整模式:ml-citation{ref="5" data="citationList"}
            )
            self.table_cif.resizeColumnToContents(col)  # 立即触发调整:ml-citation{ref="1" data="citationList"}

        checkbox_widget = QWidget()
        checkbox_layout = QHBoxLayout()
        checkbox_layout.setContentsMargins(0, 0, 0, 0)
        check_box = QCheckBox()
        check_box.stateChanged.connect(self.check_cif)
        checkbox_layout.addWidget(check_box)
        checkbox_layout.setAlignment(QtCore.Qt.AlignCenter)  # 居中对齐
        checkbox_widget.setLayout(checkbox_layout)
        self.table_cif.setCellWidget(row_position, 11, checkbox_widget)
        self.cif_checkboxes.append((row_position, check_box))  # 保存复选框的引用

    def _update_slider_value(self, slider_value, col, label, row):
        if not self.updating:
            self.updating = True
            try:
                if col in range(1,7):
                    actual_value = slider_value / 100.0
                    # 更新标签显示
                    label.setText(f"{actual_value:.2f}")
                    # 同步相关参数
                    self._sync_parameters(row, col, actual_value)
                elif col in range(7, 9):
                    actual_value = slider_value / 1e5
                    # 更新标签显示
                    label.setText(f"{actual_value:.5f}")
            finally:
                self.updating = False

    def _sync_parameters(self, row, col, new_value):
        """根据晶系约束同步相关参数"""
        if row >= len(self.crystal_systems):
            return
        
        crystal_system, constraints = self.crystal_systems[row]
        constraint = constraints.get(col, {})
        sync_cols = constraint.get("sync_cols", [])
        
        # 同步相关列的值
        for sync_col in sync_cols:
            container = self.table_cif.cellWidget(row, sync_col)
            if container:
                value_edit = container.findChild(QLineEdit)
                slider = container.findChild(QSlider)
                if value_edit and slider:
                    # 更新文本框和滑块
                    value_edit.blockSignals(True)
                    slider.blockSignals(True)
                    
                    value_edit.setText(f"{new_value:.2f}")
                    slider.setValue(int(new_value * 100))
                    
                    value_edit.blockSignals(False)
                    slider.blockSignals(False)

    # 连接信号：文本框内容改变时更新滑块
    def _on_line_edit_change(self, text, s, min_val, max_val, c, row):
        if not self.updating:
            self.updating = True
            try:
                new_value = float(text)
                # 根据列选择不同的精度转换
                if c in range(1, 7):
                    new_val_scaled = int(new_value * 100)
                    # 同步相关参数
                    self._sync_parameters(row, c, new_value)
                else:
                    new_val_scaled = int(new_value * 1e5)
                # 将值限制在滑块范围内
                new_val_scaled = max(min(new_val_scaled, max_val), min_val)
                s.setValue(new_val_scaled)
            except ValueError:
                pass  # 可以选择向用户显示错误
            finally:
                self.updating = False


    def run(self):
        try:
            if self.toggle_button.isChecked():
                peaks = self.extract_peaks_from_table()
                peaks_for_strip = self.transform_peaks_for_strip(peaks)
                for data in self.parent.data_list:
                    if data['detector'] in peaks.keys():
                        data['detector_focused'] = strip_peaks_neutron_data(data['detector_focused'],
                                                                            peaks_for_strip[f"{data['detector']}"]['peaks'],
                                                                            peaks_for_strip[f"{data['detector']}"]['ranges'])
        except Exception as e:
            print(f'Reason: {e}')
            import traceback
            traceback.print_exc()  # 打印异常的堆栈跟踪

    def transform_peaks_for_strip(self,peaks):
        peaks_for_strip = {}
        for detector,peaks in peaks.items():
            peaks_for_strip[detector] = {}
            peaks_for_strip[detector]["peaks"] = []
            peaks_for_strip[detector]["ranges"] = []
            for peak in peaks:
                peaks_for_strip[detector]["peaks"].append((peak[0]+peak[1])/2)
                peaks_for_strip[detector]["ranges"].append([(peak[1]-peak[0])/2,(peak[1]-peak[0])/2])
        return peaks_for_strip

    def adjust_colWidth(self, col):
        # 动态调整列宽
        self.tableWidget.horizontalHeader().setSectionResizeMode(
            col, QHeaderView.ResizeToContents  # 设置目标列调整模式:ml-citation{ref="5" data="citationList"}
        )
        self.tableWidget.resizeColumnToContents(col)  # 立即触发调整:ml-citation{ref="1" data="citationList"}

    def extract_peaks_from_table(self):
        peaks = {}
        num_rows = self.tableWidget.rowCount()
        for row in range(num_rows):
            # 获取第一列的文件名作为字典的 key
            detector_name = self.tableWidget.item(row, 0).text()

            # 获取第二至第三列的数值，代表 "peaks"
            range_ = []
            for col in range(1, 3):
                float_edit = self.tableWidget.cellWidget(row, col)
                if float_edit is not None:
                    try:
                        range_.append(float(float_edit.text()))
                    except ValueError:
                        range_.append(0.0)

            # 将值添加到字典中
            if detector_name not in peaks:
                peaks[detector_name] = []

            peaks[detector_name].append(range_)
        return peaks

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

    def add_peak(self):
        detector_set = set()
        # 使用 for 循环将每个 data['detector'] 添加到集合，集合会自动去重
        for data in self.parent.data_list:
            detector_set.add(data['detector'])
        # 将集合转换为列表
        detectors = list(detector_set)
        self.select_detectors(detectors)

    def add_defaultPeak(self):
        try:
            selected_items = self.select_defaultPeaksGroup()
            if len(selected_items) != 0:
                selected_detectors = self.select_detectors_from_data()
                curr_peaks = self.extract_peaks_from_table()
                for item in selected_items:
                    for detector in selected_detectors:
                        group, modules = get_all_from_detector(detector, self.parent.config['base']['group_info'],
                                                               self.parent.config['base']['bank_info'])
                        peaks = self.parent.config['base']["default_peaks_for_cut"][item][group]
                        for i, peak in enumerate(peaks):
                            if detector in curr_peaks.keys():
                                if peak in curr_peaks[detector]:
                                    continue
                            row_position = self.tableWidget.rowCount()
                            self.tableWidget.insertRow(row_position)

                            # 第1列: 探测器名
                            _item = QTableWidgetItem(detector)
                            self.tableWidget.setItem(row_position, 0, _item)

                            # 第2-3列: 可以输入浮点数的 QLineEdit
                            for col in range(1, 3):
                                float_edit = QLineEdit()
                                float_edit.setValidator(QtGui.QDoubleValidator())  # 仅允许输入浮点数
                                if col == 1:
                                    float_edit.setText(str(peak[0]))
                                if col == 2:
                                    float_edit.setText(str(peak[1]))
                                self.tableWidget.setCellWidget(row_position, col, float_edit)

                            # 第4列: 复选框
                            checkbox_widget = QWidget()
                            checkbox_layout = QHBoxLayout()
                            checkbox_layout.setContentsMargins(0, 0, 0, 0)
                            check_box = QCheckBox()
                            checkbox_layout.addWidget(check_box)
                            checkbox_layout.setAlignment(QtCore.Qt.AlignCenter)  # 居中对齐
                            checkbox_widget.setLayout(checkbox_layout)
                            self.tableWidget.setCellWidget(row_position, 3, checkbox_widget)
                            self.checkboxes.append((row_position, check_box))  # 保存复选框的引用
        except Exception as e:
            print(f'Reason: {e}')
            import traceback
            traceback.print_exc()  # 打印异常的堆栈跟踪

    def select_defaultPeaksGroup(self):
        items = [item for item in self.parent.config['base']["default_peaks_for_cut"].keys()]
        detector_dialog = UtilsSelectionDialog(items, window_title="Select Default Peaks for Cut", parent=None)
        if detector_dialog.exec_() == QtWidgets.QDialog.Accepted:
            selected_items = detector_dialog.selectedFiles()
            return selected_items
        else:
            return []

    def select_detectors(self,detectors,parent=None):
        detector_dialog = UtilsSelectionDialog(detectors,window_title="Select Detectors", parent=parent)
        if detector_dialog.exec_() == QtWidgets.QDialog.Accepted:
            selected_files = detector_dialog.selectedFiles()
            for file in selected_files:
                # 添加一行到 table widget
                row_position = self.tableWidget.rowCount()
                self.tableWidget.insertRow(row_position)

                # 第1列: 文件名
                file_item = QTableWidgetItem(file)
                self.tableWidget.setItem(row_position, 0, file_item)

                # 第2-3列: 可以输入浮点数的 QLineEdit
                for col in range(1, 3):
                    float_edit = QLineEdit()
                    float_edit.setValidator(QtGui.QDoubleValidator())  # 仅允许输入浮点数
                    self.tableWidget.setCellWidget(row_position, col, float_edit)

                # 第4列: 复选框
                checkbox_widget = QWidget()
                checkbox_layout = QHBoxLayout()
                checkbox_layout.setContentsMargins(0, 0, 0, 0)
                check_box = QCheckBox()
                checkbox_layout.addWidget(check_box)
                checkbox_layout.setAlignment(QtCore.Qt.AlignCenter)  # 居中对齐
                checkbox_widget.setLayout(checkbox_layout)
                self.tableWidget.setCellWidget(row_position, 3, checkbox_widget)
                self.checkboxes.append((row_position, check_box))  # 保存复选框的引用

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
            "cut_info": self.save_table(),
            "is_use": self.toggle_button.isChecked()
        }

    def set_config(self,config):
        """根据配置更新模块状态"""
        self.plot.setChecked(config.get("plot", False))
        self.load_table(config.get("cut_info", []))
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
                        self.checkboxes.append((row, check_box))  # 保存复选框的引用
        except FileNotFoundError:
            print("Table data file not found!")
        except Exception as e:
            print(f"Error loading table data: {e}")

    def calculate_dspacing_peaks(self, struct, parameters, wavelength=0.7,two_theta_range=(0, 180)):
        """
        处理晶胞参数修改后的衍射峰计算，支持自适应空间群
        """
        def build_ordered_approx(input_struct):
            # 对无序结构做近似有序化：每个位点取占比最高的组分
            if input_struct.is_ordered:
                return input_struct
            ordered_species = []
            for site in input_struct.sites:
                species_dict = site.species.as_dict()
                dominant = max(species_dict, key=species_dict.get)
                ordered_species.append(dominant)
            return Structure(
                lattice=input_struct.lattice,
                species=ordered_species,
                coords=input_struct.frac_coords,
                coords_are_cartesian=False,
            )

        def d_to_two_theta(d_spacing, lambda_angstrom):
            if d_spacing <= 0:
                return None
            ratio = lambda_angstrom / (2 * d_spacing)
            if ratio >= 1:
                return 180.0
            return math.degrees(2 * math.asin(ratio))

        new_lattice_dict = {
            'a': parameters[0],
            'b': parameters[1],
            'c': parameters[2],
            'alpha': parameters[3],
            'beta': parameters[4],
            'gamma': parameters[5]
        }
        # 尝试创建新的晶格，如果参数非法会抛出异常
        try:
            new_lattice = Lattice.from_parameters(**new_lattice_dict)
        except Exception as e:
            raise ValueError(f"Invalid lattice parameters: {new_lattice_dict}. Error: {str(e)}")

        # 兼容有序/无序结构：无序结构不能访问 struct.species，使用 site.species 保留占位信息
        struct = Structure(
            lattice=new_lattice,
            species=[site.species for site in struct.sites],
            coords=struct.frac_coords,
            coords_are_cartesian=False
        )
        # 自动分析空间群；若无序结构导致失败，则退化为有序近似继续计算
        try:
            analyzer = SpacegroupAnalyzer(struct)
            struct = analyzer.get_conventional_standard_structure()
        except Exception:
            ordered_struct = build_ordered_approx(struct)
            analyzer = SpacegroupAnalyzer(ordered_struct)
            struct = analyzer.get_conventional_standard_structure()

        # 大晶胞优先尝试 primitive 结构，显著降低 XRD 计算量
        try:
            primitive_input = build_ordered_approx(struct)
            primitive_struct = SpacegroupAnalyzer(primitive_input).get_primitive_standard_structure()
            if len(primitive_struct.sites) < len(struct.sites):
                struct = primitive_struct
        except Exception:
            pass

        # 根据界面设置的 d 范围，先换算为 two-theta 范围，减少无关峰计算
        requested_d_min = parameters[8]
        requested_d_max = parameters[9]
        if requested_d_max > 0 and requested_d_min > requested_d_max:
            requested_d_min, requested_d_max = requested_d_max, requested_d_min

        theta_min, theta_max = two_theta_range
        xrd_calc = XRDCalculator(wavelength=wavelength)
        lambda_ = xrd_calc.wavelength

        d_theta_min = d_to_two_theta(requested_d_max, lambda_)
        d_theta_max = d_to_two_theta(requested_d_min, lambda_)
        if d_theta_min is not None:
            theta_min = max(theta_min, d_theta_min)
        if d_theta_max is not None:
            theta_max = min(theta_max, d_theta_max)

        if theta_min >= theta_max:
            return []

        # 自适应限制 two-theta 上限，避免超大结构导致 UI 卡死
        site_count = len(struct.sites)
        capped_theta_max = theta_max
        if site_count >= 800:
            capped_theta_max = min(theta_max, 40)
        elif site_count >= 400:
            capped_theta_max = min(theta_max, 60)
        elif site_count >= 250:
            capped_theta_max = min(theta_max, 90)

        if theta_min >= capped_theta_max:
            return []
        calc_two_theta_range = (theta_min, capped_theta_max)

        # 计算 XRD 图谱
        xrd_pattern = xrd_calc.get_pattern(struct, two_theta_range=calc_two_theta_range)

        # 过滤 d-spacing 范围内的峰
        filtered_peaks = []
        for theta_deg, intensity, hkls in zip(xrd_pattern.x, xrd_pattern.y, xrd_pattern.hkls):
            theta_rad = math.radians(theta_deg / 2)
            try:
                d = lambda_ / (2 * math.sin(theta_rad))
            except ZeroDivisionError:
                continue
            hkl_list = [(hkl["hkl"], hkl["multiplicity"]) for hkl in hkls]
            filtered_peaks.append((
                round(theta_deg, 4),
                round(intensity, 4),
                hkl_list,
                round(d, 4)
            ))

        return sorted(filtered_peaks, key=lambda x: x[0])
