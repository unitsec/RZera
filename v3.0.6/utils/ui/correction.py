from PyQt5.uic import loadUi
from PyQt5 import QtWidgets, QtCore
import traceback, copy
from utils.browse import browse
from PyQt5.QtGui import QDoubleValidator
# from rongzai.algSvc.instrument.diffraction import correct_abs_ms,calculate_material_property
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import (
    FigureCanvasQTAgg as FigureCanvas,
    NavigationToolbar2QT as NavigationToolbar
)
# from rongzai.algSvc.neutron.unit_convert_nd import UnitConvertNeutronData
from PyQt5.QtCore import QTimer


class correction(QtWidgets.QWidget):
    def __init__(self, parent):
        super(correction, self).__init__(parent)
        loadUi("utils/ui/correction.ui", self)
        self.parent = parent

        # 初始化状态变量
        self._is_home_clicked = False
        self._current_xlim = None
        self._current_ylim = None

        self._setup_validators() # 设置输入验证器

        # 初始化correction开关
        self.is_correction.stateChanged.connect(self.toggle_style)
        self.is_correction.setChecked(False)

        # 初始化浏览功能
        self.browse_run = browse()
        self.select_button.clicked.connect(self._on_select_clicked)

        # 设置Matplotlib图形
        self.figure = Figure()
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setStyleSheet("background-color: transparent;")

        # 配置工具栏
        self._setup_toolbar()

        # 设置布局
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.canvas)
        layout.addWidget(self.toolbar)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.graphicsView.setLayout(layout)

        # 设置防抖定时器
        self.update_timer = QTimer()
        self.update_timer.setSingleShot(True)
        self.update_timer.timeout.connect(self.compute_figure)

        # 连接滑块信号
        self.scale.valueChanged.connect(self.update_scale_label)
        self.scale.valueChanged.connect(self.update_num_density_label)
        self.scale.valueChanged.connect(lambda: self.update_timer.start(50))
        self.scale.valueChanged.connect(self._notify_parent)

        # 单位转换工具
        self.unit_cvt = UnitConvertNeutronData()

    def toggle_style(self):
        if self.is_correction.isChecked():
            # Set active style
            self.setStyleSheet(f"QFrame#correction {{ background-color: lightblue; border: 1px solid black; }}")
        else:
            # Set inactive style
            self.setStyleSheet(f"QFrame#correction {{ background-color: lightgrey; }}")

    def _setup_validators(self):
        """设置输入验证器"""
        validator = QDoubleValidator(0.0, float('inf'), 8, self)
        validator.setNotation(QDoubleValidator.StandardNotation)

        self.mass.setValidator(validator)
        self.mass.setText("1.0")
        self.sam_height.setValidator(validator)
        self.sam_height.setText("3.0")
        self.radius_text.setValidator(validator)
        self.radius_text.setText("0.5")
        self.beam_height.setValidator(validator)
        self.beam_height.setText("3.0")
        self.num_density_text.setValidator(validator)
        self.num_density_text.setText("0.01")
        self.num_density_check.stateChanged.connect(lambda state: self.num_density_text.setEnabled(state == 2))
        self.num_density_check.setChecked(False)

        self.mass.textChanged.connect(self.update_num_density_label)
        self.sam_height.textChanged.connect(self.update_num_density_label)
        self.radius_text.textChanged.connect(self.update_num_density_label)
        self.beam_height.textChanged.connect(self.update_num_density_label)
        self.num_density_check.stateChanged.connect(lambda: self.update_timer.start(50))

    def _setup_toolbar(self):
        """配置Matplotlib工具栏"""
        self.toolbar = NavigationToolbar(self.canvas, self)
        self.toolbar.setIconSize(QtCore.QSize(16, 16))

        # 隐藏不需要的按钮
        for action in self.toolbar.actions():
            if action.text() in ["Customize", "Subplots", "Save"]:
                action.setVisible(False)

        # 自定义Home按钮行为
        home_action = self.toolbar.actions()[0]
        home_action.disconnect()
        home_action.triggered.connect(self._reset_view)

    def _on_select_clicked(self):
        """处理选择按钮点击"""
        self.browse_run.select_utils(
            self.select_text,
            [data['name'] for data in self.parent.data_list]
        )
        self.compute_figure()

    def _reset_view(self):
        """完全重置视图到自动缩放状态"""
        self._is_home_clicked = True
        if hasattr(self, 'ax'):
            self.ax.autoscale(enable=True)
            self.canvas.draw_idle()
        self._is_home_clicked = False

    def update_scale_label(self):
        """更新缩放比例标签"""
        value = self.scale.value()
        self.scale_value.setText(f"{value / 100:.2f}")

    def update_num_density_label(self):
        try:
            info = self._get_correction_info()
            cal_info = calculate_material_property(info)
            cal_num_density = cal_info["density_num"]
            value = self.scale.value()
            self.num_density_label.setText(f"Calculated Num Density:{cal_num_density*value/100:.6f} Å⁻³")
        except:
            self.num_density_label.setText(f"Calculated Num Density:0.000000 Å⁻³")

    def compute_figure(self):
        """计算并更新图形"""
        # 保存当前视图状态（如果不是Home操作）
        if hasattr(self, 'ax') and not self._is_home_clicked:
            self._current_xlim = self.ax.get_xlim()
            self._current_ylim = self.ax.get_ylim()

        data_list_backup = copy.deepcopy(self.parent.data_list)
        try:
            # 执行前置模块
            self._run_previous_modules()

            # 准备绘图
            self.figure.clear()
            ax = self.figure.add_subplot(111)
            ax.set_navigate(True)

            # 获取数据
            name_list = [n for n in self.select_text.text().split('; ') if n]
            data_dict = {item['name']: item for item in self.parent.data_list}

            if name_list:
                self._plot_data(ax, name_list, data_dict)
            else:
                ax.text(0.5, 0.5, "No data selected",
                        fontsize=8, ha='center', va='center',
                        transform=ax.transAxes)

            # 应用视图状态
            if not self._is_home_clicked and self._current_xlim and self._current_ylim:
                ax.set_xlim(self._current_xlim)
                ax.set_ylim(self._current_ylim)
                ax.autoscale_view(scalex=False, scaley=False)
            else:
                ax.autoscale(enable=True)

            # 添加y=0参考线
            ax.axhline(y=0, color='gray', linestyle='--', linewidth=0.5)

            # 优化坐标轴显示
            ax.tick_params(axis='both', which='major', labelsize=6, pad=1)
            for spine in ax.spines.values():
                spine.set_linewidth(0.5)

            # 调整布局
            self.figure.tight_layout(pad=0.5)
            self.figure.subplots_adjust(
                left=0.1, right=0.98,
                bottom=0.1, top=0.95
            )

            self.ax = ax
            self.canvas.draw()

        except Exception as e:
            self._show_error_message(str(e))
        finally:
            self.parent.data_list = data_list_backup

    def _run_previous_modules(self):
        """运行前置模块"""
        current_name = self.objectName()
        for i in range(self.parent.inner_layout.count()):
            module = self.parent.inner_layout.itemAt(i).widget()
            if module.objectName() == current_name:
                break
            if hasattr(module, 'run'):
                module.run()

    def _plot_data(self, ax, name_list, data_dict):
        """绘制数据曲线并添加图例"""
        lines = []
        labels = []
        correction_info = self._get_correction_info()
        if self.num_density_check.isChecked():
            correction_info["density_num"] = float(self.num_density_text.text())

        for name in name_list:
            try:
                if name in data_dict.keys():
                    dataset = data_dict[name]["detector_focused"]

                    # 单位转换和校正计算
                    dataset = self.unit_cvt.run(dataset, "wavelength")
                    dataset = correct_abs_ms(dataset, correction_info)
                    dataset = self.unit_cvt.run(dataset, "dspacing")

                    # 确保数据有效
                    x = dataset["xvalue"].values[0]
                    y = dataset["histogram"].values[0]

                    if len(x) == 0 or len(y) == 0:
                        print(f"Warning: Empty data for {name}")
                        continue

                    # 绘制曲线
                    line, = ax.plot(x, y, linestyle='-', linewidth=0.5)
                    lines.append(line)
                    labels.append(name)

                    # 调试输出数据范围
                    # print(f"Data range for {name}: x=[{min(x):.2f}, {max(x):.2f}], y=[{min(y):.2f}, {max(y):.2f}]")

            except Exception as e:
                print(f"Error processing {name}: {e}")
                traceback.print_exc()

        # 添加图例（仅在有多条曲线时）
        if len(lines) > 1:
            legend = ax.legend(
                lines, labels,
                loc='upper right',
                fontsize=6,
                framealpha=0.5
            )
            legend.get_frame().set_linewidth(0.5)
            self.figure.subplots_adjust(right=0.85)

        # 强制更新视图范围（如果数据有效）
        if lines:
            ax.relim()
            ax.autoscale_view()

    def _get_correction_info(self):
        """获取校正参数"""
        return {
            "sample_name": self.sample_name.text(),
            "mass": float(self.mass.text()),
            "volume": {
                "type": "cylinder",
                "height": float(self.sam_height.text()),
                "radius": float(self.radius_text.text()),
                "beam_height": float(self.beam_height.text()),
                "thickness": 0},
            "scale": self.scale.value() / 100
        }

    def _show_error_message(self, message):
        """显示错误信息"""
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        ax.text(0.5, 0.5, f"Error: {message}",
                fontsize=8, ha='center', va='center',
                transform=ax.transAxes)
        self.canvas.draw()

    def _notify_parent(self):
        """通知父窗口数据已更新"""
        if hasattr(self.parent, 'module_value_changed'):
            self.parent.module_value_changed(self)



    def run(self):
        """执行计算但不更新图形"""
        if not self.is_correction.isChecked():
            return

        try:
            correction_info = self._get_correction_info()
            if self.num_density_check.isChecked():
                correction_info["density_num"] = float(self.num_density_text.text())
            name_list = [n for n in self.select_text.text().split('; ') if n]
            data_dict = {item['name']: item for item in self.parent.data_list}

            for name in name_list:
                dataset = data_dict[name]["detector_focused"]
                dataset = self.unit_cvt.run(dataset, "wavelength")
                dataset = correct_abs_ms(dataset, correction_info)
                dataset = self.unit_cvt.run(dataset, "dspacing")
                data_dict[name]["detector_focused"] = dataset
                data_dict[name]["correction_info"] = correction_info

        except Exception as e:
            print(f"Error in run(): {e}")
            traceback.print_exc()

    def get_config(self):
        """获取当前配置"""
        return {
            "is_correction": self.is_correction.isChecked(),
            "select_text": self.select_text.text(),
            "sample_name": self.sample_name.text(),
            "mass": self.mass.text(),
            "radius": self.radius_text.text(),
            "sam_height": self.sam_height.text(),
            "beam_height": self.beam_height.text(),
            "scale": self.scale.value(),
        }

    def set_config(self, config):
        """设置配置"""
        self.is_correction.setChecked(config.get("is_correction", False))
        self.select_text.setText(config.get("select_text", ""))
        self.sample_name.setText(config.get("sample_name", ""))
        self.mass.setText(config.get("mass", "1.0"))
        self.radius_text.setText(config.get("radius", "0.5"))
        self.sam_height.setText(config.get("sam_height", "3.0"))
        self.beam_height.setText(config.get("beam_height", "3.0"))
        self.scale.setValue(config.get("scale", 100))

