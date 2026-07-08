from utils.browse import browse
from utils.ui.BaseUI import CollapsibleWidget
from rongzai.algSvc.instrument.diffraction import calculate_neutron_data
from PyQt5.QtGui import QDoubleValidator
from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtCore import QEvent
import copy
import traceback


class substraction(CollapsibleWidget):
    def __init__(self, name, parent):
        super(substraction, self).__init__(name, "utils/ui/substraction.ui", parent)
        self.parent = parent

        self.validator = QDoubleValidator(-float('inf'), float('inf'), 8,
                                          self)  # 创建一个浮点数验证器，限制输入范围在 [0.0, +∞)，且最多允许 8 位小数
        self.validator.setNotation(QDoubleValidator.StandardNotation)  # 强制使用标准十进制表示法（避免科学计数法）

        # # 初始化状态变量
        # self._is_home_clicked = False
        # self._current_xlim = None
        # self._current_ylim = None

        # self.legend_visible = True  # 默认显示图例

        # 初始化浏览功能
        self.browse_run = browse()
        self.samload_button.clicked.connect(self._on_samload_clicked)
        self.bkgload_button.clicked.connect(self._on_bkgload_clicked)

        # # 设置Matplotlib图形
        # self.figure = Figure()
        # self.canvas = FigureCanvas(self.figure)
        # self.canvas.setStyleSheet("background-color: transparent;")

        # # 配置工具栏
        # self._setup_toolbar()

        # # 设置布局
        # layout = QtWidgets.QVBoxLayout()
        # layout.addWidget(self.canvas)
        # layout.addWidget(self.toolbar)
        # layout.setContentsMargins(0, 0, 0, 0)
        # layout.setSpacing(0)
        # self.graphicsView.setLayout(layout)

        # # 设置防抖定时器
        # self.update_timer = QTimer()
        # self.update_timer.setSingleShot(True)
        # self.update_timer.timeout.connect(self.compute_figure)

        # 连接滑块信号
        self.updating = False
        self.scale_text.setValidator(self.validator)
        self.scale.valueChanged.connect(self.update_label)
        self.scale_text.textChanged.connect(self.update_scale)
        # self.scale.valueChanged.connect(lambda: self.update_timer.start(50))
        self.scale.valueChanged.connect(self._notify_parent)

        # 禁用鼠标滚轮对 scale 的调整（鼠标放上去滚轮不应改变值）
        try:
            self.scale.installEventFilter(self)
        except Exception:
            pass

        # # 添加右键点击事件监听器
        # self.canvas.mpl_connect('button_press_event', self.on_right_click)

    # def on_right_click(self, event):
    #     # 检查是否是右键点击
    #     if event.button == 3:  # 3 表示右键
    #         # 创建右键菜单
    #         context_menu = QtWidgets.QMenu(self)
    #         toggle_legend_action = context_menu.addAction("Toggle Legend")
    #         toggle_legend_action.triggered.connect(self.toggle_legend)
    #
    #         # 将 Matplotlib 的坐标转换为 Qt 的全局坐标
    #         x = int(event.x)  # Matplotlib 事件中的 x 坐标
    #         y = int(self.canvas.height() - event.y)  # 转换为 Qt 的 y 坐标
    #         global_pos = self.canvas.mapToGlobal(QtCore.QPoint(x, y))
    #
    #         # 在鼠标位置显示菜单
    #         context_menu.exec_(global_pos)

    # def toggle_legend(self):
    #     try:
    #         # 切换图例可见性
    #         self.legend_visible = not self.legend_visible
    #         self.compute_figure()
    #
    #     except Exception as e:
    #         print(f"An error occurred: {e}")
    #         traceback.print_exc()  # 打印异常的堆栈跟踪

    # def _setup_toolbar(self):
    #     """配置Matplotlib工具栏"""
    #     self.toolbar = NavigationToolbar(self.canvas, self)
    #     self.toolbar.setIconSize(QtCore.QSize(16, 16))
    #
    #     # 隐藏不需要的按钮
    #     for action in self.toolbar.actions():
    #         if action.text() in ["Customize", "Subplots", "Save"]:
    #             action.setVisible(False)
    #
    #     # 自定义Home按钮行为
    #     home_action = self.toolbar.actions()[0]
    #     home_action.disconnect()
    #     home_action.triggered.connect(self._reset_view)

    def _on_samload_clicked(self):
        """处理样品加载按钮点击"""
        self.browse_run.select_utils(
            self.samload_text,
            [data['name'] for data in self.parent.data_list]
        )
        # self.compute_figure()

    def _on_bkgload_clicked(self):
        """处理背景加载按钮点击"""
        self.browse_run.select_utils(
            self.bkgload_text,
            [data['name'] for data in self.parent.data_list]
        )
        # self.compute_figure()

    # def _reset_view(self):
    #     """完全重置视图到自动缩放状态"""
    #     self._is_home_clicked = True
    #     if hasattr(self, 'ax'):
    #         self.ax.autoscale(enable=True)
    #         self.canvas.draw_idle()
    #     self._is_home_clicked = False

    def update_label(self):
        """更新缩放比例标签"""
        if not self.updating:
            self.updating = True
            try:
                value = self.scale.value()
                self.scale_text.setText(f"{value / 100:.2f}")
            finally:
                self.updating = False

    def update_scale(self):
        if not self.updating:
            self.updating = True
            try:
                new_value = float(self.scale_text.text())
                new_val_scaled = int(new_value * 100)
                new_val_scaled = max(min(new_val_scaled,self.scale.maximum()), self.scale.minimum())
                self.scale.setValue(new_val_scaled)
            except ValueError:
                pass  # 可以选择向用户显示错误
            finally:
                self.updating = False

    # def compute_figure(self):
    #     """计算并更新图形"""
    #     # 保存当前视图状态（如果不是Home操作）
    #     if hasattr(self, 'ax') and not self._is_home_clicked:
    #         self._current_xlim = self.ax.get_xlim()
    #         self._current_ylim = self.ax.get_ylim()
    #
    #     data_list_backup = copy.deepcopy(self.parent.data_list)
    #     try:
    #         # 执行前置模块
    #         self._run_previous_modules()
    #
    #         # 准备绘图
    #         self.figure.clear()
    #         ax = self.figure.add_subplot(111)
    #         ax.set_navigate(True)
    #
    #         # 获取数据
    #         sam_list = [s for s in self.samload_text.text().split('; ') if s]
    #         bkg_list = [b for b in self.bkgload_text.text().split('; ') if b]
    #         data_dict = {item['name']: item for item in self.parent.data_list}
    #
    #         if sam_list and bkg_list:
    #             self._plot_data(ax, sam_list, bkg_list, data_dict)
    #         else:
    #             ax.text(0.5, 0.5, "No valid sample/background pairs",
    #                     fontsize=8, ha='center', va='center',
    #                     transform=ax.transAxes)
    #
    #         # 应用视图状态
    #         if not self._is_home_clicked and self._current_xlim and self._current_ylim:
    #             ax.set_xlim(self._current_xlim)
    #             ax.set_ylim(self._current_ylim)
    #         else:
    #             ax.autoscale(enable=True)
    #
    #         # 添加y=0参考线
    #         ax.axhline(y=0, color='gray', linestyle='--', linewidth=0.5)
    #
    #         # 优化坐标轴显示
    #         ax.tick_params(axis='both', which='major', labelsize=6, pad=1)
    #         for spine in ax.spines.values():
    #             spine.set_linewidth(0.5)
    #
    #         # 调整布局
    #         self.figure.tight_layout(pad=0.5)
    #         self.figure.subplots_adjust(
    #             left=0.1, right=0.98,
    #             bottom=0.1, top=0.95
    #         )
    #
    #         self.ax = ax
    #         self.canvas.draw()
    #
    #     except Exception as e:
    #         self._show_error_message(str(e))
    #     finally:
    #         self.parent.data_list = data_list_backup

    # def _run_previous_modules(self):
    #     """运行前置模块"""
    #     current_name = self.objectName()
    #     for i in range(self.parent.inner_layout.count()):
    #         module = self.parent.inner_layout.itemAt(i).widget()
    #         if module.objectName() == current_name:
    #             break
    #         if hasattr(module, 'run'):
    #             module.run()

    # def _get_label(self, data_dict, name):
    #     label = data_dict[name]["runno"]
    #     if "time_slice" in data_dict[name]:
    #         label = label + "_" + data_dict[name]["time_slice"]
    #     label = label + "_" + data_dict[name]["detector"]
    #     return label
    #
    # def _plot_data(self, ax, sam_list, bkg_list, data_dict):
    #     """绘制数据曲线并添加图例"""
    #     lines = []  # 存储所有线条对象
    #     labels = []  # 存储对应标签
    #
    #     for sam in sam_list:
    #         for bkg in bkg_list:
    #             if data_dict[bkg]["detector"] == data_dict[sam]["detector"]:
    #                 try:
    #                     # 缩放背景数据
    #                     scale_factor = self.scale.value() / 100
    #                     data_dict[bkg]["detector_focused"]["histogram"].values *= scale_factor
    #                     data_dict[bkg]["detector_focused"]["error"].values *= scale_factor
    #
    #                     # 计算差值数据
    #                     data_dict[sam]["detector_focused"] = calculate_neutron_data(
    #                         'subtract',
    #                         data_dict[sam]["detector_focused"],
    #                         data_dict[bkg]["detector_focused"]
    #                     )
    #
    #                     # 绘制曲线并保存引用
    #                     x = data_dict[sam]["detector_focused"]["xvalue"].values[0]
    #                     y = data_dict[sam]["detector_focused"]["histogram"].values[0]
    #                     line, = ax.plot(x, y, linestyle='-', linewidth=0.5)
    #
    #                     # 添加图例标签
    #                     lines.append(line)
    #                     labels.append(f"{self._get_label(data_dict, sam)} - {self._get_label(data_dict, bkg)}")
    #
    #                 except Exception as e:
    #                     print(f"Error processing {sam}-{bkg}: {e}")
    #                     traceback.print_exc()
    #
    #     # 添加图例（仅在有多条曲线时）
    #     if len(lines) > 1 and self.legend_visible:
    #         legend = ax.legend(
    #             lines,
    #             labels,
    #             loc='upper right',
    #             fontsize=6,  # 与坐标轴标签大小一致
    #             framealpha=0.5,
    #             handlelength=1.5,
    #             handletextpad=0.5,
    #             borderaxespad=0.5
    #         )
    #         # 设置图例边框线条宽度
    #         legend.get_frame().set_linewidth(0.5)
    #
    #         # 调整布局避免图例遮挡
    #         self.figure.subplots_adjust(right=0.85)  # 为图例留出空间

    def _show_error_message(self, message):
        """显示错误信息"""
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        ax.text(0.5, 0.5, f"Error: {message}",
                fontsize=8, ha='center', va='center',
                transform=ax.transAxes)
        self.canvas.draw()

    def run(self):
        """执行计算但不更新图形"""
        try:
            if self.toggle_button.isChecked():
                sam_list = [s for s in self.samload_text.text().split('; ') if s]
                bkg_list = [b for b in self.bkgload_text.text().split('; ') if b]
                data_dict = {item['name']: item for item in self.parent.data_list}
                if self.check_load_text(sam_list, data_dict, "sam") is False:
                    return
                if self.check_load_text(bkg_list, data_dict, "Sample Bkg") is False:
                    return
                if sam_list and bkg_list:
                    for sam in sam_list:
                        for bkg in bkg_list:
                            if bkg in data_dict.keys():
                                if data_dict[bkg]["detector"] == data_dict[sam]["detector"]:
                                    backup = copy.deepcopy(data_dict[bkg]["detector_focused"])
                                    scale = self.scale.value() / 100
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

    def eventFilter(self, obj, event):
        """拦截对 `self.scale` 的 Wheel 事件，防止滚轮调整滑块值。"""
        try:
            if obj is getattr(self, 'scale', None) and event.type() == QEvent.Wheel:
                return True
        except Exception:
            pass
        return super(substraction, self).eventFilter(obj, event)

    # def plot_data(self):
    #     """返回当前数据"""
    #     return copy.deepcopy(self.parent.data_list)

    def plot_data(self):
        if self.toggle_button.isChecked():
            plot_data = []
            sam_list = self.samload_text.text().split('; ')
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

    def get_config(self):
        """获取当前配置"""
        return {
            "samload_text": self.samload_text.text(),
            "bkgload_text": self.bkgload_text.text(),
            "scale": self.scale.value(),
            "is_use": self.toggle_button.isChecked()
        }

    def set_config(self, config):
        """设置配置"""
        # 临时阻塞信号
        self.samload_text.blockSignals(True)
        self.bkgload_text.blockSignals(True)
        self.scale.blockSignals(True)

        try:
            self.samload_text.setText(config.get("samload_text", ""))
            self.bkgload_text.setText(config.get("bkgload_text", ""))
            self.scale.setValue(config.get("scale", 100))
            self.toggle_button.setChecked(config.get("is_use", False))
        finally:
            # 恢复信号
            self.samload_text.blockSignals(False)
            self.bkgload_text.blockSignals(False)
            self.scale.blockSignals(False)
            self.update_label()