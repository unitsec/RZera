from PyQt5.uic import loadUi
from PyQt5 import QtWidgets,QtCore
import traceback
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QIntValidator
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from utils.helper import get_resource_path
from rongzai.dataSvc import read_dataset
import numpy as np
import os


def apply_smart_legend(ax, legend_size=7, ncol_override=None, loc_override=None):
    """图例始终放在图内，避免压缩绘图区域。"""
    handles, labels = ax.get_legend_handles_labels()
    if not handles:
        return None

    legend_loc = loc_override if loc_override is not None else 'best'

    if ncol_override is not None:
        ncol = max(1, min(int(ncol_override), 6))
        legend = ax.legend(
            handles,
            labels,
            fontsize=legend_size,
            ncol=ncol,
            loc=legend_loc,
            borderaxespad=0.3,
            labelspacing=0.3,
            handlelength=1.5,
            columnspacing=1.0,
            framealpha=0.9,
        )
        return legend

    # 线条较少时先让 matplotlib 自动选择相对不遮挡的位置
    if len(handles) <= 6:
        legend = ax.legend(handles, labels, fontsize=legend_size, ncol=2, loc=legend_loc, framealpha=0.9)
        return legend

    # 曲线较多时仍保持图内显示，通过多列和更紧凑排版减少遮挡面积
    item_count = len(handles)
    target_rows_per_col = 12
    ncol = int(np.ceil(item_count / float(target_rows_per_col)))
    ncol = max(2, min(ncol, 4))

    legend = ax.legend(
        handles,
        labels,
        fontsize=legend_size,
        ncol=ncol,
        loc=legend_loc,
        borderaxespad=0.3,
        labelspacing=0.3,
        handlelength=1.5,
        columnspacing=1.0,
        framealpha=0.9,
    )
    return legend

