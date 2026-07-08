import os
import sys
import h5py
import json
import re
import numpy as np
from matplotlib import cm
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg') 
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas, NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
from io import BytesIO
from PyQt5 import QtWidgets, uic, QtCore, QtGui
from PyQt5.QtWidgets import QFileDialog, QMessageBox, QGraphicsScene, QGraphicsPixmapItem, QSizePolicy, QGraphicsRectItem
from PyQt5.QtGui import QImage, QPixmap, QPainter, QColor, QFont, QPen, QBrush, QLinearGradient
from PyQt5.QtCore import Qt, QRectF, QPointF, QTimer
from PyQt5.QtWidgets import QTextBrowser, QDialog, QVBoxLayout, QDialogButtonBox
from PyQt5.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsPixmapItem  # 导入所需类
from PyQt5.QtWidgets import QLabel, QLineEdit, QHBoxLayout, QPushButton, QListWidgetItem, QSpinBox
from rongzai.dataSvc.data_loader import load_histogram_data
from rongzai.algSvc.base.core_unitconvert import tof_to_wavelength as RZ_TOF_TO_WAVELENGTH
# 获取当前脚本所在目录: .../utils/ui
current_dir = os.path.dirname(os.path.abspath(__file__))

# 向上回退两级，得到项目根目录: .../rzera_offline-main/
project_root = os.path.dirname(os.path.dirname(current_dir))


# 帮助文档内容（HTML格式）
HELP_DOCUMENT = """
<!DOCTYPE html>
<html>
<head>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; line-height: 1.6; }
        h1 { color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px; }
        h2 { color: #3498db; margin-top: 20px; }
        h3 { color: #2c3e50; margin-top: 15px; }
        .step { background-color: #f8f9fa; border-left: 4px solid #3498db; padding: 10px; margin: 10px 0; }
        .note { background-color: #fff3cd; border-left: 4px solid #ffc107; padding: 10px; margin: 10px 0; }
        .warning { background-color: #f8d7da; border-left: 4px solid #dc3545; padding: 10px; margin: 10px 0; }
        .tip { background-color: #d1ecf1; border-left: 4px solid #17a2b8; padding: 10px; margin: 10px 0; }
        code { background-color: #f4f4f4; padding: 2px 5px; border-radius: 3px; font-family: 'Courier New', monospace; }
        ul { padding-left: 20px; }
    </style>
</head>
<body>
    <h1>2D-TOF数据显示器使用指南</h1>
    
    <h2>概述</h2>
    <p>本软件用于显示中子衍射实验的2D TOF（飞行时间）数据。主要功能包括：</p>
    <ul>
        <li>加载和处理NeXus格式的数据文件</li>
        <li>显示探测器模块的2D热图</li>
        <li>选择感兴趣区域并提取TOF谱</li>
        <li>保存数据和图像</li>
    </ul>
    
    <h2>基本工作流程</h2>
    
    <div class="step">
        <h3>步骤1：选择仪器</h3>
        <p>在"仪器"下拉菜单中选择对应的实验仪器（如BL05、BL09、BL15、BL16）。</p>
        <p>软件会自动扫描该仪器的配置文件。</p>
    </div>
    
        # 切换 scene 前先清理 ROI 图元，避免持有已删除的 C++ 对象引用。
        self._safe_remove_scene_item('roi_graphics_item')
        self._safe_remove_scene_item('roi_hint_item')
    <div class="step">
        <h3>步骤2：加载数据文件</h3>
        <p>点击"Load"按钮，选择NeXus格式（通常为detector.nxs）的数据文件。</p>
        <p>软件会自动读取文件中的数据信息。</p>
    </div>
    
    <div class="step">
        <h3>步骤3：选择模块</h3>
        <p>在"module"下拉菜单中选择要显示的探测器模块。</p>
        <p>软件会加载对应的配置文件和实验数据，并显示2D热图。</p>
    </div>
    
    <div class="step">
        <h3>步骤4：选择感兴趣区域</h3>
        <p>点击"Select Region"按钮进入区域选择模式。</p>
        <p>在左侧热图中拖动鼠标选择矩形区域。</p>
        <p>右侧会显示该区域的TOF谱。</p>
    </div>
    
    <div class="step">
        <h3>步骤5：分析TOF谱</h3>
        <p>使用"Set Tof range"按钮调整TOF谱的显示范围。</p>
        <p>使用"Save"按钮保存TOF谱数据或图像。</p>
    </div>
    
    <h2>数据格式说明</h2>
    
    <h3>输出文件</h3>
    <ul>
        <li><strong>图像文件：</strong>PNG格式，保存TOF谱图</li>
        <li><strong>数据文件：</strong>文本格式，保存TOF谱数据</li>
    </ul>
    
    <div class="warning">
        <h3>注意事项</h3>
        <ul>
            <li>加载大文件时可能需要等待几秒钟</li>
            <li>区域选择时请确保已加载数据</li>
            <li>保存数据前请确保已生成TOF谱</li>
        </ul>
    </div>
    
    <div class="note">
        <h3>技术支持</h3>
        <p>如遇问题，请联系：</p>
        <ul>
            <li>技术支持邮箱：gufy@ihep.ac.cn</li>
            <li>文档版本：v1.0</li>
            <li>最后更新：2025年12月16日</li>
        </ul>
    </div>
</body>
</html>
"""

