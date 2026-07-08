from PyQt5 import QtWidgets, QtCore
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QHeaderView
from PyQt5.QtGui import QStandardItemModel, QStandardItem
import traceback,copy
from utils.ui.BaseUI import CollapsibleWidget
from utils.browse import browse
from utils.iTrain import Conv1DModel_4096, predict
from matplotlib.backends.backend_qt5agg import (
    FigureCanvasQTAgg as FigureCanvas,
    NavigationToolbar2QT as NavigationToolbar
)
from matplotlib.figure import Figure
from scipy.interpolate import interp1d
import numpy as np
import matplotlib.pyplot as plt
from utils.spacegroup_list import hm_to_space_group_number
from cctbx import uctbx, sgtbx, miller
from cctbx.crystal import symmetry
from utils.helper import get_resource_path

class AIndex(CollapsibleWidget):
    def __init__(self, parent):
        super(AIndex, self).__init__("AIndex", "utils/ui/AIndex.ui", parent)
        self.parent = parent
        # 初始化数据加载
        self.browse_run = browse()
        self.load_button.clicked.connect(self._on_load_clicked)
        # 设置Matplotlib图形
        self.figure = Figure()
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setStyleSheet("background-color: transparent;")
        # 配置工具栏
        self.toolbar = NavigationToolbar(self.canvas, self)
        self.toolbar.setIconSize(QtCore.QSize(16, 16))
        # 设置布局
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.canvas)
        layout.addWidget(self.toolbar)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.graphicsView.setLayout(layout)
        QTimer = QtCore.QTimer
        QTimer.singleShot(0, self.init_splitter_sizes)
        #初始化AIndex
        self.predict_button.clicked.connect(self.predict)
        self.csmap = ["tetragonal","hexa_trigonal","cubic"]
        self.symmetrymap = {"tetragonal":31, "hexa_trigonal":9, "cubic":17}
        self.cs_sg_map={"tetragonal":[75,143],"hexa_trigonal":[143,195],"cubic":[195,231]}
        #初始化treeView
        self.init_treeView()
        #初始化AIndex_Check
        self.check_button.clicked.connect(self.check)

    def init_splitter_sizes(self):
        if hasattr(self, 'splitter'):
            self.splitter.setChildrenCollapsible(False)
            self.splitter.setStretchFactor(0, 2)
            self.splitter.setStretchFactor(1, 3)
            self.splitter.setSizes([380, 580])
            self.treeView.setMinimumWidth(360)


    def predict(self):
        try:
            if self.toggle_button.isChecked():
                self.compute_figure()
                self.model.clear()  # 清除旧数据
                self.model.setHorizontalHeaderLabels(["Property", "Value"])
                root_item = self.model.invisibleRootItem()

                sam_list = self.load_text.text().split('; ')
                data_dict = {item['name']: item for item in self.parent.data_list}
                if sam_list != ['']:
                    csNet = Conv1DModel_4096(input_channels=1, output_num=3)
                    for sam in sam_list:
                        # 添加SAM节点
                        sam_item = QStandardItem(sam)
                        root_item.appendRow([sam_item, QStandardItem("")])
                        try:
                            # 绘制曲线并保存引用
                            x = data_dict[sam]["detector_focused"]["xvalue"].values[0]
                            y = data_dict[sam]["detector_focused"]["histogram"].values[0]
                            new_x = np.linspace(0.5, 10, 4096)
                            new_y = self.reorganize_data(x, y, new_x)
                            result, _, confidence_distribution = predict(new_y, csNet,get_resource_path('param_data/model_weights/csNet.pth'),task_type='classification')
                            # new_x = np.linspace(0.5, 5, 2048)
                            # new_y = self.reorganize_data(x, y, new_x)
                            for i, confidence in enumerate(confidence_distribution):
                                if confidence >= 0.01:
                                    cs = self.csmap[i]

                                    # 添加晶系节点
                                    cs_value_item = QStandardItem(cs)
                                    cs_value_item.setCheckable(True)  # 添加复选框
                                    cs_value_item.setCheckState(Qt.Unchecked)  # 默认未选中
                                    cs_value_item.setData(cs, role=Qt.UserRole)  # 存储晶系类型
                                    cs_value_item.setData(sam, role=Qt.UserRole + 1)  # 存储样品名
                                    cs_confidence_item = QStandardItem(f"{confidence:.2%}")
                                    sam_item.appendRow([cs_value_item, cs_confidence_item])

                                    symmetryNet = Conv1DModel_4096(input_channels=1, output_num=self.symmetrymap[cs])
                                    latticeNet = Conv1DModel_4096(input_channels=1, output_num=6)
                                    result, _, confidence_distribution = predict(new_y, symmetryNet,
                                                                                 get_resource_path(f'param_data/model_weights/symmetryNet_{cs}.pth'),
                                                                                 task_type='classification')
                                    space_groups = []
                                    for index in range(self.cs_sg_map[cs][0],self.cs_sg_map[cs][1]):
                                        if hm_to_space_group_number[str(index)][2] == result:
                                            space_groups.append([index,hm_to_space_group_number[str(index)][0]])

                                    # 添加空间群节点
                                    sg_item = QStandardItem("Space Group")
                                    cs_value_item.appendRow([sg_item, QStandardItem("")])

                                    # 如果有匹配的空间群
                                    if space_groups:

                                        # 添加每个空间群的详细信息
                                        for sg_num, sg_symbol in space_groups:

                                            # 添加空间群详细信息
                                            sg_symbol_item = QStandardItem(sg_symbol)
                                            sg_num_value = QStandardItem(str(sg_num))
                                            sg_item.appendRow([sg_symbol_item, sg_num_value])
                                    else:
                                        # 如果没有匹配的空间群
                                        no_match_item = QStandardItem("No matching space groups found")
                                        sg_item.appendRow([no_match_item, QStandardItem("")])

                                    lattice = predict(new_y, latticeNet, get_resource_path(f'param_data/model_weights/latticeNet_{cs}.pth'), task_type='regression')

                                    # 添加晶格参数节点
                                    lattice_item = QStandardItem("Lattice Parameters")
                                    cs_value_item.appendRow([lattice_item, QStandardItem("")])

                                    # 格式化晶格参数显示
                                    lattice_params = [
                                        f"a: {lattice[0][0] * 15:.4f}",
                                        f"b: {lattice[0][1] * 15:.4f}",
                                        f"c: {lattice[0][2] * 15:.4f}",
                                        f"α: {lattice[0][3] * 180:.2f}°",
                                        f"β: {lattice[0][4] * 180:.2f}°",
                                        f"γ: {lattice[0][5] * 180:.2f}°"
                                    ]

                                    for param in lattice_params:
                                        param_item = QStandardItem(param)
                                        lattice_item.appendRow([param_item, QStandardItem("")])


                        except Exception as e:
                            error_item = QStandardItem("Analysis Error")
                            sam_item.appendRow([error_item, QStandardItem(str(e))])
                            traceback.print_exc()  # 打印异常的堆栈跟踪
                    # 展开SAM层级
                    self.treeView.expandToDepth(0)
                    self._resize_tree_columns()
                    QtCore.QTimer.singleShot(0, self._resize_tree_columns)

        except Exception as e:
            print(f'Reason: {e}')
            traceback.print_exc()  # 打印异常的堆栈跟踪

    def check(self):
        # 从根开始遍历
        selected_data = self.traverse(self.model.invisibleRootItem())
        # 现在 selected_data 包含所有选中的晶系及其参数
        print("Selected data:", selected_data)
        # 调用你的衍射峰计算函数
        for data in selected_data:
            peaks_info = self.calculate_peaks(data['lattice_params']['a'],
                                     data['lattice_params']['b'],
                                     data['lattice_params']['c'],
                                     data['lattice_params']['alpha'],
                                     data['lattice_params']['beta'],
                                     data['lattice_params']['gamma'],
                                     data['space_groups'][0]['symbol'])
            data["d_list"] = [peak["d_spacing"] for peak in peaks_info]

        self.add_d_in_figure(selected_data)

    def get_config(self):
        return {
            "load_text": self.load_text.text(),
            "is_use": self.toggle_button.isChecked()
        }

    def set_config(self,config):
        """根据配置更新模块状态"""
        self.load_text.setText(config.get("load_text", ""))
        self.toggle_button.setChecked(config.get("is_use", False))

    def traverse(self, item):
        selected_data = []
        for row in range(item.rowCount()):
            child = item.child(row)
            # 检查是否是晶系节点且有复选框
            if child.isCheckable() and child.checkState() == Qt.Checked:
                # 获取存储的数据
                cs = child.data(Qt.UserRole)
                sam = child.data(Qt.UserRole + 1)

                # 获取该晶系下的空间群和晶格参数
                space_groups = []
                lattice_params = None

                # 查找空间群和晶格参数
                for i in range(child.rowCount()):
                    sub_item = child.child(i)

                    if sub_item.text() == "Space Group":
                        # 遍历空间群项（每行包含符号和编号）
                        for sg_row in range(sub_item.rowCount()):
                            # 获取整行（包含符号和编号两个QStandardItem）
                            sg_symbol_item = sub_item.child(sg_row, 0)  # 第一列：符号
                            sg_number_item = sub_item.child(sg_row, 1)  # 第二列：编号

                            if (sg_symbol_item and sg_number_item and
                                    sg_symbol_item.text() != "No matching space groups found"):
                                try:
                                    space_groups.append({
                                        'number': int(sg_number_item.text()),
                                        'symbol': sg_symbol_item.text()
                                    })
                                except (ValueError, AttributeError) as e:
                                    print(f"解析空间群时出错：{e}")

                    elif sub_item.text() == "Lattice Parameters":
                        # 解析晶格参数
                        lattice_params = {}
                        for param_row in range(sub_item.rowCount()):
                            param_item = sub_item.child(param_row)
                            param_text = param_item.text()
                            if param_text.startswith("a:"):
                                lattice_params['a'] = float(param_text.split(":")[1].strip().split()[0])
                            elif param_text.startswith("b:"):
                                lattice_params['b'] = float(param_text.split(":")[1].strip().split()[0])
                            elif param_text.startswith("c:"):
                                lattice_params['c'] = float(param_text.split(":")[1].strip().split()[0])
                            elif param_text.startswith("α:"):
                                lattice_params['alpha'] = float(param_text.split(":")[1].strip().split()[0][:-1])
                            elif param_text.startswith("β:"):
                                lattice_params['beta'] = float(param_text.split(":")[1].strip().split()[0][:-1])
                            elif param_text.startswith("γ:"):
                                lattice_params['gamma'] = float(param_text.split(":")[1].strip().split()[0][:-1])

                # 添加到选中数据
                selected_data.append({
                    'sample': sam,
                    'crystal_system': cs,
                    'space_groups': space_groups,
                    'lattice_params': lattice_params
                })

            # 递归检查子项并合并结果
            selected_data.extend(self.traverse(child))

        return selected_data

    def calculate_peaks(self, a, b, c, alpha, beta, gamma, spacegroup_symbol, round_number=15, d_min=0.5, d_max=10):
        unit_cell = uctbx.unit_cell((a, b, c, alpha, beta, gamma))
        space_group_info = sgtbx.space_group_info(symbol=spacegroup_symbol)
        crystal_symmetry = symmetry(unit_cell=unit_cell, space_group_info=space_group_info)

        # 构建米勒指数集合
        miller_indices = miller.build_set(crystal_symmetry=crystal_symmetry, anomalous_flag=False, d_min=d_min)

        peaks_info = []
        for hkl in miller_indices.indices():
            d_spacing = unit_cell.d(hkl)
            # 检查d-spacing是否在给定的范围内
            if d_min <= d_spacing <= d_max:
                # 检查消光规则
                if not crystal_symmetry.space_group().is_sys_absent(hkl):
                    # 使用 `miller_index=True` 来指明我们是在处理米勒指数
                    symmetry_multiplicity = crystal_symmetry.space_group().multiplicity(hkl, miller_index=True)
                    peaks_info.append({
                        "hkl": hkl,
                        "d_spacing": d_spacing,
                        "multiplicity": symmetry_multiplicity
                    })

        # 使用字典来存储最小米勒指数的 d_spacing
        unique_peaks_info = {}
        for info in peaks_info:
            d_rounded = round(info['d_spacing'], round_number)
            # 如果当前的 d_rounded 不在字典中，或找到更小的米勒指数
            # 这里通过比较绝对值的和来找到较小的米勒指数
            if (d_rounded not in unique_peaks_info or
                    sum(map(abs, info['hkl'])) < sum(map(abs, unique_peaks_info[d_rounded]['hkl']))):
                unique_peaks_info[d_rounded] = info

        # 提取处理后的峰信息
        peaks_info = list(unique_peaks_info.values())
        sorted_peaks_info = sorted(peaks_info, key=lambda x: x['d_spacing'])

        return sorted_peaks_info

    def add_d_in_figure(self, selected_data):
        """添加d间距标记线（确保与曲线颜色一致）"""
        if not hasattr(self, 'ax'):
            return

        # 清除所有标记线（包括之前可能遗留的）
        for artist in self.ax.lines + self.ax.collections:
            if hasattr(artist, '_is_d_marker'):
                artist.remove()

        # 获取当前数据曲线及其颜色
        data_lines = [line for line in self.ax.lines
                      if not hasattr(line, '_is_d_marker')]

        if not data_lines or not selected_data:
            return

        # 绘制标记线
        _, y_max = self.ax.get_ylim()
        marker_height = (y_max - self.y_min_origin) * 0.05
        base_y = self.y_min_origin - (y_max - self.y_min_origin) * 0.1

        # 定义可用的线型样式循环
        line_styles = ['-', '--', '-.', ':']
        for i, data in enumerate(selected_data):
            if 'd_list' not in data:
                continue

            # 获取对应曲线颜色，如果没有则使用默认色系
            color = self.line_colors.get(data['sample'],
                                    plt.cm.tab10(i % 10))
            line_style = line_styles[i % len(line_styles)]  # 循环使用不同线型

            current_base = base_y - i * marker_height * 1.5

            # 绘制标记线
            for d in data['d_list']:
                line = self.ax.plot(
                    [d, d], [current_base, current_base + marker_height],
                    color=color, linewidth=1, linestyle=line_style, alpha=0.7,
                    zorder=3
                )
                line[0]._is_d_marker = True  # 标记为峰位线

        # 调整图形范围
        new_y_min = base_y - len(selected_data) * marker_height * 2
        self.ax.set_ylim(new_y_min, y_max)

        self.canvas.draw()

    def init_treeView(self):
        self.model = QStandardItemModel()
        self.model.setHorizontalHeaderLabels(["Property", "Value"])

        self.treeView.setModel(self.model)
        self.treeView.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.treeView.setTextElideMode(Qt.ElideNone)
        # 设置表头
        header = self.treeView.header()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)  # 第一列按内容自适应
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)  # 第二列按内容自适应
        header.setStretchLastSection(False)
        header.setDefaultAlignment(Qt.AlignLeft)  # 左对齐

    def _resize_tree_columns(self):
        header = self.treeView.header()
        self.treeView.resizeColumnToContents(0)
        self.treeView.resizeColumnToContents(1)

        prop_width = max(self._get_second_level_property_width(), 120)
        value_width = max(self.treeView.columnWidth(1), self.treeView.sizeHintForColumn(1)) + 20

        self.treeView.setColumnWidth(0, prop_width)
        self.treeView.setColumnWidth(1, value_width)

        # 固定到当前计算结果，同时保留用户后续手动拖拽能力。
        header.setSectionResizeMode(0, QHeaderView.Interactive)
        header.setSectionResizeMode(1, QHeaderView.Interactive)

    def _get_second_level_property_width(self):
        """仅根据二级及更深层级的 Property 文本估算列宽，允许一级节点被遮挡。"""
        metrics = self.treeView.fontMetrics()
        indent = self.treeView.indentation()
        model = self.model

        max_width = metrics.horizontalAdvance("Property") + 20

        def walk(parent_item, depth):
            nonlocal max_width
            for row in range(parent_item.rowCount()):
                item = parent_item.child(row, 0)
                if item is None:
                    continue

                if depth >= 1:
                    text_width = metrics.horizontalAdvance(item.text())
                    # 预留树缩进、展开箭头与复选框空间。
                    extra = (depth + 1) * indent + 42
                    max_width = max(max_width, text_width + extra)

                walk(item, depth + 1)

        walk(model.invisibleRootItem(), 0)
        return max_width

    def _on_load_clicked(self):
        """处理样品加载按钮点击"""
        try:
            self.browse_run.select_utils(
                self.load_text,
                [data['name'] for data in self.parent.data_list]
            )
            self.compute_figure()
        except Exception as e:
            print(f'Reason: {e}')
            traceback.print_exc()  # 打印异常的堆栈跟踪

    def compute_figure(self):
        """计算并更新图形（包含清除旧标记）"""
        data_list_backup = copy.deepcopy(self.parent.data_list)
        try:
            # 清除所有图形元素
            self.figure.clear()

            # 初始化新图形
            ax = self.figure.add_subplot(111)
            ax.set_navigate(True)
            self.ax = ax  # 保存ax引用供后续使用

            # 执行前置模块
            self._run_previous_modules()

            # 获取数据
            sam_list = [s for s in self.load_text.text().split('; ') if s]
            data_dict = {item['name']: item for item in self.parent.data_list}

            if sam_list:
                # 绘制数据曲线并保存颜色信息
                self._plot_data(ax, sam_list, data_dict)
            else:
                ax.text(0.5, 0.5, "No valid data",
                        fontsize=8, ha='center', va='center',
                        transform=ax.transAxes)

            # 图形样式设置
            ax.tick_params(axis='both', which='major', labelsize=6, pad=1)
            for spine in ax.spines.values():
                spine.set_linewidth(0.5)

            self.figure.tight_layout(pad=0.5)
            self.figure.subplots_adjust(
                left=0.1, right=0.98,
                bottom=0.1, top=0.95
            )

            self.canvas.draw()

        except Exception as e:
            self._show_error_message(str(e))
        finally:
            self.parent.data_list = data_list_backup


    def _show_error_message(self, message):
        """显示错误信息"""
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        ax.text(0.5, 0.5, f"Error: {message}",
                fontsize=8, ha='center', va='center',
                transform=ax.transAxes)
        self.canvas.draw()

    def _plot_data(self, ax, sam_list, data_dict):
        """绘制数据曲线并添加图例"""
        lines = []  # 存储所有线条对象
        labels = []  # 存储对应标签
        self.line_colors = {}

        for sam in sam_list:
            try:
                # 绘制曲线并保存引用
                x = data_dict[sam]["detector_focused"]["xvalue"].values[0]
                y = data_dict[sam]["detector_focused"]["histogram"].values[0]
                new_x = np.linspace(0.5, 5, 2048)
                new_y = self.reorganize_data(x,y,new_x)
                line, = ax.plot(new_x, new_y, linestyle='-', linewidth=0.5)


                # 添加图例标签
                lines.append(line)
                labels.append(f"{sam}")
                self.line_colors[sam] = line.get_color()


            except Exception as e:
                print(f"Error processing {sam}: {e}")
                traceback.print_exc()

        # 添加图例（仅在有多条曲线时）
        if len(lines) > 1:
            legend = ax.legend(
                lines,
                labels,
                loc='upper right',
                fontsize=6,  # 与坐标轴标签大小一致
                framealpha=0.5,
                handlelength=1.5,
                handletextpad=0.5,
                borderaxespad=0.5
            )
            # 设置图例边框线条宽度
            legend.get_frame().set_linewidth(0.5)

            # 调整布局避免图例遮挡
            self.figure.subplots_adjust(right=0.85)  # 为图例留出空间

        self.y_min_origin, y_max = self.ax.get_ylim()

    def reorganize_data(self,x,y,d_range):
        interp = interp1d(x, y, kind='linear', bounds_error=False, fill_value=0)
        I_interp = interp(d_range)
        I_interp /= np.max(I_interp)
        return I_interp

    def _run_previous_modules(self):
        """运行前置模块"""
        current_name = self.objectName()
        for i in range(self.parent.inner_layout.count()):
            module = self.parent.inner_layout.itemAt(i).widget()
            if module.objectName() == current_name:
                break
            if hasattr(module, 'run'):
                module.run()