class plot_window(QtWidgets.QWidget):
    def __init__(self,plot_dict, parent):
        super(plot_window, self).__init__(parent)
        loadUi(get_resource_path("utils/ui/plot_window.ui"), self)

        # 配置分割器初始比例（左:右=4:1），并允许鼠标拖拽调整
        self.splitter.setChildrenCollapsible(False)
        self.splitter.setStretchFactor(0, 4)
        self.splitter.setStretchFactor(1, 1)
        QTimer.singleShot(0, self.init_splitter_sizes)

        # 存储完整的数据字典
        self.plot_dict = plot_dict
        self.plot_order = list(plot_dict.keys())
        # key -> 显示名（legend文案）
        self.legend_name_map = {k: k for k in self.plot_order}
        self._is_rebuilding_list = False

        # 存储当前显示的keys（用于检测新增项）
        self.current_keys = set(plot_dict.keys())
        self.legend_visible = True  # 默认显示图例
        self.legend_ncol_override = None
        self.legend_loc_override = None
        self.legend_size_override = None
        ################################ 初始化绘图区域 ######################################
        # 创建 Figure 和 FigureCanvas 对象
        self.figure = Figure()
        self.canvas = FigureCanvas(self.figure)
        self.ax = self.figure.add_subplot(111)

        # 将 FigureCanvas 添加到 graphicView 容器中
        self.graphicsView.setLayout(QtWidgets.QVBoxLayout())
        self.graphicsView.layout().addWidget(self.canvas)

        # 创建 NavigationToolbar 对象并添加到 graphicView 容器中
        self.toolbar = NavigationToolbar(self.canvas, self)
        # 自定义Home按钮行为
        home_action = self.toolbar.actions()[0]
        home_action.disconnect()
        home_action.triggered.connect(self.custom_home_behavior)
        self.graphicsView.layout().addWidget(self.toolbar)

        self.figure.tight_layout()  # 设置为紧凑布局
        self.figure.subplots_adjust(bottom=0.17)  # 可以调整这个值以设置适当的空隙

        # 添加右键点击事件监听器
        self.canvas.mpl_connect('button_press_event', self.on_right_click)
        self.canvas.mpl_connect('scroll_event', self.on_legend_scroll)
        self.canvas.mpl_connect('button_release_event', self.on_legend_release)

        ######################################### 配置 plot_list  #######################################################
        # 添加 "ALL" 条目到 sam_list 的第一行
        all_item = QtWidgets.QListWidgetItem("ALL")
        all_item.setData(Qt.UserRole, "__ALL__")
        all_item.setFlags((all_item.flags() | Qt.ItemIsUserCheckable) & ~Qt.ItemIsDragEnabled & ~Qt.ItemIsDropEnabled)
        all_item.setCheckState(Qt.Unchecked)
        self.listWidget.insertItem(0, all_item)

        # 允许用户拖拽重排数据条目顺序（ALL固定在顶部）
        self.listWidget.setDragDropMode(QtWidgets.QAbstractItemView.InternalMove)
        self.listWidget.setDragDropOverwriteMode(False)
        self.listWidget.setDefaultDropAction(Qt.MoveAction)
        self.listWidget.setDragEnabled(True)
        self.listWidget.setAcceptDrops(True)
        self.listWidget.setDropIndicatorShown(True)
        self.listWidget.setEditTriggers(
            QtWidgets.QAbstractItemView.DoubleClicked |
            QtWidgets.QAbstractItemView.EditKeyPressed |
            QtWidgets.QAbstractItemView.SelectedClicked
        )
        
        self.listWidget.itemChanged.connect(self.handle_item_changed)  # 配置sam_list中item的变化
        self.listWidget.model().rowsMoved.connect(self.on_list_rows_moved)

        self.filterbox.itemChecked.connect(self.filter_items)
        self.filter_refresh.clicked.connect(lambda: self.refresh(self.filterbox, self.plot_dict))

        ######################################### 配置 plot_button  #######################################################
        self.data_plot = data_plot()  # 实例化data_plot
        self.plot_button.clicked.connect(self.on_plot_button_clicked)
        self.delete_button.clicked.connect(self.delete_item)
        self.import_button.clicked.connect(self.import_reduced_data)
        
        ######################################### 配置滑块  #######################################################
        self.default_stack_slider_max = 10
        self.stack_slider_steps = 100
        self.StackPlotSlider.setMinimum(0)
        self.StackPlotSlider.setMaximum(self.stack_slider_steps)
        self.StackPlotSlider.setSingleStep(1)
        self.SliderMaxText.setValidator(QIntValidator(1, 1000000, self))
        self.StackPlotSlider.valueChanged.connect(self.on_slider_changed)

    def init_splitter_sizes(self):
        """设置分割器初始宽度比例为4:1"""
        total_width = max(self.width(), 1000)
        self.splitter.setSizes([int(total_width * 0.8), int(total_width * 0.2)])

    def get_stack_slider_max(self):
        """获取当前偏移上限，空值使用默认值"""
        text = self.SliderMaxText.text().strip()
        if text == "":
            return float(self.default_stack_slider_max)
        else:
            try:
                slider_max = float(text)
                if slider_max <= 0:
                    return float(self.default_stack_slider_max)
                return slider_max
            except ValueError:
                return float(self.default_stack_slider_max)

    def get_current_stack_offset(self):
        """将滑块位置(0~100)映射到偏移值(0~max)"""
        slider_ratio = self.StackPlotSlider.value() / float(self.stack_slider_steps)
        return slider_ratio * self.get_stack_slider_max()

    def on_plot_button_clicked(self):
        """绘图按钮点击事件处理"""
        setattr(self.data_plot, 'initialized', False)
        current_offset = self.get_current_stack_offset()
        self.data_plot.plot_data(self.listWidget, self.plot_dict, self.canvas, self.ax,
                                 self.legend_visible, y_offset=current_offset,
                                 legend_size_override=self.legend_size_override,
                                 legend_ncol_override=self.legend_ncol_override,
                                 legend_loc_override=self.legend_loc_override)

    def on_slider_changed(self, value):
        """滑块值变化事件处理"""
        value = self.get_current_stack_offset()
        # 只有在已经绘制过数据时才响应滑块变化
        if self.data_plot.initialized:
            self.data_plot.plot_data(self.listWidget, self.plot_dict, self.canvas, self.ax, 
                                     self.legend_visible, y_offset=value, clear_axis=True,
                                     legend_size_override=self.legend_size_override,
                                     legend_ncol_override=self.legend_ncol_override,
                                     legend_loc_override=self.legend_loc_override)

    def sync_plot_order_with_list(self):
        """根据当前listWidget顺序同步plot_order"""
        ordered_keys = []
        for index in range(1, self.listWidget.count()):
            item = self.listWidget.item(index)
            key = item.data(Qt.UserRole) or item.text()
            if key in self.plot_dict:
                ordered_keys.append(key)

        for key in self.plot_dict.keys():
            if key not in ordered_keys:
                ordered_keys.append(key)
        self.plot_order = ordered_keys

    def reorder_plot_dict_by_order(self):
        """按plot_order重建dict顺序"""
        self.plot_dict = {key: self.plot_dict[key] for key in self.plot_order if key in self.plot_dict}

    def on_list_rows_moved(self, *args):
        """处理列表拖拽排序，保持数据结构顺序同步"""
        if self._is_rebuilding_list:
            return

        # 兜底保证ALL始终在第一行
        if self.listWidget.count() > 0 and self.listWidget.item(0).text() != "ALL":
            for i in range(self.listWidget.count()):
                if self.listWidget.item(i).text() == "ALL":
                    self._is_rebuilding_list = True
                    all_item = self.listWidget.takeItem(i)
                    self.listWidget.insertItem(0, all_item)
                    self._is_rebuilding_list = False
                    break

        self.sync_plot_order_with_list()
        self.reorder_plot_dict_by_order()

        # 拖拽后若已绘图，则按新顺序立即重绘
        if self.data_plot.initialized:
            current_offset = self.get_current_stack_offset()
            self.data_plot.plot_data(self.listWidget, self.plot_dict, self.canvas, self.ax,
                                     self.legend_visible, y_offset=current_offset, clear_axis=True,
                                     legend_size_override=self.legend_size_override,
                                     legend_ncol_override=self.legend_ncol_override,
                                     legend_loc_override=self.legend_loc_override)

    def custom_home_behavior(self):
        """自定义的`Home`行为，仅重置视图范围，不重绘数据"""
        if self.data_plot.initial_xlim and self.data_plot.initial_ylim:
            self.ax.set_xlim(self.data_plot.initial_xlim)
            self.ax.set_ylim(self.data_plot.initial_ylim)
            self.canvas.draw()

    def redraw_current_plot(self):
        """按当前状态重绘，用于交互式更新图例布局。"""
        if not self.data_plot.initialized:
            return
        current_offset = self.get_current_stack_offset()
        self.data_plot.plot_data(
            self.listWidget,
            self.plot_dict,
            self.canvas,
            self.ax,
            self.legend_visible,
            y_offset=current_offset,
            clear_axis=True,
            legend_size_override=self.legend_size_override,
            legend_ncol_override=self.legend_ncol_override,
            legend_loc_override=self.legend_loc_override,
        )
    def _get_effective_legend_size(self):
        if self.legend_size_override is not None:
            return int(self.legend_size_override)
        return int(self.data_plot._get_font_config(self.canvas)["legend"])

    def set_legend_font_size(self):
        current_size = self._get_effective_legend_size()
        size, ok = QtWidgets.QInputDialog.getInt(
            self,
            "Legend Font Size",
            "Legend font size:",
            current_size,
            1,
            72,
            1,
        )
        if ok:
            self.legend_size_override = int(size)
            self.redraw_current_plot()

    def reset_legend_font_size(self):
        self.legend_size_override = None
        self.redraw_current_plot()

    def on_legend_scroll(self, event):
        """鼠标在图例上滚轮：调整图例列数，实现图例形状变化与自适应排列。"""
        if not self.legend_visible:
            return
        legend = self.ax.get_legend()
        if legend is None:
            return
        contains, _ = legend.contains(event)
        if not contains:
            return

        current_ncol = self.legend_ncol_override or getattr(legend, '_ncols', 1)
        if event.button == 'up':
            self.legend_ncol_override = min(6, int(current_ncol) + 1)
        elif event.button == 'down':
            self.legend_ncol_override = max(1, int(current_ncol) - 1)
        else:
            return

        self.legend_loc_override = getattr(legend, '_loc', self.legend_loc_override)
        self.redraw_current_plot()

    def on_legend_release(self, event):
        """拖动图例后记录位置，保证重绘后仍保持用户拖动结果。"""
        if event.button != 1:
            return
        legend = self.ax.get_legend()
        if legend is None:
            return
        self.legend_loc_override = getattr(legend, '_loc', self.legend_loc_override)

    def reset_legend_layout(self):
        """重置图例布局为自动模式。"""
        self.legend_ncol_override = None
        self.legend_loc_override = None
        self.redraw_current_plot()


    def update_plot_data(self, new_plot_dict):
        """智能更新绘图数据并刷新列表"""
        try:
            # 1. 合并数据字典
            updated = False
            new_keys = set(new_plot_dict.keys())
            # print("new_keys:", new_keys)
            # print("old_keys:", self.plot_dict.keys())

            # 更新或添加现有项
            for key in new_keys:
                if key in self.plot_dict:
                    # 检查数据是否实际发生变化
                    if not self._data_equal(self.plot_dict[key], new_plot_dict[key]):
                        self.plot_dict[key] = new_plot_dict[key]
                        updated = True
                else:
                    # 添加新项
                    # print("add new key：", key)
                    self.plot_dict[key] = new_plot_dict[key]
                    self.plot_order.append(key)
                    updated = True

            self.reorder_plot_dict_by_order()

            # 2. 更新列表控件（如果有新增key）
            if new_keys - self.current_keys:
                # print("entered setup plot keys")
                self.setup_plot_list()
                self.current_keys = self.current_keys.union(new_keys)
                # self.current_keys = new_keys
            # if updated:
            #     # 数据更新但无新增key，只需重绘
            self.data_plot.plot_data(self.listWidget, self.plot_dict, self.canvas, self.ax,
                                     self.legend_visible, clear_axis=True,
                                     legend_size_override=self.legend_size_override,
                                     legend_ncol_override=self.legend_ncol_override,
                                     legend_loc_override=self.legend_loc_override)


        except Exception as e:
            print(f"Error updating plot data: {e}")
            traceback.print_exc()

    def _data_equal(self, data1, data2):
        """比较两个数据项是否相同"""
        try:
            return np.array_equal(data1[0], data2[0]) and np.array_equal(data1[1], data2[1]) and np.array_equal(data1[2], data2[2])
        except:
            return False

    def on_right_click(self, event):
        # 检查是否是右键点击
        if event.button == 3:  # 3 表示右键
            # 创建右键菜单
            context_menu = QtWidgets.QMenu(self)
            toggle_legend_action = context_menu.addAction("Toggle Legend")
            toggle_legend_action.triggered.connect(self.toggle_legend)
            reset_legend_action = context_menu.addAction("Reset Legend Layout")
            reset_legend_action.triggered.connect(self.reset_legend_layout)
            legend_font_action = context_menu.addAction("Set Legend Font Size")
            legend_font_action.triggered.connect(self.set_legend_font_size)
            reset_legend_font_action = context_menu.addAction("Reset Legend Font Size")
            reset_legend_font_action.triggered.connect(self.reset_legend_font_size)

            # 将 Matplotlib 的坐标转换为 Qt 的全局坐标
            x = int(event.x)  # Matplotlib 事件中的 x 坐标
            y = int(self.canvas.height() - event.y)  # 转换为 Qt 的 y 坐标
            global_pos = self.canvas.mapToGlobal(QtCore.QPoint(x, y))

            # 在鼠标位置显示菜单
            context_menu.exec_(global_pos)

    def toggle_legend(self):
        try:
            # 切换图例可见性
            self.legend_visible = not self.legend_visible
            if self.legend_visible:
                legend = apply_smart_legend(
                    self.ax,
                    legend_size=self._get_effective_legend_size(),
                    ncol_override=self.legend_ncol_override,
                    loc_override=self.legend_loc_override,
                )
                if legend is not None:
                    try:
                        legend.set_draggable(True, use_blit=True, update='loc')
                    except TypeError:
                        legend.set_draggable(True)
            else:
                if self.ax.get_legend():
                    self.ax.get_legend().remove()

            # 重绘图像
            self.canvas.draw()
        except Exception as e:
            print(f"An error occurred: {e}")
            traceback.print_exc()  # 打印异常的堆栈跟踪

    def delete_item(self):
        # 逆向遍历列表
        for index in range(self.listWidget.count() - 1, 0, -1):  # 从最后一个条目开始，跳过 "ALL" 条目
            item = self.listWidget.item(index)
            if item.checkState() == Qt.Checked:
                item_key = item.data(Qt.UserRole) or item.text()  # 稳定key
                item_to_remove = self.listWidget.takeItem(index)  # 移除条目并获取条目对象
                if item_key in self.plot_dict:
                    print("enter the delete plot dict step")
                    del self.plot_dict[item_key]  # 删除字典中的条目
                    self.plot_order = [k for k in self.plot_order if k != item_key]
                    self.legend_name_map.pop(item_key, None)
                    self.current_keys.remove(item_key)
                del item_to_remove  # 删除条目对象
        all_item = self.listWidget.item(0)
        self.listWidget.blockSignals(True)
        all_item.setCheckState(Qt.Unchecked)
        self.listWidget.blockSignals(False)

    def import_reduced_data(self):
        options = QtWidgets.QFileDialog.Options()
        file_paths, _ = QtWidgets.QFileDialog.getOpenFileNames(
            self,
            "Import Reduced/Focused Data",
            "",
            "Supported Files (*.txt *.dat *.xy *.xye *.gsa *.histogramIgor *.nc);;All Files (*)",
            options=options,
        )
        if not file_paths:
            return

        imported_plot_dict = {}
        failed_files = []

        for file_path in file_paths:
            try:
                if os.path.basename(file_path).lower().endswith("_record.txt"):
                    raise ValueError("record metadata file is not plottable")
                x, y = self._load_curve_from_file(file_path)
                xlabel, ylabel = self._get_import_axis_labels(file_path)
                key = self._build_import_key(file_path)
                imported_plot_dict[key] = [x, y, xlabel, ylabel]
                self.legend_name_map[key] = key
            except Exception as e:
                failed_files.append(f"{os.path.basename(file_path)}: {e}")

        if imported_plot_dict:
            self.update_plot_data(imported_plot_dict)

        if failed_files:
            QtWidgets.QMessageBox.warning(
                self,
                "Import Reduced Data",
                "Some files failed to import:\n" + "\n".join(failed_files),
            )

    def _load_curve_from_file(self, file_path):
        ext = os.path.splitext(file_path)[1].lower()

        if ext == ".nc":
            return self._load_curve_from_nc(file_path)

        if ext == ".histogramigor":
            return self._load_curve_from_histogram_igor(file_path)

        if ext == ".gsa":
            return self._load_curve_from_gsa(file_path)

        if ext == ".dat":
            return self._load_curve_from_fullprof_dat(file_path)

        # save_reduced_data 里的 txt/dat 以及通用的 xy/xye 文本格式
        if ext in {".txt", ".xy", ".xye"}:
            return self._load_curve_from_text_numeric(file_path)

        raise ValueError(f"unsupported file type: {ext}")

    def _load_curve_from_nc(self, file_path):
        dataset = read_dataset(file_path)
        if "xvalue" not in dataset or "histogram" not in dataset:
            raise ValueError("missing xvalue/histogram in nc")

        x = np.asarray(dataset["xvalue"].values, dtype=float).reshape(-1)
        y = np.asarray(dataset["histogram"].values, dtype=float).reshape(-1)
        if x.size == 0 or y.size == 0:
            raise ValueError("empty data")
        return x, y

    def _load_curve_from_histogram_igor(self, file_path):
        numeric_rows = []
        in_data_block = False
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            for raw_line in f:
                line = raw_line.strip()
                if not line:
                    continue
                upper_line = line.upper()
                if upper_line == "BEGIN":
                    in_data_block = True
                    continue
                if upper_line == "END":
                    break
                if not in_data_block:
                    continue
                parts = line.split()
                if len(parts) < 2:
                    continue
                try:
                    numeric_rows.append((float(parts[0]), float(parts[1])))
                except ValueError:
                    continue

        if not numeric_rows:
            raise ValueError("no numeric rows in histogramIgor")

        arr = np.asarray(numeric_rows, dtype=float)
        return arr[:, 0], arr[:, 1]

    def _load_curve_from_gsa(self, file_path):
        numeric_rows = []
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            for raw_line in f:
                line = raw_line.strip()
                if not line:
                    continue
                parts = line.split()

                if len(parts) < 3:
                    continue
                try:
                    x_val = float(parts[0])
                    y_val = float(parts[1])
                except ValueError:
                    continue
                numeric_rows.append((x_val, y_val))

        if not numeric_rows:
            raise ValueError("no numeric rows in gsa")

        arr = np.asarray(numeric_rows, dtype=float)
        x_gsa = arr[:, 0]
        y_scaled = arr[:, 1]

        # writeGSAS 中 x 不是原始 tof 网格，按写出关系递推恢复 tof：
        # x0 = tof0; xi = 0.5*(tofi + tof{i-1}) (i>=1)
        tof = np.zeros_like(x_gsa)
        tof[0] = x_gsa[0]
        for i in range(1, x_gsa.size):
            tof[i] = 2.0 * x_gsa[i] - tof[i - 1]

        # writeGSAS 保存的是 counts[i] * (tof[i+1]-tof[i])，做逐点反算
        if tof.size > 1:
            bin_width = np.diff(tof)
            # 最后一个点对应的宽度不可直接获得，使用前一个宽度近似
            last_width = bin_width[-1]
            bin_width = np.concatenate([bin_width, [last_width]])
        else:
            bin_width = np.array([1.0], dtype=float)

        safe_width = np.where(np.abs(bin_width) > 1e-12, bin_width, 1.0)
        y = y_scaled / safe_width

        return tof, y

    def _load_curve_from_fullprof_dat(self, file_path):
        numeric_rows = []
        scale_factor = 1.0
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            for raw_line in f:
                line = raw_line.strip()
                if not line:
                    continue

                # save_reduced_data -> DiffractionFormat.writeFP 会写该行
                if "multiplied by" in line.lower():
                    line_lower = line.lower()
                    marker = "multiplied by"
                    idx = line_lower.find(marker)
                    if idx != -1:
                        tail = line[idx + len(marker):].strip()
                        try:
                            scale_factor = float(tail)
                        except ValueError:
                            pass
                    continue

                parts = line.split()
                if len(parts) < 2:
                    continue
                try:
                    x_val = float(parts[0])
                    y_val = float(parts[1])
                except ValueError:
                    continue
                numeric_rows.append((x_val, y_val))

        if not numeric_rows:
            raise ValueError("no numeric rows in dat")

        arr = np.asarray(numeric_rows, dtype=float)
        x = arr[:, 0]
        y = arr[:, 1]
        # FullProf dat 里强度可能被乘过系数，导入时反算回原始强度
        if scale_factor not in (0.0, 1.0):
            y = y / scale_factor
        return x, y

    def _load_curve_from_text_numeric(self, file_path):
        # 先尝试标准 numpy 读取；失败后退化到逐行提取数字。
        try:
            data = np.loadtxt(file_path)
            return self._extract_xy_from_array(data)
        except Exception:
            pass

        numeric_rows = []
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            for raw_line in f:
                line = raw_line.strip()
                if not line:
                    continue
                parts = line.split()
                if len(parts) < 2:
                    continue
                try:
                    numeric_rows.append((float(parts[0]), float(parts[1])))
                except ValueError:
                    continue

        if not numeric_rows:
            raise ValueError("no numeric rows")

        arr = np.asarray(numeric_rows, dtype=float)
        return arr[:, 0], arr[:, 1]

    def _extract_xy_from_array(self, data):
        if data.ndim == 1:
            data = np.atleast_2d(data)

        if data.shape[1] < 2:
            raise ValueError("expected at least 2 columns")

        x = np.asarray(data[:, 0], dtype=float)
        y = np.asarray(data[:, 1], dtype=float)
        if x.size == 0 or y.size == 0:
            raise ValueError("empty data")
        return x, y

    def _get_import_axis_labels(self, file_path):
        ext = os.path.splitext(file_path)[1].lower()

        if ext in {".gsa", ".dat", ".histogramigor"}:
            return "TOF (us)", "Intensity"

        if ext in {".txt", ".xy", ".xye"}:
            return "d (Å)", "Intensity"

        # focused nc 默认仍用 d 轴展示
        if ext == ".nc":
            return "d (Å)", "Intensity"

        return "X", "Intensity"

    def _build_import_key(self, file_path):
        filename = os.path.basename(file_path)
        base_name, ext = os.path.splitext(filename)
        if base_name == "":
            base_name = "imported_curve"

        ext_label = ext.lower().lstrip(".")
        if ext_label:
            base_name = f"{base_name} [{ext_label}]"

        candidate = base_name
        suffix = 1
        while candidate in self.plot_dict:
            candidate = f"{base_name}_import{suffix}"
            suffix += 1
        return candidate

    def handle_item_changed(self, item):
        # 当任何条目的状态改变时，调用此方法
        if item.data(Qt.UserRole) == "__ALL__":
            # 如果是 "ALL" 条目，更新其他所有条目的状态
            new_state = item.checkState()
            self.listWidget.blockSignals(True)
            for index in range(1, self.listWidget.count()):
                other_item = self.listWidget.item(index)
                other_item.setCheckState(new_state)
                # print(f"Item: {other_item.text()}, State: {other_item.checkState()}")  # 调试打印
            self.listWidget.blockSignals(False)
        else:
            # 同步可编辑的legend显示名（不影响真实数据key）
            key = item.data(Qt.UserRole) or item.text()
            if key in self.plot_dict:
                self.legend_name_map[key] = item.text()
            # 如果是其他条目，检查是否需要更新 "ALL" 条目的状态
            self.update_all_checkbox_state()

    def update_all_checkbox_state(self):
        # 检查除了 "ALL" 之外的所有条目是否都被勾选
        all_checked = True
        for index in range(1, self.listWidget.count()):
            if self.listWidget.item(index).checkState() != Qt.Checked:
                all_checked = False
                break
        all_item = self.listWidget.item(0)
        self.listWidget.blockSignals(True)
        all_item.setCheckState(Qt.Checked if all_checked else Qt.Unchecked)
        self.listWidget.blockSignals(False)

    def setup_plot_list(self, filter=None):
        self._is_rebuilding_list = True
        # 记录除了第一项以外的现有项目的文本和勾选状态
        existing_items_status = {}
        for index in range(1, self.listWidget.count()):  # 从第二项开始
            item = self.listWidget.item(index)
            key = item.data(Qt.UserRole) or item.text()
            existing_items_status[key] = item.checkState()

        # 保存第一项 "ALL" 的引用，并从列表中移除其他所有项
        all_item = self.listWidget.takeItem(0)
        self.listWidget.clear()

        # 将 "ALL" 项添加回列表的第一项
        self.listWidget.insertItem(0, all_item)

        if not self.plot_order:
            self.plot_order = list(self.plot_dict.keys())

        names_in_order = [k for k in self.plot_order if k in self.plot_dict]
        for k in self.plot_dict.keys():
            if k not in names_in_order:
                names_in_order.append(k)
        self.plot_order = names_in_order
        self.reorder_plot_dict_by_order()

        # 遍历这个排序后的列表，按顺序添加项目到 QListWidget
        for name in names_in_order:
            display_name = self.legend_name_map.get(name, name)
            item = QtWidgets.QListWidgetItem(display_name)
            item.setData(Qt.UserRole, name)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable | Qt.ItemIsDragEnabled | Qt.ItemIsEditable)

            # 根据之前记录的状态设置勾选状态
            if name in existing_items_status:
                item.setCheckState(existing_items_status[name])
            else:
                item.setCheckState(Qt.Unchecked)

            self.listWidget.addItem(item)

        if filter is not None:
            self.filter_items(filter)

        self.update_all_checkbox_state()
        self._is_rebuilding_list = False

        self.refresh(self.filterbox, self.plot_dict)

    def filter_items(self, data):
        try:
            self._is_rebuilding_list = True
            # 记录除了第一项以外的现有项目的文本和勾选状态
            existing_items_status = {}
            for index in range(1, self.listWidget.count()):  # 从第二项开始
                item = self.listWidget.item(index)
                key = item.data(Qt.UserRole) or item.text()
                existing_items_status[key] = item.checkState()

            if not data:
                # 保存第一项 "ALL" 的引用，并从列表中移除其他所有项
                all_item = self.listWidget.takeItem(0)
                self.listWidget.clear()

                # 将 "ALL" 项添加回列表的第一项
                self.listWidget.insertItem(0, all_item)

                names_in_order = [k for k in self.plot_order if k in self.plot_dict]
                for k in self.plot_dict.keys():
                    if k not in names_in_order:
                        names_in_order.append(k)

                # 遍历这个排序后的列表，按顺序添加项目到 QListWidget
                for name in names_in_order:
                    display_name = self.legend_name_map.get(name, name)
                    item = QtWidgets.QListWidgetItem(display_name)
                    item.setData(Qt.UserRole, name)
                    item.setFlags(item.flags() | Qt.ItemIsUserCheckable | Qt.ItemIsDragEnabled | Qt.ItemIsEditable)

                    # 根据之前记录的状态设置勾选状态
                    if name in existing_items_status:
                        item.setCheckState(existing_items_status[name])
                    else:
                        item.setCheckState(Qt.Unchecked)

                    self.listWidget.addItem(item)

                self.update_all_checkbox_state()
                self._is_rebuilding_list = False
                return

            filter_list = []
            for key, value in self.plot_dict.items():  # 从第二项开始
                item = key.split('_')
                # 检查 data 中的所有元素是否都在 item 中
                if all(elem in item for elem in data):
                    filter_list.append(key)

            names_in_order = [k for k in self.plot_order if k in filter_list]

            # 保存第一项 "ALL" 的引用，并从列表中移除其他所有项
            all_item = self.listWidget.takeItem(0)
            self.listWidget.clear()

            # 将 "ALL" 项添加回列表的第一项
            self.listWidget.insertItem(0, all_item)

            # 遍历这个排序后的列表，按顺序添加项目到 QListWidget
            for name in names_in_order:
                display_name = self.legend_name_map.get(name, name)
                item = QtWidgets.QListWidgetItem(display_name)
                item.setData(Qt.UserRole, name)
                item.setFlags(item.flags() | Qt.ItemIsUserCheckable | Qt.ItemIsDragEnabled | Qt.ItemIsEditable)

                # 根据之前记录的状态设置勾选状态
                if name in existing_items_status:
                    item.setCheckState(existing_items_status[name])
                else:
                    item.setCheckState(Qt.Unchecked)

                self.listWidget.addItem(item)

            self.update_all_checkbox_state()
            self._is_rebuilding_list = False
        except Exception as e:
            self._is_rebuilding_list = False
            print(f"An error occurred: {e}")
            traceback.print_exc()  # 打印异常的堆栈跟踪

    def refresh(self, filterbox, list_dict):
        filterbox.clear()
        for name in list_dict.keys():
            name_elements = name.split('_')
            filter_elements = filterbox.get_item_names()
            for name_element in name_elements:
                if name_element not in filter_elements:
                    filterbox.add_item(name_element)
        self.filter_items([])