class Tof2dWindow(QtWidgets.QMainWindow):
    def __init__(self,parent=None):
        super(Tof2dWindow, self).__init__(parent)
        
        # 加载UI文件
        ui_path = os.path.join(os.path.dirname(__file__), 'Tof_2d_window.ui')  # 请确保文件名正确
        uic.loadUi(ui_path, self)

        # 设置窗口标题和大小
        self.setWindowTitle("2D-Tof显示窗口")
        self.resize(1600, 1200)
        
        # 连接信号
        self.pushButton_how.clicked.connect(self.show_help_document)
        self.comboBox_instrument.currentTextChanged.connect(self.on_instrument_changed)
        self.pushButton_run.clicked.connect(self.load_nxs_file)
        self.moduleComboBox.currentTextChanged.connect(self.on_module_combo_changed)
        self.pushButton_Select.clicked.connect(self.toggle_roi_selection_mode)
        self.pushButton_pixel.clicked.connect(self.select_single_pixel_and_plot)
        self.pushButton_manual_roi.clicked.connect(self.show_manual_roi_dialog)
        self.pushButton_Tof.clicked.connect(self.show_roi_tof_range_dialog)
        self.pushButton_save.clicked.connect(self.save_roi_data)
        self.comboBox_xunit.currentTextChanged.connect(self.on_xunit_changed)

        # 初始化变量
        self.current_file_path = None
        self.current_module_data = None
        self.current_instrument = None
        self.current_neutron_data = None
        self.current_data_min = None
        self.current_data_max = None
        self.current_data_shape = None
        self.current_pixel_ids = None
        self.current_pixel_coords = None 
        self.current_counts_2d = None      # 保存当前 counts_2d
        self.current_pixel_id_2d = None    # 保存当前 pixel_id_2d 布局
        self.current_roi_pixel_ids = None  
        self.roi_selection_mode = False
        self.roi_start = None
        self.roi_graphics_item = None
        self.roi_hint_item = None           # 选择起点（QPoint）
        self.tof_us = None          
        self.pixel_tof = None
        self.roi_tof_us = None          
        self.roi_tof_counts = None         
        self.original_roi_tof_us = None
        self.original_roi_tof_counts = None

        # 当前显示的数据（可被裁剪）
        self.current_display_tof_us = None
        self.current_display_tof_counts = None
        self.current_plot_pixel_id = None
        self.current_l1 = 10.0  # 当前模块的第一飞行距离（m），用于 TOF→波长换算
        self.heatmap_pixmap_item = None
        
        # 计算项目根目录
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(os.path.dirname(current_dir))  # 回退到 rzera_offline-main/

        # TXT 路径（存放 .txt 模块文件的目录）
        self.txt_paths = {
            "BL05": [
                os.path.join(project_root, "param_data", "BL05", "instrumentFiles"),
            ],
            "BL09": [
                os.path.join(project_root, "param_data", "BL09", "instrumentFiles"),
            ],
            "BL15": [
                os.path.join(project_root, "param_data", "BL15", "instrumentFiles_big"),
                os.path.join(project_root, "param_data", "BL15", "instrumentFiles_small"),
            ],
            "BL16": [
                os.path.join(project_root, "param_data", "BL16", "instrumentFiles"),
            ],
        }

        # JSON 路径（base 配置文件）
        self.json_paths = {
            "BL05": [
                os.path.join(project_root, "CSNS_Alg", "configure", "BL05_base.json"),
            ],
            "BL09": [
                os.path.join(project_root, "CSNS_Alg", "configure", "BL09_base.json"),
            ],
            "BL15": [
                os.path.join(project_root, "CSNS_Alg", "configure", "BL15_big_base.json"),
                os.path.join(project_root, "CSNS_Alg", "configure", "BL15_small_base.json"),
            ],
            "BL16": [
                os.path.join(project_root, "CSNS_Alg", "configure", "BL16_base.json"),
            ],
        }

        # 安装事件过滤器以捕获鼠标事件
        self.graphicsView_module.viewport().installEventFilter(self)

        # 用 FigureCanvas + NavigationToolbar 替换 graphicsView_region
        self.tof_figure = Figure()
        self.tof_canvas = FigureCanvas(self.tof_figure)
        self.tof_toolbar = NavigationToolbar(self.tof_canvas, self)
        tof_container = QtWidgets.QWidget()
        tof_container_layout = QtWidgets.QVBoxLayout(tof_container)
        tof_container_layout.setContentsMargins(0, 0, 0, 0)
        tof_container_layout.setSpacing(0)
        tof_container_layout.addWidget(self.tof_toolbar)
        tof_container_layout.addWidget(self.tof_canvas)
        old_region_widget = self.graphicsView_region
        old_region_widget.parent().layout().replaceWidget(old_region_widget, tof_container)
        old_region_widget.hide()
    
    def get_paths_by_instrument(self, bl_name):
        """
        根据仪器名称，获取 JSON 配置目录 和 TXT 数据目录
        返回: (json_dirs, txt_dirs)
        """
        json_dirs = self.json_paths.get(bl_name, [])
        txt_dirs = self.txt_paths.get(bl_name, [])
        return json_dirs, txt_dirs
    
    def load_all_json_path(self, json_file_paths):
        """
        加载多个 base JSON 配置文件（每个是一个完整路径），返回结构化字典。
        
        参数:
            json_file_paths (list): JSON 文件的完整路径列表，例如：
                ["/.../BL15_big_base.json", "/.../BL15_small_base.json"]
        
        返回:
            dict: 以配置类型为 key 的字典，例如：
                {
                    "big": { ...完整 JSON 内容... },
                    "small": { ...完整 JSON 内容... }
                }
        """
        json_dict = {}
        for path in json_file_paths:
            if not os.path.isfile(path):
                print(f"⚠️ JSON 配置文件不存在或不是文件: {path}")
                continue

            try:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)  # 保留原始 JSON 的全部内容（嵌套字典）
                
                # 根据文件名推断配置类型
                filename_lower = os.path.basename(path).lower()
                if 'big' in filename_lower:
                    key = 'big'
                elif 'small' in filename_lower:
                    key = 'small'
                else:
                    key = 'default'  # 适用于 BL05/BL09/BL16 等单配置仪器
                
                json_dict[key] = data  # 完整保留原始结构
                print(f"✅ 成功加载 base 配置 [{key}]: {path}")

            except json.JSONDecodeError as e:
                print(f"❌ JSON 格式错误 ({path}): {e}")
            except Exception as e:
                print(f"❌ 读取或解析失败 ({path}): {e}")

        return json_dict
    
    def load_all_txt_path(self, txt_dirs):
        """
        从多个目录中收集所有 .txt 文件，生成 {模块名: 文件路径} 的字典。
        
        例如：
            文件: /xxx/module10201.txt  →  key="module10201", value="/xxx/module10201.txt"
        
        参数:
            txt_dirs (list): 包含 .txt 文件的目录路径列表
        
        返回:
            dict: { "module10201": "/full/path/module10201.txt", ... }
        """
        txt_dict = {}
        for folder in txt_dirs:
            if not os.path.isdir(folder):
                print(f"⚠️ TXT 目录不存在或无效: {folder}")
                continue

            for filename in os.listdir(folder):
                if filename.endswith(".txt"):
                    # 去掉 .txt 后缀，得到模块名（如 "module10201"）
                    module_name = filename[:-4]  # 等价于 os.path.splitext(filename)[0]
                    full_path = os.path.join(folder, filename)
                    txt_dict[module_name] = full_path

        return txt_dict
    
    def on_instrument_changed(self, text):
        """用户选择 BL 后，加载 JSON 和 TXT 配置，并弹窗反馈结果"""
        self.current_instrument = text

        try:
            # 1. 获取路径
            json_files, txt_dirs = self.get_paths_by_instrument(text)

            if not json_files and not txt_dirs:
                raise FileNotFoundError(f"未配置 {text} 的 JSON 或 TXT 路径")

            # 2. 加载 JSON 配置（base 文件）
            self.json_dict = self.load_all_json_path(json_files)
            print(f"✅ 加载 {len(self.json_dict)} 个 JSON 配置")

            # 3. 加载 TXT 文件路径映射
            self.txt_dict = self.load_all_txt_path(txt_dirs)
            print(f"✅ 加载 {len(self.txt_dict)} 个 TXT 文件")

            # 4. 至少应有一个有效配置
            if len(self.json_dict) == 0 and len(self.txt_dict) == 0:
                raise RuntimeError(f"{text} 的所有配置文件均无效或无法读取")

            # ✅ 成功：弹出信息摘要
            summary_lines = [f"仪器: {text}", ""]

            # JSON 部分
            if self.json_dict:
                types = ", ".join(self.json_dict.keys())
                summary_lines.append(f"✅ 已加载 Base 配置类型: {types}")
            else:
                summary_lines.append("⚠️ 未加载任何 Base 配置")

            # TXT 部分
            if self.txt_dict:
                module_count = len(self.txt_dict)
                # 列出前 5 个模块名，避免太长
                sample_modules = list(self.txt_dict.keys())[:5]
                modules_str = ", ".join(sample_modules)
                if module_count > 5:
                    modules_str += f" ... (共 {module_count} 个)"
                summary_lines.append(f"📄 已加载 TXT 模块 ({module_count} 个):")
                summary_lines.append(f"   {modules_str}")
            else:
                summary_lines.append("⚠️ 未发现 TXT 模块文件")

            info_msg = "\n".join(summary_lines)
            QMessageBox.information(
                self,
                "配置加载成功",
                info_msg,
                QMessageBox.Ok
            )

        except Exception as e:
            error_msg = f"加载仪器配置失败：\n{str(e)}"
            print(f"❌ {error_msg}")
            # ❌ 失败：弹出错误对话框
            QMessageBox.critical(
                self,
                "配置加载错误",
                error_msg,
                QMessageBox.Ok
            )
            # 确保后续可安全调用
            self.json_dict = {}
            self.txt_dict = {}

    def load_nxs_file(self):
        """
        响应 pushButton_run 点击事件：
        弹出文件选择对话框，仅允许选择一个 .nxs 文件
        获取选中的文件路径，供后续处理
        """
        # 弹出单文件选择对话框
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择 NeXus (.nxs) 数据文件",
            "",  # 起始目录（可留空或设为上次路径）
            "NeXus Files (*.nxs);;All Files (*)"
        )

        if not file_path:
            # 用户取消了选择
            print("⚠️ 未选择 .nxs 文件")
            return

        # 确保是 .nxs 文件（虽然过滤器已限制，但可二次校验）
        if not file_path.lower().endswith('.nxs'):
            QMessageBox.warning(
                self,
                "文件类型错误",
                "请选择一个 .nxs 格式的 NeXus 数据文件。"
            )
            return

        print(f"✅ 已选择 .nxs 文件: {file_path}")

        # 👇 保存路径（如果后续需要）
        self.selected_nxs_file = file_path

        # 👇 更新模块下拉框
        self.update_module_combo_from_nxs(file_path)

    def update_module_combo_from_nxs(self, nxs_path):
        """
        从 .nxs 文件的 /csns/histogram_data/ 路径下读取所有 moduleXXX 子组，
        提取数字后缀（如 '10201'），并更新 self.moduleComboBox 的选项。
        
        Args:
            nxs_path (str): .nxs 文件路径
        """
        # 清空当前选项
        self.moduleComboBox.clear()

        try:
            with h5py.File(nxs_path, 'r') as f:
                histogram_group = f.get('/csns/histogram_data')
                if histogram_group is None:
                    print("⚠️ 路径 '/csns/histogram_data' 不存在于 .nxs 文件中")
                    self.moduleComboBox.addItem("❌ 无模块数据")
                    return

                # 获取所有子项名称（只取 Group 类型）
                all_keys = [name for name in histogram_group.keys() 
                            if isinstance(histogram_group[name], h5py.Group)]

                # 过滤出符合 module<数字> 格式的名称，并提取数字
                module_numbers = []
                pattern = re.compile(r'^module(\d+)$')
                for key in all_keys:
                    match = pattern.match(key)
                    if match:
                        num_str = match.group(1)
                        module_numbers.append(num_str)

                if not module_numbers:
                    print(f"⚠️ 在 '/csns/histogram_data' 中未找到任何 'module<数字>' 格式的子组")
                    self.moduleComboBox.addItem("❌ 未识别模块")
                    return

                # 排序（按数字大小，不是字符串）
                module_numbers.sort(key=int)

                # 添加到 ComboBox
                self.moduleComboBox.addItems(module_numbers)

                # 可选：默认选中第一个
                self.moduleComboBox.setCurrentIndex(0)

                print(f"✅ 成功加载 {len(module_numbers)} 个模块: {module_numbers}")

        except Exception as e:
            error_msg = f"读取 .nxs 模块失败: {e}"
            print("❌", error_msg)
            self.moduleComboBox.clear()
            self.moduleComboBox.addItem("❌ 读取错误")
            import traceback
            traceback.print_exc()

    def on_module_combo_changed(self, module_num: str):
        """当用户从 moduleComboBox 选择一个模块编号时调用"""
        if not module_num or not module_num.isdigit():
            return

        self.current_plot_pixel_id = None

        if not hasattr(self, 'selected_nxs_file'):
            QMessageBox.warning(self, "错误", "请先选择 .nxs 文件！")
            return

        # 调用处理函数
        self.process_nxs_data(self.selected_nxs_file, module_num)

    def _get_module_config(self, module_num: str) -> str:
        """根据模块编号返回对应的 .txt 配置文件路径"""
        full_module_name = f"module{module_num}"
        if full_module_name not in self.txt_dict:
            raise FileNotFoundError(f"未找到模块 {full_module_name} 对应的 .txt 配置文件")
        return self.txt_dict[full_module_name], full_module_name


    def _get_l1_distance(self, full_module_name: str) -> float:
        """从 json_dict 中查找模块所属配置，并返回 l1（第一飞行距离）"""
        l1 = 10.0  # 默认值
        found = False

        if hasattr(self, 'json_dict') and self.json_dict:
            for config_name, config in self.json_dict.items():
                pixel_info = config.get("pixel_info", [])
                if full_module_name in pixel_info:
                    l1_candidate = config.get("first_flight_distance")
                    if l1_candidate is not None:
                        l1 = float(l1_candidate)
                        found = True
                        print(f"✅ 从配置 '{config_name}' 读取 l1 = {l1} m")
                        break

            if not found:
                print(f"⚠️ 未在任何 base 配置的 pixel_info 中找到 {full_module_name}，使用默认 l1 = {l1} m")
        else:
            print("⚠️ 未加载 base JSON 配置，使用默认 l1 = 10.0 m")

        return l1


    def _load_neutron_histogram(
        self,
        nxs_path: str,
        txt_file_path: str,
        full_module_name: str,
        l1: float,
        x_offset: float = 0.0
    ):
        """调用底层函数加载中子直方图数据"""
        return load_histogram_data(
            hdf_file_list=[nxs_path],
            txt_file_path=txt_file_path,
            module=full_module_name,
            l1=l1,
            x_offset=x_offset
        )


    def process_nxs_data(self, nxs_path: str, module_num: str):
        """
        加载指定模块的中子 TOF 直方图数据，并返回 neutron_data 对象。
        
        Args:
            nxs_path (str): .nxs 文件路径
            module_num (str): 模块编号，如 '10502'
        
        Returns:
            neutron_data: 加载后的数据对象（通常包含 .y 或 .histogram 属性）
        
        Raises:
            Exception: 若加载失败
        """
        print("=" * 70)
        print(f"🔍 开始加载模块 module{module_num} 的数据...")
        print("=" * 70)

        try:
            # 1. 获取配置
            txt_file_path, full_module_name = self._get_module_config(module_num)
            print(f"✅ 使用 TXT 配置: {txt_file_path}")

            # 2. 获取 l1
            l1 = self._get_l1_distance(full_module_name)
            self.current_l1 = l1  # 保存供 TOF→波长换算使用

            # 3. 加载数据
            neutron_data = self._load_neutron_histogram(
                nxs_path=nxs_path,
                txt_file_path=txt_file_path,
                full_module_name=full_module_name,
                l1=l1
            )

            # 5. 获取几何配置
            geometry = self.extract_json_file(full_module_name)
            xpixels = geometry['xpixels']
            ypixels = geometry['ypixels']
            stepbyrow = geometry['stepbyrow']

            print(f"\n🔧 几何配置: {xpixels} × {ypixels}, stepbyrow='{stepbyrow}', start={geometry['start']}")

            # 6. 重塑为 2D
            pixel_id_2d = self.reshape_pixel_id_to_2d(neutron_data, geometry)  # 注意：如果你定义为类方法，用 self.

            pixel_counts = self.get_pixel_total_counts(neutron_data)
            counts_2d = self.map_counts_to_2d(pixel_id_2d, pixel_counts)
            self.pixel_tof, self.tof_us = self.get_pixel_histogram_with_id(neutron_data)
            # ✅ 保存数据供后续使用
            self.current_neutron_data = neutron_data
            self.current_counts_2d = counts_2d
            self.current_pixel_id_2d = pixel_id_2d

            self.display_counts_heatmap(counts_2d)

            # ✅ 新增：显示状态信息到 listWidget_stats
            full_module_name = f"module{module_num}"
            self.display_status_info(full_module_name)  # ← 关键！调用显示函数

            # ✅ 新增：追加统计信息（max/min）
            self.append_statistics_to_list()  # ← 新函数，见下文
            self.append_pixel_id_range_to_list()             # 新增：追加像素ID范围信息

            # 5. 调试打印
            print("\n✅ 2D counts 矩阵（左下/右上）:")
            print(f"左下角 (底行, 第0列): {counts_2d[-1, 0]}")
            print(f"右上角 (顶行, 最后列): {counts_2d[0, -1]}")
            print("底行前5个:", counts_2d[-1, :5])
            print("counts_2d shape:", counts_2d.shape)
            return neutron_data

        except Exception as e:
            error_msg = f"加载失败: {str(e)}"
            print("❌", error_msg)
            import traceback
            traceback.print_exc()
            raise  # 重新抛出异常，便于调用者处理

    def extract_neutron_data(self, neutron_data):
        """
        从 neutron_data (xarray.Dataset) 中提取核心数据，返回结构化字典。
        
        Args:
            neutron_data (xarray.Dataset): 由 process_nxs_data 返回的数据对象
            crop_tof_range (tuple, optional): (tof_min, tof_max) in μs，用于裁剪 TOF 范围
            crop_pixel_range (tuple, optional): (start_idx, end_idx)，用于裁剪像素范围（按索引）
        
        Returns:
            dict: 包含 pixel_id, tof_us, histogram, module_name 的字典
        """
        # 1. 提取 pixel_id
        pixel_id = neutron_data.positions.coords['pixel'].values  # (N_pixels,)
        
        # 2. 提取 TOF 轴（所有像素共享，取第0行）
        tof_us = neutron_data.xvalue.values[0, :]  # (N_tof,)
        
        # 3. 提取 histogram
        histogram = neutron_data.histogram.values  # (N_pixels, N_tof)
        
        # 4. 模块名
        module_name = neutron_data.attrs.get("name", "unknown")
        
        return {
            "pixel_id": pixel_id,          # (N_pixels,)
            "tof_us": tof_us,              # (N_tof,)
            "histogram": histogram,        # (N_pixels, N_tof)
            "module_name": module_name,
            "shape": histogram.shape
        }
        
    def extract_json_file(self, module_name):
        """
        从 self.json_dict 中提取指定模块的像素几何信息和所属配置的全局元数据。
        """
        if not hasattr(self, 'json_dict') or not self.json_dict:
            raise ValueError("❌ self.json_dict 未加载或为空")

        # 遍历所有子配置（'big', 'small', 'default'...），找到包含该模块的配置
        target_config = None
        pixel_info_dict = {}

        for config_key, config in self.json_dict.items():
            pi = config.get("pixel_info", {})
            if isinstance(pi, dict) and module_name in pi:
                # 找到所属配置！
                target_config = config
                pixel_info_dict = pi
                break

        if target_config is None:
            available = []
            for config in self.json_dict.values():
                pi = config.get("pixel_info", {})
                if isinstance(pi, dict):
                    available.extend(pi.keys())
            raise KeyError(
                f"❌ 模块 {module_name} 不在任何配置的 pixel_info 中。\n"
                f"可用模块（前5个）: {list(set(available))[:5]}"
            )

        # 提取像素信息
        info = pixel_info_dict[module_name]
        required_keys = ['xpixels', 'ypixels', 'stepbyrow', 'start']
        for k in required_keys:
            if k not in info:
                raise ValueError(f"❌ 模块 {module_name} 的 pixel_info 缺少字段: {k}")

        # ✅ 从 target_config（即匹配的子配置）中提取全局元数据
        general_info = {
            'beamline': target_config.get('beamline', 'N/A'),
            'beamline_name': target_config.get('beamline_name', 'N/A'),
            'create_time': target_config.get('create_time', 'N/A')
        }

        return {
            'xpixels': info['xpixels'],
            'ypixels': info['ypixels'],
            'stepbyrow': info['stepbyrow'],
            'start': info['start'],
            **general_info
        }
    
    def reshape_pixel_id_to_2d(self, neutron_data, geometry):
        """
        将一维 pixel_id 数组重塑为 (ypixels, xpixels) 的二维布局。
        
        支持两种排布方式：
        - stepbyrow='x': 行优先（每行从左到右，行间从底到顶）
        - stepbyrow='y': 列优先（每列从底到顶，列间从左到右）
        
        原点始终在左下角（最小 pixel_id 在 [ypixels-1, 0]）。
        """
        xpixels = geometry['xpixels']
        ypixels = geometry['ypixels']
        stepbyrow = geometry['stepbyrow']
        start_id = geometry['start']

        expected_total = xpixels * ypixels
        pixel_ids = self.extract_neutron_data(neutron_data)['pixel_id']
        if len(pixel_ids) != expected_total:
            print(f"⚠️ 警告: 实际像素数 ({len(pixel_ids)}) ≠ 配置期望 ({expected_total})")

        # 创建 ID -> index 映射（虽然这里只用 ID，但保留结构一致性）
        pixel_set = set(pixel_ids)

        # 初始化二维数组
        pixel_id_2d = np.full((ypixels, xpixels), -1, dtype=pixel_ids.dtype)

        current_id = start_id

        if stepbyrow == 'x':
            # 行优先：先填一行（从左到右），再上移一行
            for row in range(ypixels - 1, -1, -1):      # 从底行到顶行
                for col in range(xpixels):               # 从左到右
                    if current_id in pixel_set:
                        pixel_id_2d[row, col] = current_id
                    else:
                        print(f"⚠️ pixel_id {current_id} 不存在于输入数据中")
                    current_id += 1

        elif stepbyrow == 'y':
            # 列优先：先填一列（从底到顶），再右移一列
            for col in range(xpixels):                   # 从左到右遍历列
                for row in range(ypixels - 1, -1, -1):   # 每列从底行到顶行
                    if current_id in pixel_set:
                        pixel_id_2d[row, col] = current_id
                    else:
                        print(f"⚠️ pixel_id {current_id} 不存在于输入数据中")
                    current_id += 1

        else:
            raise ValueError(f"❌ 不支持的 stepbyrow 值: '{stepbyrow}'，仅支持 'x' 或 'y'")

        return pixel_id_2d
    
    def get_pixel_total_counts(self, neutron_data):
        """
        基于 extract_neutron_data 的结果，返回 (N, 2) 数组：
            第0列：pixel_id
            第1列：total counts（histogram 沿 TOF 轴求和）
        
        Args:
            neutron_data: 由 _load_neutron_histogram 返回的数据对象
        
        Returns:
            np.ndarray: shape (N, 2), dtype float64（或混合）
        """
        # 1. 提取结构化数据
        data_dict = self.extract_neutron_data(neutron_data)
        
        # 2. 获取 pixel_id 和 histogram
        pixel_id = data_dict['pixel_id']      # (N,)
        histogram = data_dict['histogram']    # (N, T)
        
        # 3. 计算 total counts per pixel
        total_counts = histogram.sum(axis=1)  # (N,)
        
        # 4. 合并为 (N, 2) 数组
        pixel_counts = np.column_stack((pixel_id, total_counts))
        
        return pixel_counts
    
    def get_pixel_histogram_with_id(self, neutron_data):
        """
        基于 extract_neutron_data 的结果，返回 (N, T+1) 数组：
            第0列：pixel_id
            第1~T列：TOF histogram（每个时间道的计数）

        Args:
            neutron_data: 由 _load_neutron_histogram 返回的数据对象

        Returns:
            np.ndarray: shape (N, T+1), dtype float64（或根据输入自动推断）
        """
        # 1. 提取结构化数据
        data_dict = self.extract_neutron_data(neutron_data)
        
        # 2. 获取 pixel_id 和 histogram
        pixel_id = data_dict['pixel_id']      # (N,)
        histogram = data_dict['histogram']    # (N, T)
        tof_us = data_dict['tof_us']          # (T,)
        
        # 3. 将 pixel_id 扩展为列向量，并与 histogram 水平拼接
        pixel_id_col = pixel_id[:, np.newaxis]  # (N, 1)
        pixel_tof = np.hstack((pixel_id_col, histogram))  # (N, T+1)
        
        return pixel_tof, tof_us
    
    def map_counts_to_2d(self, pixel_id_2d, pixel_counts):
        """
        将一维的 (pixel_id, total_counts) 映射到二维几何布局中。
        
        Args:
            pixel_id_2d (np.ndarray): shape (ypixels, xpixels), 存储 pixel_id
            pixel_counts (np.ndarray): shape (N, 2), [:,0]=pixel_id, [:,1]=total_counts
        
        Returns:
            np.ndarray: shape (ypixels, xpixels), 对应位置的 total_counts
        """
        # 1. 构建映射字典: {pixel_id: total_counts}
        id_to_count = dict(zip(pixel_counts[:, 0], pixel_counts[:, 1]))
        
        # 2. 初始化 counts_2d，用 0 填充（无效像素视为 0 计数）
        counts_2d = np.zeros_like(pixel_id_2d, dtype=np.float32)
        
        # 3. 向量化映射（高效方式）
        # 创建一个向量化的查找函数
        vectorized_lookup = np.vectorize(lambda pid: id_to_count.get(pid, 0.0))
        counts_2d = vectorized_lookup(pixel_id_2d)
        
        return counts_2d
    
    def display_counts_heatmap(self, counts_2d):
        """
        将 counts_2d 以热图形式显示在 self.graphicsView_module 中。
        
        使用默认的热图色（如 viridis）
        """
        if counts_2d.size == 0:
            print("⚠️ counts_2d 为空，跳过绘图")
            return
        
        # 归一化前先记录原始范围
        vmin, vmax = np.nanmin(counts_2d), np.nanmax(counts_2d)
        if vmin == vmax:
            normalized = np.zeros_like(counts_2d)
        else:
            normalized = (counts_2d - vmin) / (vmax - vmin)

        # 归一化 counts_2d 到 [0, 1]
        vmin, vmax = np.nanmin(counts_2d), np.nanmax(counts_2d)
        normalized = (counts_2d - vmin) / (vmax - vmin)

        # 应用 matplotlib 的 viridis 色图，并转换为 uint8 类型的 RGB 图像
        cmap = cm.get_cmap('viridis_r')  # 可以选择其他内置色图，如 'plasma', 'inferno', 'magma', 'cividis' 等
        rgb_image = (cmap(normalized)[:, :, :3] * 255).astype(np.uint8)  # 忽略 alpha 通道

        # 计算目标尺寸并调整大小
        h, w = counts_2d.shape
        short_side = min(h, w)
        target_h = h * (10 if h < w else 1)
        target_w = w * (10 if w < h else 1)

        try:
            from scipy.ndimage import zoom
            zoom_h = target_h / h
            zoom_w = target_w / w
            resized = zoom(rgb_image, (zoom_h, zoom_w, 1), order=1)  # bilinear interpolation
        except ImportError:
            if h <= w:
                resized = np.repeat(rgb_image, 10, axis=0)  # 拉伸高度
            else:
                resized = np.repeat(rgb_image, 10, axis=1)  # 拉伸宽度
            resized = resized[:target_h, :target_w, :]  # 防止超限

        # 转换为 QImage (必须是 RGB888)
        height, width, _ = resized.shape
        qimage = QImage(
            resized.data,
            width,
            height,
            resized.strides[0],
            QImage.Format_RGB888
        ).copy()  # .copy() 防止内存释放

        # 切换 scene 前先清理 ROI 图元，避免持有已删除对象的引用。
        self._safe_remove_scene_item('roi_graphics_item')
        self._safe_remove_scene_item('roi_hint_item')

        # 显示到 graphicsView_module
        scene = QGraphicsScene()
        pixmap = QPixmap.fromImage(qimage)
        self.heatmap_pixmap_item = scene.addPixmap(pixmap)
        scene.setSceneRect(self.heatmap_pixmap_item.sceneBoundingRect())
        self.graphicsView_module.setScene(scene)
        self.graphicsView_module.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.graphicsView_module.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.graphicsView_module.resetTransform()
        self.graphicsView_module.fitInView(scene.sceneRect(), Qt.KeepAspectRatio)

        # 记录热图原始像素与显示区域，后续 ROI 必须以这个映射为准。
        self._heatmap_pixel_shape = counts_2d.shape
        self._heatmap_scene_rect = self.heatmap_pixmap_item.sceneBoundingRect()

        self.display_colorbar(vmin, vmax, cmap_name='viridis_r')

    def display_colorbar(self, vmin: float, vmax: float, cmap_name='viridis_r'):
        """
        在 self.graphicsView_colorbar 中显示带数值标签的垂直 colorbar，并确保标签完全可见。
        """
        if not hasattr(self, 'graphicsView_colorbar'):
            return
        
        bar_height = 280  # 稍微增加高度以适应标签
        bar_width = 50
        label_offset = 10
        font_size = 8
        padding_top_bottom = 10  # 增加上下填充

        gradient = np.linspace(0, 1, bar_height).reshape(-1, 1)
        cmap = cm.get_cmap(cmap_name)
        rgb_bar = (cmap(gradient)[:, :, :3] * 255).astype(np.uint8)
        colorbar_img = np.repeat(rgb_bar, bar_width, axis=1)

        total_width = bar_width + label_offset + 50
        canvas = np.ones((bar_height, total_width, 3), dtype=np.uint8) * 255
        canvas[padding_top_bottom:-padding_top_bottom, :bar_width, :] = colorbar_img[padding_top_bottom:-padding_top_bottom, :, :]
        
        h, w, _ = canvas.shape
        qimage = QImage(canvas.data, w, h, canvas.strides[0], QImage.Format_RGB888).copy()

        painter = QPainter(qimage)
        painter.setPen(QColor(0, 0, 0))
        font = QFont("Arial", font_size)
        painter.setFont(font)

        tick_positions = [0.0, 0.25, 0.5, 0.75, 1.0]
        for pos in tick_positions:
            y_pixel = int(padding_top_bottom + (1 - pos) * (bar_height - 2*padding_top_bottom - 1))
            real_value = vmin + pos * (vmax - vmin)
            
            if abs(real_value) >= 1e4 or (abs(real_value) < 1e-2 and real_value != 0):
                label = f"{real_value:.2e}"
            else:
                label = f"{real_value:.2f}".rstrip('0').rstrip('.')
            
            painter.drawText(bar_width + label_offset, y_pixel + 4, label)
        
        painter.end()

        scene = QGraphicsScene()
        pixmap = QPixmap.fromImage(qimage)
        scene.addPixmap(pixmap)
        scene.setSceneRect(QRectF(0, 0, w, h))

        self.graphicsView_colorbar.setScene(scene)
        self.graphicsView_colorbar.resetTransform()
        self.graphicsView_colorbar.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.graphicsView_colorbar.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

    def _safe_remove_scene_item(self, attr_name: str):
        """安全移除 scene item，兼容底层 C++ 对象已被删除的情况。"""
        item = getattr(self, attr_name, None)
        if item is None:
            return
        try:
            scene = item.scene()
            if scene is not None:
                scene.removeItem(item)
        except RuntimeError:
            # wrapped C/C++ object may already be deleted
            pass
        setattr(self, attr_name, None)

    def display_status_info(self, module_name: str):
        """
        从 JSON 配置中提取指定模块的详细信息，并显示在 self.listWidget_stats 中。
        
        显示内容包括：
        - 像素几何信息（xpixels, ypixels, stepbyrow, start）
        - 全局元数据（beamline, beamline_name, create_time）
        
        Args:
            module_name (str): 要显示信息的模块名称，如 'module10502'
        """
        try:
            # 1. 调用 extract_json_file 获取模块及全局配置信息
            info = self.extract_json_file(module_name)
            
            # 2. 清空状态信息列表，准备更新
            self.listWidget_stats.clear()
            
            # 3. 添加模块标识（作为标题）
            self.listWidget_stats.addItem(f"📊 模块: {module_name}")
            self.listWidget_stats.addItem("")  # 空行，提升可读性

             # 4. 显示实验/设备元数据
            self.listWidget_stats.addItem("🔹 实验信息:")
            self.listWidget_stats.addItem(f"   • beamline: {info.get('beamline', 'N/A')}")
            self.listWidget_stats.addItem(f"   • beamline name: {info.get('beamline_name', 'N/A')}")
            self.listWidget_stats.addItem(f"   • create time: {info.get('create_time', 'N/A')}")
            self.listWidget_stats.addItem("")  # 空行，提升可读性
            
            # 5. 显示像素布局参数
            self.listWidget_stats.addItem("🔹 像素布局:")
            self.listWidget_stats.addItem(f"   • X 像素数: {info['xpixels']}")
            self.listWidget_stats.addItem(f"   • Y 像素数: {info['ypixels']}")
            scan_dir = "按行" if info['stepbyrow'] == 'x' else "按列"
            self.listWidget_stats.addItem(f"   • 扫描方向: {scan_dir}")
            self.listWidget_stats.addItem(f"   • 起始位置: {info['start']}")
            self.listWidget_stats.addItem("")  # 空行分隔
            
        except (ValueError, KeyError) as e:
            # 6. 异常处理：显示错误提示
            self.listWidget_stats.clear()
            self.listWidget_stats.addItem("❌ 加载状态信息失败:")
            self.listWidget_stats.addItem(str(e))

    def append_statistics_to_list(self):
        """在 listWidget_stats 末尾追加热图统计信息"""
        if self.current_counts_2d is None:
            return
        
        vmin = np.nanmin(self.current_counts_2d)
        vmax = np.nanmax(self.current_counts_2d)
        
        self.listWidget_stats.addItem("🔹 热图统计:")
        self.listWidget_stats.addItem(f"   • 最小计数: {int(vmin)}")
        self.listWidget_stats.addItem(f"   • 最大计数: {int(vmax)}")

    def get_region_pixel_ids(self, roi_bounds=None):
        """
        获取指定区域内的像素ID
        roi_bounds: None 表示整个模块
                    或 (x_start, x_end, y_start, y_end) 表示ROI区域
        返回: 像素ID数组
        """
        if self.current_pixel_id_2d is None:
            return np.array([])
        
        if roi_bounds is None:
            # 整个模块的所有像素ID
            valid_ids = self.current_pixel_id_2d.flatten()
        else:
            # ROI区域
            x_start, x_end, y_start, y_end = roi_bounds
            # 确保边界在有效范围内
            h, w = self.current_pixel_id_2d.shape
            x_start = max(0, min(w-1, x_start))
            x_end = max(0, min(w-1, x_end))
            y_start = max(0, min(h-1, y_start))
            y_end = max(0, min(h-1, y_end))
            
            valid_ids = self.current_pixel_id_2d[y_start:y_end+1, x_start:x_end+1].flatten()
        
        # 过滤无效ID（值为-1或其他无效值）
        return valid_ids[valid_ids > 0]

    def append_pixel_id_range_to_list(self, roi_bounds=None):
        """显示指定区域内的像素ID，连续ID用'-'压缩显示
        roi_bounds: None表示整个模块，否则为(x_start, x_end, y_start, y_end)"""
        
        # 使用通用函数获取像素ID
        valid_ids = self.get_region_pixel_ids(roi_bounds)
        
        if valid_ids.size == 0:
            self.listWidget_stats.addItem(" • 像素ID: N/A")
            return
        
        # 判断是显示整个模块还是ROI
        prefix = "模块" if roi_bounds is None else "ROI"
        
        # ✅ 添加调试信息
        print(f"🔍 调试信息 - 当前仪器: {self.current_instrument}")
        print(f"🔍 原始像素ID (前10个): {valid_ids[:10] if len(valid_ids) > 10 else valid_ids}")
        print(f"🔍 像素ID类型: {valid_ids.dtype}")
        print(f"🔍 像素ID数量: {len(valid_ids)}")
        
        # 确保ID是整数并排序
        try:
            valid_ids = np.sort(valid_ids.astype(int))
        except Exception as e:
            print(f"⚠️ 转换像素ID为整数时出错: {e}")
            print(f"⚠️ 原始ID示例: {valid_ids[:5]}")
            # 尝试直接排序
            valid_ids = np.sort(valid_ids)
        
        print(f"🔍 排序后像素ID (前10个): {valid_ids[:10] if len(valid_ids) > 10 else valid_ids}")
        
        # 1. 先显示统计信息
        self.listWidget_stats.addItem(f" • 像素总数: {len(valid_ids)} 个")
        self.listWidget_stats.addItem(f" • ID最小值: {valid_ids[0]}")
        self.listWidget_stats.addItem(f" • ID最大值: {valid_ids[-1]}")
        
        # 2. 添加空行分隔
        self.listWidget_stats.addItem("")
        
        # 3. 显示未压缩的原始ID（调试用）
        if len(valid_ids) <= 20:  # 如果ID数量不多，显示原始ID
            self.listWidget_stats.addItem(f" • 原始像素ID列表:")
            for i in range(0, len(valid_ids), 5):  # 每行显示5个
                id_chunk = valid_ids[i:i+5]
                id_str = "  ".join(str(id) for id in id_chunk)
                self.listWidget_stats.addItem(f"   {id_str}")
            self.listWidget_stats.addItem("")
        
        # 4. 压缩连续ID
        compressed_ranges = []
        start = valid_ids[0]
        end = valid_ids[0]
        
        # ✅ 添加压缩算法的调试信息
        print(f"🔍 开始压缩ID，第一个ID: {start}")
        
        for i in range(1, len(valid_ids)):
            current_id = valid_ids[i]
            is_consecutive = (current_id == end + 1)
            
            if i < 5:  # 打印前几个ID的压缩判断
                print(f"  ID[{i}]: {current_id}, 是否连续: {is_consecutive} (上一个: {end})")
            
            if is_consecutive:
                # 连续ID，更新结束位置
                end = current_id
            else:
                # 不连续ID，保存当前范围
                if start == end:
                    compressed_ranges.append(f"{start}")
                else:
                    compressed_ranges.append(f"{start}-{end}")
                start = current_id
                end = current_id
        
        # 处理最后一个范围
        if start == end:
            compressed_ranges.append(f"{start}")
        else:
            compressed_ranges.append(f"{start}-{end}")
        
        print(f"🔍 压缩后范围数量: {len(compressed_ranges)}")
        print(f"🔍 压缩范围: {compressed_ranges}")
        
        # 5. 显示标题
        self.listWidget_stats.addItem(f" • 像素ID列表:")
        
        # 6. 显示压缩后的ID（每个范围一行）
        if len(compressed_ranges) == 1:
            # 如果只有一个范围，可能所有ID都是连续的
            self.listWidget_stats.addItem(f"   {compressed_ranges[0]}")
            print(f"⚠️ 注意：所有{len(valid_ids)}个ID被压缩为1个范围")
            print(f"⚠️ 这可能意味着：")
            print(f"   1. 所有ID确实是连续的")
            print(f"   2. ID格式有问题，导致压缩算法误判")
            print(f"   3. BL16的ID编号方式特殊")
        else:
            # 多个范围，每行显示一个
            for i, segment in enumerate(compressed_ranges):
                if i == len(compressed_ranges) - 1:
                    # 最后一段不带逗号
                    self.listWidget_stats.addItem(f"   {segment}")
                else:
                    # 其他段带逗号
                    self.listWidget_stats.addItem(f"   {segment},")
        
        # # 7. 添加ID间隔信息
        # if len(valid_ids) > 1:
        #     self.listWidget_stats.addItem("")
        #     self.listWidget_stats.addItem(f" • ID间隔统计:")
            
        #     # 计算ID之间的间隔
        #     intervals = np.diff(valid_ids)
        #     unique_intervals = np.unique(intervals)
            
        #     for interval in unique_intervals:
        #         count = np.sum(intervals == interval)
        #         if interval == 1:
        #             self.listWidget_stats.addItem(f"   - 连续间隔(+1): {count} 处")
        #         else:
        #             self.listWidget_stats.addItem(f"   - 间隔(+{interval}): {count} 处")

    def toggle_roi_selection_mode(self):
        """切换 ROI 选择模式"""
        self.roi_selection_mode = not self.roi_selection_mode
        if self.roi_selection_mode:
            self.pushButton_Select.setText("取消选择")
            self.graphicsView_module.viewport().setCursor(Qt.CrossCursor)
            self._safe_remove_scene_item('roi_hint_item')
            
        else:
            self.pushButton_Select.setText("Select Region")
            self.graphicsView_module.viewport().setCursor(Qt.ArrowCursor)

            # 清除图形项
            self._safe_remove_scene_item('roi_graphics_item')
            self._safe_remove_scene_item('roi_hint_item')
            
            self.roi_start = None
            # 重置 ROI TOF 数据
            self.roi_tof_us = None
            self.roi_tof_counts = None
            self.original_roi_tof_us = None
            self.original_roi_tof_counts = None
            self.current_display_tof_us = None
            self.current_display_tof_counts = None
            self.current_plot_pixel_id = None
            # 恢复原始模块统计信息
            if hasattr(self, 'current_module_data') and self.current_module_data is not None:
                full_module_name = f"module{self.moduleComboBox.currentText()}"
                self.display_status_info(full_module_name)
                self.append_statistics_to_list()
                self.append_pixel_id_range_to_list()

    def roi_mouse_press_event(self, event):
        if event.button() == Qt.LeftButton and self.roi_selection_mode:
            scene_pos = self.graphicsView_module.mapToScene(event.pos())
            self.roi_start = scene_pos
            
            scene = self.graphicsView_module.scene()
            if scene is None:
                return True

            self._safe_remove_scene_item('roi_graphics_item')
            
            self.roi_graphics_item = QGraphicsRectItem()
            pen = QPen(QColor(0, 0, 0))
            pen.setWidth(1)
            pen.setStyle(Qt.DashLine)
            pen.setDashPattern([3, 3])
            pen.setCosmetic(True)
            self.roi_graphics_item.setPen(pen)
            self.roi_graphics_item.setBrush(QBrush(QColor(255, 255, 0, 30)))
            self.roi_graphics_item.setZValue(1)
            self.roi_graphics_item.setAcceptedMouseButtons(Qt.NoButton)
            scene.addItem(self.roi_graphics_item)
            return True
        return False

    def roi_mouse_move_event(self, event):
        if self.roi_selection_mode and self.roi_start and event.buttons() & Qt.LeftButton:
            current_pos = self.graphicsView_module.mapToScene(event.pos())
            rect = QRectF(self.roi_start, current_pos).normalized()
            if self.roi_graphics_item:
                try:
                    self.roi_graphics_item.setRect(rect)
                except RuntimeError:
                    # 场景切换后旧图元引用可能失效
                    self.roi_graphics_item = None
            return True
        return False

    def roi_mouse_release_event(self, event):
        if event.button() == Qt.LeftButton and self.roi_selection_mode and self.roi_start:
            end_pos = self.graphicsView_module.mapToScene(event.pos())
            self.process_selected_roi(self.roi_start, end_pos)
            self.roi_start = None
            return True
        return False
    
    def eventFilter(self, source, event):
        """处理 graphicsView_module 的鼠标事件"""
        if source is self.graphicsView_module.viewport() and self.roi_selection_mode:
            if event.type() == QtCore.QEvent.MouseButtonPress:
                return self.roi_mouse_press_event(event)
            elif event.type() == QtCore.QEvent.MouseMove:
                return self.roi_mouse_move_event(event)
            elif event.type() == QtCore.QEvent.MouseButtonRelease:
                return self.roi_mouse_release_event(event)
        return super().eventFilter(source, event)
    
    def process_selected_roi(self, start: QPointF, end: QPointF):
        """处理选中的 ROI 区域，更新统计信息，并绘制 TOF 谱"""
        if self.current_counts_2d is None or not hasattr(self, 'pixel_tof') or self.pixel_tof is None:
            return

        bounds = self._scene_points_to_pixel_bounds(start, end)
        if bounds is None:
            self._clear_roi_selection_result("选区未覆盖热图有效区域")
            return

        x_start, x_end, y_start, y_end = bounds
        self.process_roi_bounds(x_start, x_end, y_start, y_end)

    def _scene_points_to_pixel_bounds(self, start: QPointF, end: QPointF):
        """把 scene 坐标稳定映射到原始像素索引边界。"""
        if self.current_counts_2d is None:
            return None

        h, w = self.current_counts_2d.shape
        scene = self.graphicsView_module.scene()
        if scene is None or h <= 0 or w <= 0:
            return None

        if self.heatmap_pixmap_item is not None:
            scene_rect = self.heatmap_pixmap_item.sceneBoundingRect()
        else:
            scene_rect = scene.sceneRect()

        displayed_w = scene_rect.width()
        displayed_h = scene_rect.height()
        if displayed_w <= 0 or displayed_h <= 0:
            return None

        # 先与热图矩形求交集，热图外选区不应映射到边缘像素。
        selection_rect = QRectF(start, end).normalized()
        overlap_rect = selection_rect.intersected(scene_rect)
        if overlap_rect.isNull() or overlap_rect.width() <= 0 or overlap_rect.height() <= 0:
            return None

        scale_x = w / displayed_w
        scale_y = h / displayed_h

        x1 = int(np.floor((overlap_rect.left() - scene_rect.left()) * scale_x))
        x2 = int(np.floor((overlap_rect.right() - scene_rect.left()) * scale_x))
        y1 = int(np.floor((overlap_rect.top() - scene_rect.top()) * scale_y))
        y2 = int(np.floor((overlap_rect.bottom() - scene_rect.top()) * scale_y))

        x_start = max(0, min(w - 1, min(x1, x2)))
        x_end = max(0, min(w - 1, max(x1, x2)))
        y_start = max(0, min(h - 1, min(y1, y2)))
        y_end = max(0, min(h - 1, max(y1, y2)))

        if x_start > x_end or y_start > y_end:
            return None

        return x_start, x_end, y_start, y_end

    def _clear_roi_selection_result(self, reason_text="未选中有效像素"):
        """清空 ROI 结果，避免热图外选择误导统计。"""
        self.current_roi_pixel_ids = np.array([], dtype=int)
        self.current_plot_pixel_id = None
        self.roi_tof_us = None
        self.roi_tof_counts = None
        self.original_roi_tof_us = None
        self.original_roi_tof_counts = None
        self.current_display_tof_us = None
        self.current_display_tof_counts = None
        self.plot_summed_tof_in_region(np.array([]), np.array([]))

        self.listWidget_stats.clear()
        self.listWidget_stats.addItem("🔹 选中区域统计:")
        self.listWidget_stats.addItem(" • 像素数量: 0")
        self.listWidget_stats.addItem(f" • 说明: {reason_text}")

    def process_roi_bounds(self, x_start: int, x_end: int, y_start: int, y_end: int):
        """按明确的像素边界处理 ROI，适合精确行/列/范围选择。"""
        if self.current_counts_2d is None or not hasattr(self, 'pixel_tof') or self.pixel_tof is None:
            return

        h, w = self.current_counts_2d.shape
        x_start = max(0, min(w - 1, int(x_start)))
        x_end = max(0, min(w - 1, int(x_end)))
        y_start = max(0, min(h - 1, int(y_start)))
        y_end = max(0, min(h - 1, int(y_end)))

        if x_start > x_end:
            x_start, x_end = x_end, x_start
        if y_start > y_end:
            y_start, y_end = y_end, y_start

        self.current_plot_pixel_id = None

        selected_ids_flat = self.current_pixel_id_2d[y_start:y_end + 1, x_start:x_end + 1].flatten()
        valid_ids = selected_ids_flat[selected_ids_flat > 0]
        self.current_roi_pixel_ids = valid_ids.copy()

        if valid_ids.size > 0:
            summed_tof = self.get_summed_tof_spectrum(self.pixel_tof, valid_ids)
            self.original_roi_tof_us = self.tof_us.copy()
            self.original_roi_tof_counts = summed_tof.copy()
            self.current_display_tof_us = self.tof_us.copy()
            self.current_display_tof_counts = summed_tof.copy()
            self.roi_tof_us = self.tof_us.copy()
            self.roi_tof_counts = summed_tof.copy()
            self.plot_tof_spectrum_with_pyplot(summed_tof, self.tof_us)
        else:
            self.original_roi_tof_us = None
            self.original_roi_tof_counts = None
            self.current_display_tof_us = None
            self.current_display_tof_counts = None
            self.plot_summed_tof_in_region(np.array([]), np.array([]))

        selected_counts = self.current_counts_2d[y_start:y_end + 1, x_start:x_end + 1]
        stats_lines = []
        stats_lines.append("🔹 选中区域统计:")
        stats_lines.append(f" • 像素数量: {valid_ids.size}")
        stats_lines.append(f" • X 范围: {x_start} – {x_end}")
        stats_lines.append(f" • Y 范围: {y_start} – {y_end}")
        stats_lines.append(f" • 计数总和: {selected_counts.sum():.0f}")
        stats_lines.append(f" • 计数最小值: {selected_counts.min():.2f}")
        stats_lines.append(f" • 计数最大值: {selected_counts.max():.2f}")

        self.listWidget_stats.clear()
        for line in stats_lines:
            self.listWidget_stats.addItem(line)

        self.listWidget_stats.addItem("")
        roi_bounds = (x_start, x_end, y_start, y_end)
        self.append_pixel_id_range_to_list(roi_bounds)

    def show_manual_roi_dialog(self):
        """通过输入精确像素范围选择 ROI。"""
        if self.current_counts_2d is None:
            QMessageBox.warning(self, "警告", "请先加载模块数据，再设置精确范围。")
            return

        h, w = self.current_counts_2d.shape
        dialog = QDialog(self)
        dialog.setWindowTitle("精确选择 ROI")
        layout = QVBoxLayout(dialog)

        info_label = QLabel(f"当前像素范围: X 0 - {w - 1}, Y 0 - {h - 1}")
        layout.addWidget(info_label)

        form_layout = QtWidgets.QFormLayout()
        x_start_spin = QSpinBox()
        x_start_spin.setRange(0, max(0, w - 1))
        x_start_spin.setValue(0)
        x_end_spin = QSpinBox()
        x_end_spin.setRange(0, max(0, w - 1))
        x_end_spin.setValue(max(0, w - 1))
        y_start_spin = QSpinBox()
        y_start_spin.setRange(0, max(0, h - 1))
        y_start_spin.setValue(0)
        y_end_spin = QSpinBox()
        y_end_spin.setRange(0, max(0, h - 1))
        y_end_spin.setValue(max(0, h - 1))

        form_layout.addRow("X 起始列:", x_start_spin)
        form_layout.addRow("X 结束列:", x_end_spin)
        form_layout.addRow("Y 起始行:", y_start_spin)
        form_layout.addRow("Y 结束行:", y_end_spin)
        layout.addLayout(form_layout)

        button_layout = QHBoxLayout()
        ok_btn = QPushButton("应用")
        cancel_btn = QPushButton("取消")
        button_layout.addWidget(ok_btn)
        button_layout.addWidget(cancel_btn)
        layout.addLayout(button_layout)

        def apply_roi():
            self.process_roi_bounds(
                x_start_spin.value(),
                x_end_spin.value(),
                y_start_spin.value(),
                y_end_spin.value(),
            )
            dialog.accept()

        ok_btn.clicked.connect(apply_roi)
        cancel_btn.clicked.connect(dialog.reject)
        dialog.exec_()

    def get_summed_tof_spectrum(self, pixel_tof, selected_pixel_ids):
        """
        根据选中的 pixel_id，从 pixel_tof 中提取对应 TOF 谱并求和。

        Args:
            pixel_tof (np.ndarray): shape (N, T+1), 第0列为pixel_id
            selected_pixel_ids (array-like): 选中的 pixel_id 列表

        Returns:
            np.ndarray: shape (T,), 所有选中像素的 TOF 谱之和
        """
        if len(selected_pixel_ids) == 0 or pixel_tof.size == 0:
            T = pixel_tof.shape[1] - 1 if pixel_tof.size > 0 else 0
            return np.zeros(T)

        selected_ids = np.asarray(selected_pixel_ids)
        all_ids = pixel_tof[:, 0]
        mask = np.isin(all_ids, selected_ids)
        matched_tof = pixel_tof[mask, 1:]  # (m, T)
        return matched_tof.sum(axis=0)     # (T,)

    def _get_single_pixel_tof_spectrum(self, pixel_id):
        """根据 pixel_id 返回该像素的 TOF 谱。"""
        if self.pixel_tof is None or self.tof_us is None:
            return None, None

        all_ids = self.pixel_tof[:, 0].astype(int)
        target_id = int(pixel_id)
        idx = np.where(all_ids == target_id)[0]
        if idx.size == 0:
            return None, None

        tof_counts = self.pixel_tof[idx[0], 1:].astype(float)
        return self.tof_us.copy(), tof_counts

    def _get_pixel_position_by_id(self, pixel_id):
        """从 current_neutron_data 中按 pixel_id 获取像素位置。"""
        if self.current_neutron_data is None:
            return None
        try:
            pos_da = self.current_neutron_data["positions"]
            pos_pixel_ids = pos_da.coords["pixel"].values.astype(int)
            target_id = int(pixel_id)
            idx = np.where(pos_pixel_ids == target_id)[0]
            if idx.size == 0:
                return None
            return np.asarray(pos_da.values[idx[0]], dtype=float)
        except Exception:
            return None

    def _tof_us_to_wavelength_for_pixel(self, tof_us, pixel_id):
        """按指定像素进行 TOF->波长换算。"""
        pos = self._get_pixel_position_by_id(pixel_id)
        if pos is None:
            pos = np.array([0.0, 0.0, 0.0])
        return self._convert_tof_to_wavelength_by_position(tof_us, pos)

    def select_single_pixel_and_plot(self):
        """弹窗输入 pixel_id，绘制该像素的 TOF 谱。"""
        if self.pixel_tof is None or self.tof_us is None:
            QMessageBox.warning(self, "错误", "请先选择并加载 module 数据！")
            return

        available_ids = np.sort(self.pixel_tof[:, 0].astype(int))
        if available_ids.size == 0:
            QMessageBox.warning(self, "错误", "当前 module 无可用像素ID。")
            return

        default_id = int(available_ids[0])
        min_id = int(available_ids[0])
        max_id = int(available_ids[-1])

        pixel_id, ok = QtWidgets.QInputDialog.getInt(
            self,
            "选择像素",
            f"请输入像素ID（范围 {min_id} - {max_id}）:",
            value=default_id,
            min=min_id,
            max=max_id,
            step=1
        )
        if not ok:
            return

        if pixel_id not in set(available_ids.tolist()):
            QMessageBox.warning(self, "无效像素ID", f"像素ID {pixel_id} 不在当前 module 的有效像素列表中。")
            return

        tof_us, tof_counts = self._get_single_pixel_tof_spectrum(pixel_id)
        if tof_us is None or tof_counts is None:
            QMessageBox.warning(self, "错误", f"未找到像素ID {pixel_id} 的 TOF 谱数据。")
            return

        self.current_plot_pixel_id = int(pixel_id)
        self.current_roi_pixel_ids = np.array([int(pixel_id)], dtype=int)
        self.roi_tof_us = tof_us.copy()
        self.roi_tof_counts = tof_counts.copy()
        self.original_roi_tof_us = tof_us.copy()
        self.original_roi_tof_counts = tof_counts.copy()
        self.current_display_tof_us = tof_us.copy()
        self.current_display_tof_counts = tof_counts.copy()

        self.plot_tof_spectrum_with_pyplot(self.current_display_tof_counts, self.current_display_tof_us)

        self.listWidget_stats.clear()
        self.listWidget_stats.addItem("🔹 单像素谱统计:")
        self.listWidget_stats.addItem(f" • 模块: module{self.moduleComboBox.currentText()}")
        self.listWidget_stats.addItem(f" • 像素ID: {pixel_id}")
        self.listWidget_stats.addItem(f" • 谱点数: {len(tof_us)}")
        self.listWidget_stats.addItem(f" • 计数最小值: {float(np.min(tof_counts)):.2f}")
        self.listWidget_stats.addItem(f" • 计数最大值: {float(np.max(tof_counts)):.2f}")
    
    def plot_summed_tof_in_region(self, tof_counts, tof_us):
        """
        使用 matplotlib 绘制 TOF 谱，显示在嵌入的 FigureCanvas 中。
        """
        self.plot_tof_spectrum_with_pyplot(tof_counts, tof_us)

    def _get_tof_bin_width(self, tof_centers):
        """估算 TOF bin 宽度（假设等间距）"""
        if tof_centers.size <= 1:
            return 16.0  # 默认值或从元数据读取
        return float(tof_centers[1] - tof_centers[0])

    def _convert_tof_to_wavelength_by_position(self, tof_us, position):
        """
        按单个像素位置进行 TOF->波长换算（直接调用 rongzai.core_unitconvert）。
        """
        l1 = self.current_l1 if self.current_l1 > 0 else 10.0
        pos = np.asarray(position, dtype=float).reshape(-1)

        if pos.size >= 4:
            l2 = float(pos[3])
        elif pos.size >= 3:
            l2 = float(np.sqrt(pos[0] ** 2 + pos[1] ** 2 + pos[2] ** 2))
        else:
            l2 = 0.0

        return RZ_TOF_TO_WAVELENGTH(tof_us, l1, l2, "elastic", 0.0, False)

    def _tof_us_to_wavelength(self, tof_us):
        """
        将 TOF（μs）转换为中子波长（Å）。
        优先使用 ROI 选中像素平均位置；若不可用，按 l2=0 退化。
        """
        try:
            if (self.current_neutron_data is not None and
                    self.current_roi_pixel_ids is not None and
                    len(self.current_roi_pixel_ids) > 0):
                # positions: DataArray, shape (N_pixels, 3), coords: pixel, coordinate
                pos_da = self.current_neutron_data["positions"]
                all_pixel_ids = pos_da.coords["pixel"].values
                mask = np.isin(all_pixel_ids, self.current_roi_pixel_ids)
                roi_positions = pos_da.values[mask]  # (M, 3)
                if roi_positions.shape[0] > 0:
                    mean_pos = roi_positions.mean(axis=0)  # [x, y, z]
                    return self._convert_tof_to_wavelength_by_position(tof_us, mean_pos)
        except Exception as e:
            print(f"⚠️ core_unitconvert 换算失败，按 l2=0 退化: {e}")

        # 退化方案：按 l2 = 0 处理
        return self._convert_tof_to_wavelength_by_position(tof_us, np.array([0.0, 0.0, 0.0]))

    def get_summed_wavelength_spectrum(self, selected_pixel_ids, tof_us_window):
        """
        将 ROI 内每个像素先做 TOF->波长换算，再插值到公共波长轴并求和。

        Args:
            selected_pixel_ids (array-like): ROI 内 pixel_id 列表
            tof_us_window (np.ndarray): 当前显示 TOF 轴（可为裁剪后的子区间）

        Returns:
            tuple[np.ndarray, np.ndarray]: (wavelength_axis, summed_counts)
        """
        if (self.pixel_tof is None or self.tof_us is None or
                self.current_neutron_data is None or
                selected_pixel_ids is None or len(selected_pixel_ids) == 0 or
                tof_us_window is None or tof_us_window.size == 0):
            return np.array([]), np.array([])

        selected_ids = np.asarray(selected_pixel_ids).astype(int)
        all_ids = self.pixel_tof[:, 0].astype(int)
        pix_mask = np.isin(all_ids, selected_ids)
        if not np.any(pix_mask):
            return np.array([]), np.array([])

        # 在完整 TOF 轴上根据当前窗口做裁剪（窗口通常为连续子区间）
        tof_min = float(np.min(tof_us_window))
        tof_max = float(np.max(tof_us_window))
        tof_mask = (self.tof_us >= tof_min) & (self.tof_us <= tof_max)
        tof_axis = self.tof_us[tof_mask]
        if tof_axis.size == 0:
            return np.array([]), np.array([])

        counts_by_pixel = self.pixel_tof[pix_mask, 1:][:, tof_mask]
        pixel_ids_used = all_ids[pix_mask]

        # 构建 pixel_id -> position 映射
        pos_da = self.current_neutron_data["positions"]
        pos_pixel_ids = pos_da.coords["pixel"].values.astype(int)
        pos_values = pos_da.values
        pid_to_pos = {pid: pos for pid, pos in zip(pos_pixel_ids, pos_values)}

        l1 = self.current_l1 if self.current_l1 > 0 else 10.0
        wavelength_axes = []
        valid_counts_rows = []

        for pid, counts_row in zip(pixel_ids_used, counts_by_pixel):
            pos = pid_to_pos.get(int(pid))
            if pos is None:
                continue
            try:
                lam_axis = self._convert_tof_to_wavelength_by_position(tof_axis, pos)
                wavelength_axes.append(lam_axis)
                valid_counts_rows.append(counts_row)
            except Exception:
                continue

        if len(wavelength_axes) == 0:
            return np.array([]), np.array([])

        # 统一到公共波长网格：使用全体像素覆盖范围，点数与当前 TOF 窗口一致
        lam_min = min(float(np.min(x)) for x in wavelength_axes)
        lam_max = max(float(np.max(x)) for x in wavelength_axes)
        n_points = int(tof_axis.size)
        if n_points <= 1 or lam_max <= lam_min:
            return np.array([]), np.array([])

        lam_common = np.linspace(lam_min, lam_max, n_points)
        summed_counts = np.zeros_like(lam_common, dtype=float)

        for lam_axis, counts_row in zip(wavelength_axes, valid_counts_rows):
            # 出界补零，避免不同像素覆盖范围不一致带来的伪信号
            y_interp = np.interp(lam_common, lam_axis, counts_row, left=0.0, right=0.0)
            summed_counts += y_interp

        return lam_common, summed_counts

    def on_xunit_changed(self, _):
        """横轴单位切换时，用当前显示数据重绘谱图"""
        if (self.current_display_tof_us is not None and
                self.current_display_tof_counts is not None and
                self.current_display_tof_us.size > 0):
            self.plot_tof_spectrum_with_pyplot(
                self.current_display_tof_counts,
                self.current_display_tof_us
            )

    def plot_tof_spectrum_with_pyplot(self, tof_counts, tof_us):
        self.tof_figure.clear()
        ax = self.tof_figure.add_subplot(111)

        if tof_counts.size > 0 and tof_us.size > 0:
            use_wavelength = (self.comboBox_xunit.currentText() == "Wavelength (Å)")
            is_single_pixel = (
                self.current_roi_pixel_ids is not None and
                len(self.current_roi_pixel_ids) == 1 and
                self.current_plot_pixel_id is not None
            )

            if use_wavelength:
                if is_single_pixel:
                    x_data = self._tof_us_to_wavelength_for_pixel(tof_us, self.current_plot_pixel_id)
                    y_data = tof_counts
                else:
                    x_data, y_data = self.get_summed_wavelength_spectrum(self.current_roi_pixel_ids, tof_us)
                    if x_data.size == 0 or y_data.size == 0:
                        # 兜底：若逐像素换算不可用，退化为旧逻辑
                        x_data = self._tof_us_to_wavelength(tof_us)
                        y_data = tof_counts
                xlabel = "Wavelength (Å)"
                title = "Wavelength Spectrum from Selected Pixel" if is_single_pixel else "Wavelength Spectrum from Selected Region"
            else:
                x_data = tof_us
                y_data = tof_counts
                xlabel = "Time of Flight (μs)"
                title = "TOF Spectrum from Selected Pixel" if is_single_pixel else "TOF Spectrum from Selected Region"

            # 明确绘制“点线图”：底层线 + 上层实心散点
            ax.plot(x_data, y_data, color='#808080', linewidth=1.0, linestyle='-', zorder=1)

            # 每个数据点都绘制一个散点
            ax.scatter(x_data, y_data, s=9, c='#1f77b4', edgecolors='none', alpha=0.95, zorder=2)

            ax.set_xlabel(xlabel)
            ax.set_ylabel("Counts")
            ax.set_title(title)
            ax.grid(True, linestyle='--', alpha=0.5)

        self.tof_figure.tight_layout()
        self.tof_canvas.draw()

    def show_roi_tof_range_dialog(self):
        if (self.roi_tof_us is None or self.roi_tof_counts is None or
            self.roi_tof_us.size == 0):
            QMessageBox.warning(self, "警告", "没有选中的区域或 TOF 谱数据")
            return

        tof = self.current_display_tof_us
        dt = self._get_tof_bin_width(tof)

        # ✅ 显示范围：左右各扩展 dt/2
        display_min = tof[0] - dt / 2
        display_max = tof[-1] + dt / 2

        dialog = QDialog(self)
        dialog.setWindowTitle("设置 ROI TOF 显示范围")
        dialog.setFixedSize(350, 150)

        layout = QVBoxLayout(dialog)

        # 显示扩展后的范围（如 0 - 40000）
        range_label = QLabel(f"当前 TOF 范围: {int(display_min)} – {int(display_max)} μs")
        range_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(range_label)

        input_layout = QHBoxLayout()
        input_layout.addWidget(QLabel("Start (μs):"))
        start_edit = QLineEdit(f"{int(display_min)}")
        input_layout.addWidget(start_edit)

        input_layout.addWidget(QLabel("End (μs):"))
        end_edit = QLineEdit(f"{int(display_max)}")
        input_layout.addWidget(end_edit)

        layout.addLayout(input_layout)

        btn_layout = QHBoxLayout()
        ok_btn = QPushButton("确定")
        cancel_btn = QPushButton("取消")
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

        def on_ok():
            try:
                start_val = float(start_edit.text())
                end_val = float(end_edit.text())
            except ValueError:
                QMessageBox.warning(self, "错误", "请输入有效的数字")
                return

            if start_val > end_val:
                start_val, end_val = end_val, start_val

            # 在当前显示的 tof 上找索引
            start_idx = np.searchsorted(tof, start_val, side='left')
            end_idx = np.searchsorted(tof, end_val, side='right') - 1

            start_idx = np.clip(start_idx, 0, len(tof) - 1)
            end_idx = np.clip(end_idx, 0, len(tof) - 1)
            if start_idx > end_idx:
                end_idx = start_idx

            # 更新当前显示数据
            self.current_display_tof_us = tof[start_idx:end_idx + 1]
            self.current_display_tof_counts = self.current_display_tof_counts[start_idx:end_idx + 1]

            # 绘图
            self.plot_tof_spectrum_with_pyplot(
                self.current_display_tof_counts,
                self.current_display_tof_us
            )

            # 提示
            actual_start = self.current_display_tof_us[0]
            actual_end = self.current_display_tof_us[-1]
            QMessageBox.information(
                self,
                "范围已应用",
                f"实际显示 TOF 范围: {actual_start:.1f} – {actual_end:.1f} μs\n"
                f"数据点数: {len(self.current_display_tof_us)}"
            )
            dialog.accept()

        ok_btn.clicked.connect(on_ok)
        cancel_btn.clicked.connect(dialog.reject)

        dialog.exec_()

    def save_roi_data(self):
        """
        保存ROI区域的图片、当前显示谱数据和像素ID信息
        """
        # 检查是否有可保存的数据
        if (self.current_display_tof_us is None or 
            self.current_display_tof_counts is None or
            self.current_roi_pixel_ids is None):
            QMessageBox.warning(self, "警告", "没有可保存的ROI数据，请先选择区域！")
            return
        
        # 1. 弹出文件保存对话框
        default_name = f"ROI_data_{self.moduleComboBox.currentText()}"
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "保存ROI数据",
            default_name,  # 默认文件名
            "文本文件 (*.txt);;所有文件 (*)"
        )
        
        if not file_path:
            return  # 用户取消了保存
        
        # 确保文件有.txt扩展名
        if not file_path.lower().endswith('.txt'):
            file_path += '.txt'
        
        try:
            # 2. 保存TOF谱数据到txt文件
            self._save_tof_data_to_txt(file_path)
            
            # 3. 保存图片
            img_path = file_path.replace('.txt', '.png')
            self._save_region_image(img_path)
            
            # 4. 显示成功消息
            QMessageBox.information(
                self,
                "保存成功",
                f"数据已保存：\n"
                f"谱数据: {file_path}\n"
                f"图片: {img_path}"
            )
            
        except Exception as e:
            QMessageBox.critical(self, "保存失败", f"保存过程中发生错误：\n{str(e)}")

    def _save_tof_data_to_txt(self, file_path):
        """保存当前显示谱数据和像素ID信息到txt文件"""
        use_wavelength = (self.comboBox_xunit.currentText() == "Wavelength (Å)")

        if use_wavelength:
            x_data, counts_data = self.get_summed_wavelength_spectrum(
                self.current_roi_pixel_ids,
                self.current_display_tof_us
            )
            if x_data.size == 0 or counts_data.size == 0:
                x_data = self._tof_us_to_wavelength(self.current_display_tof_us)
                counts_data = self.current_display_tof_counts
            section_title = "[Wavelength谱数据]"
            x_label = "Wavelength(Å)"
            x_unit_text = "Wavelength (Å)"
        else:
            x_data = self.current_display_tof_us
            counts_data = self.current_display_tof_counts
            section_title = "[TOF谱数据]"
            x_label = "TOF(μs)"
            x_unit_text = "TOF (μs)"

        with open(file_path, 'w', encoding='utf-8') as f:
            # 写入头部信息
            f.write("=" * 60 + "\n")
            f.write("ROI数据保存\n")
            f.write("=" * 60 + "\n\n")
            
            # 写入基本信息
            f.write("[基本信息]\n")
            f.write(f"仪器: {self.current_instrument}\n")
            f.write(f"模块: {self.moduleComboBox.currentText()}\n")
            f.write(f"横轴单位: {x_unit_text}\n")
            f.write(f"保存时间: {QtCore.QDateTime.currentDateTime().toString('yyyy-MM-dd hh:mm:ss')}\n\n")
            
            # 写入像素ID信息
            f.write("[像素ID信息]\n")
            valid_ids = np.sort(self.current_roi_pixel_ids.astype(int))
            f.write(f"像素总数: {len(valid_ids)} 个\n")
            f.write(f"ID最小值: {valid_ids[0]}\n")
            f.write(f"ID最大值: {valid_ids[-1]}\n\n")
            
            # 写入详细的像素ID列表（压缩格式）
            f.write("像素ID列表（连续ID已压缩）:\n")
            compressed_ranges = []
            start = valid_ids[0]
            end = valid_ids[0]
            
            for i in range(1, len(valid_ids)):
                if valid_ids[i] == end + 1:
                    end = valid_ids[i]
                else:
                    if start == end:
                        compressed_ranges.append(f"{start}")
                    else:
                        compressed_ranges.append(f"{start}-{end}")
                    start = valid_ids[i]
                    end = valid_ids[i]
            
            if start == end:
                compressed_ranges.append(f"{start}")
            else:
                compressed_ranges.append(f"{start}-{end}")
            
            # 每个压缩段显示在一行
            for segment in compressed_ranges:
                f.write(f"  {segment}\n")
            
            f.write("\n")
            
            # 写入当前显示谱数据
            f.write(f"{section_title}\n")
            f.write(f"{x_label}\tCounts\n")
            f.write("-" * 30 + "\n")

            # 确保数据长度一致
            if len(x_data) != len(counts_data):
                # 如果长度不一致，取较小值
                min_len = min(len(x_data), len(counts_data))
                x_data = x_data[:min_len]
                counts_data = counts_data[:min_len]

            # 写入数据点
            for x_val, count in zip(x_data, counts_data):
                f.write(f"{x_val:.6f}\t{count:.2f}\n")

    def _save_region_image(self, img_path):
        """保存TOF谱图片"""
        self.tof_figure.savefig(img_path, format='png', dpi=150, bbox_inches='tight')

    def show_help_document(self):
        """显示使用说明文档"""
        help_dialog = QDialog(self)
        help_dialog.setWindowTitle("TOF谱查看器使用指南")
        help_dialog.resize(800, 600)
        
        text_browser = QTextBrowser()
        text_browser.setHtml(HELP_DOCUMENT)
        text_browser.setOpenExternalLinks(True)
        
        layout = QVBoxLayout()
        layout.addWidget(text_browser)
        
        button_box = QDialogButtonBox(QDialogButtonBox.Close)
        button_box.accepted.connect(help_dialog.accept)
        button_box.rejected.connect(help_dialog.reject)
        
        layout.addWidget(button_box)
        help_dialog.setLayout(layout)
        
        help_dialog.exec_()

# 主程序入口保持不变
if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    app.setStyle("Fusion")
    window = Tof2dWindow()
    window.setWindowTitle("2D-Tof显示窗口")
    window.resize(1600, 1200)
    window.show()
    sys.exit(app.exec_())