class data_plot:
    def __init__(self):
        self.initialized = False  # 标记是否已初始化
        self.initial_xlim = None
        self.initial_ylim = None

    def _get_font_config(self, canvas):
        """根据画布尺寸自适应字体大小，提升全屏可读性。"""
        width = max(canvas.width(), 1)
        height = max(canvas.height(), 1)

        # 以常规窗口尺寸为基准，放大时字体同步增大。
        scale = max(width / 1000.0, height / 700.0)
        scale = min(max(scale, 1.0), 2.8)

        return {
            "axis_label": int(round(12 * scale)),
            "tick": int(round(10 * scale)),
            "legend": int(round(7 * scale)),
        }

    def plot_data(self,plot_list,plot_list_dict,canvas,ax,legend_visible,clear_axis=True,y_offset=0,
                  legend_size_override=None, legend_ncol_override=None, legend_loc_override=None):
        try:
            font_cfg = self._get_font_config(canvas)

            # 保存当前的视图范围
            if self.initialized:
                xlim = ax.get_xlim()
                ylim = ax.get_ylim()

            if clear_axis:
                ax.clear()  # 根据 clear_axis 参数决定是否清除坐标轴上的图形和图例

            xlabel_set = set()
            ylabel_set = set()
            plot_count = 0
            for index in range(1, plot_list.count()):  # 从 1 开始，跳过 "ALL" 条目
                item = plot_list.item(index)
                # 如果当前条目被勾选，则绘制数据
                if item.checkState() == Qt.Checked:
                    key = item.data(Qt.UserRole) or item.text()
                    print(item.text())
                    offset_length = y_offset * plot_count
                    plot_count += 1
                    [x, y, xlabel, ylabel] = plot_list_dict[key]
                    xlabel_set.add(xlabel)
                    ylabel_set.add(ylabel)
                    self.draw_plot(
                        x, y, item.text(), xlabel_set, ylabel_set, ax,
                        offset_length, axis_label_size=font_cfg["axis_label"]
                    )  # 绘制数据

            # 添加“y=0”参考线
            ax.axhline(y=0, color='gray', linestyle='--', linewidth=0.5)

            # 同步放大坐标轴刻度字体
            ax.tick_params(axis='both', which='major', labelsize=font_cfg["tick"])

            if not self.initialized:
                self.initialized = True
                self.initial_xlim = ax.get_xlim()
                self.initial_ylim = ax.get_ylim()
            else:
                # 恢复之前的视图范围
                ax.set_xlim(xlim)
                ax.set_ylim(ylim)

            self.finalize_figure(
                ax,
                canvas,
                legend_visible,
                legend_size=legend_size_override if legend_size_override is not None else font_cfg["legend"],
                legend_ncol_override=legend_ncol_override,
                legend_loc_override=legend_loc_override,
            )  # Finalize the drawing and display
        except Exception as e:
            print(f'Failed to plot. Reason: {e}')
            traceback.print_exc()  # 打印异常的堆栈跟踪

    def draw_plot(self, x, y, label, xlabel_set, ylabel_set, ax, y_offset=0, axis_label_size=12):
        # 应用Y轴偏移
        y_adjusted = np.array(y) + y_offset
        ax.plot(x, y_adjusted, 'o-',label=label,markersize=3, linewidth=1)  # 在当前的坐标轴上绘制数据
        # 设置 X 轴和 Y 轴的标签名
        xlabel = '/'.join(xlabel_set)
        ylabel = '/'.join(ylabel_set)
        ax.set_xlabel(xlabel, fontdict={'fontsize': axis_label_size})
        ax.set_ylabel(ylabel, fontdict={'fontsize': axis_label_size})
        fig = ax.get_figure()
        fig.tight_layout()  # 设置为紧凑布局

    def finalize_figure(self,ax,canvas, legend_visible, legend_size=7,
                        legend_ncol_override=None, legend_loc_override=None):
        if legend_visible:
            legend = apply_smart_legend(
                ax,
                legend_size=legend_size,
                ncol_override=legend_ncol_override,
                loc_override=legend_loc_override,
            )
            if legend is not None:
                try:
                    legend.set_draggable(True, use_blit=True, update='loc')
                except TypeError:
                    legend.set_draggable(True)
        # else:
        #     print("No artists with labels found.")  # 如果没有，打印消息
        canvas.draw()  # 完成绘图