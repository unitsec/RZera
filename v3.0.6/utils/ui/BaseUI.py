from rongzai.utils import get_all_from_detector
from utils.helper import get_resource_path
from PyQt5.QtWidgets import QWidget, QToolButton, QSizePolicy, QFrame
from PyQt5.QtCore import Qt
from PyQt5.uic import loadUi
from utils.ui.plot_window import plot_window
from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QVBoxLayout, QHBoxLayout, QScrollArea, QFileDialog
from PyQt5.QtCore import pyqtSignal,QTimer,QEventLoop
from PyQt5.QtGui import QFont
import copy,json,traceback

class BaseDataProcessor(QtWidgets.QWidget):
    def __init__(self, parent):
        super(BaseDataProcessor, self).__init__(parent)

    def split_by_name(self, data_list):
        split_data = {}

        for item in data_list:
            runno = item["name"]

            if runno not in split_data:
                split_data[runno] = []

            split_data[runno].append(item)

        return split_data

    def get_module_list(self, items, config):
        modules_set = set()
        for data in items:
            _, modules = get_all_from_detector(data['detector'], config['group_info'],
                                               config['bank_info'])
            modules_set.update(modules)  # 将 modules 添加到集合中
        modules_list = list(modules_set)  # 将集合转换回列表
        return modules_list

    def update_data(self,items,masked_data_dict):
        # 遍历每个item，并更新module字典（假设masked_data_dict中所有key都在每个item['module']中）
        for item in items:
            module_dict = item.get('modules', {})  # 获取modules字典，默认是空字典
            # 使用字典的update方法进行批量更新
            module_dict.update((key, masked_data_dict[key]) for key in module_dict if key in masked_data_dict)

    def merge_split_data(self,split_data):
        merged_list = []
        for runno, items in split_data.items():
            merged_list.extend(items)
        return merged_list

class RunWidget(QWidget):
    def __init__(self,parent=None):
        super(RunWidget, self).__init__(parent)
        self.set_layout()

    def set_layout(self):
        # 主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(2)

        # 创建一个 QScrollArea
        scroll_area = QScrollArea(self)
        scroll_area.setWidgetResizable(True)  # 设置滚动区域的内容自动调整大小

        # 创建一个 QWidget 作为 QScrollArea 的内容
        scroll_content = QtWidgets.QWidget()
        self.inner_layout = QVBoxLayout(scroll_content)
        self.inner_layout.setContentsMargins(10, 5, 10, 5)
        self.inner_layout.setSpacing(5)

        # 创建一个 QSpacerItem，并且保持引用，以便在添加控件后重新添加到末尾
        self.spacer = QtWidgets.QSpacerItem(
            20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding
        )

        # 将内容放到 QScrollArea 中
        scroll_area.setWidget(scroll_content)
        main_layout.addWidget(scroll_area)

        # Create font object
        font = QFont("Times New Roman", 16, QFont.Bold)  # Set font name, size, and weight
        # 添加按钮布局
        self.button_layout = QHBoxLayout()
        self.run_button = QtWidgets.QPushButton("Run && Plot")
        self.run_button.setFont(font)
        self.run_button.clicked.connect(self.execute_modules)
        self.save_config_button = QtWidgets.QPushButton("Save Configure")
        self.save_config_button.setFont(font)
        self.save_config_button.clicked.connect(self.save_config)
        self.load_config_button = QtWidgets.QPushButton("Load Configure")
        self.load_config_button.setFont(font)
        self.load_config_button.clicked.connect(self.load_config)

        # 添加按钮到布局
        self.button_layout.addWidget(self.run_button)
        self.button_layout.addWidget(self.save_config_button)
        self.button_layout.addWidget(self.load_config_button)

        # 把按钮布局添加到主布局
        main_layout.addLayout(self.button_layout)

    def add_module(self, cls, name=None):
        # 将 self（Reduction 实例）作为参数传递给模块
        if name is None:
            try:
                module = cls(cls.__name__, self)  # 这里传递的是 Reduction 实例
            except:
                module = cls(self)  # 这里传递的是 Reduction 实例
        else:
            module = cls(name, self)
        # 使用 inner_layout 添加模块
        self.inner_layout.removeItem(self.spacer)
        self.inner_layout.addWidget(module)
        self.inner_layout.addItem(self.spacer)
        return module

    def execute_modules(self):
        data_list_backup = copy.deepcopy(self.data_list)
        try:
            # 存储绘图数据的列表
            all_plot_data = []
            # 遍历布局中的所有子组件
            for i in range(self.inner_layout.count()):
                module = self.inner_layout.itemAt(i).widget()
                if hasattr(module, 'run') and callable(getattr(module, 'run')):
                    #下面这一段代码的目的：保证模块串行执行。有些模块的run方法会新开线程执行任务，普通循环在该情况下会直接执行下一个模块，这会导致错误，因此必须保证模块串行执行。
                    # 这个改动保证了即使某些模块使用了异步执行，它们也会被正确地串行化，并且在没有异步操作的情况下不会引入延迟。
                    if hasattr(module, 'finished'):
                        loop = QEventLoop()

                        # 定义一个标志来标记是否已经完成
                        is_finished = False

                        # 定义完成信号的处理器
                        def on_finished():
                            nonlocal is_finished
                            is_finished = True
                            loop.quit()

                        module.finished.connect(on_finished)

                        module.run()  # 执行模块

                        # 如果在运行之后已经完成，那么直接退出，不进入事件循环
                        if not is_finished:
                            loop.exec_()  # 启动事件循环

                    else:
                        module.run()

                # 如果模块有 plot 方法和对应的 CheckBox，检查是否选中
                if hasattr(module, 'plot_data') and callable(getattr(module, 'plot_data')):
                    checkbox = getattr(module, 'plot', None)
                    if checkbox is not None and checkbox.isChecked():
                        plot_data = module.plot_data()
                        if len(plot_data) != 0:
                            module_name = module.objectName()
                            all_plot_data.append({module_name: plot_data})
            self.plot_combined(all_plot_data)  # 绘制综合图形

        except Exception as e:
            print(f'Reason: {e}')
            traceback.print_exc()  # 打印异常的堆栈跟踪
        finally:
            # 无论运行是否报错，都恢复到运行前数据，保证重复执行可复现。
            self.data_list = data_list_backup

    def execute_previous_modules(self,current_module):
        """运行前置模块并收集绘图数据"""
        data_list_backup = copy.deepcopy(self.data_list)
        try:
            all_plot_data = []
            
            for i in range(self.inner_layout.count()):
                item_widget = self.inner_layout.itemAt(i).widget()
                
                # 检查是否为 None（可能是 QSpacerItem 等）
                if item_widget is None:
                    continue
                
                # 检查是否是当前模块，如果是则停止
                if item_widget.objectName() == current_module:
                    break
                
                # 检查模块是否有 run 方法
                if hasattr(item_widget, 'run') and callable(getattr(item_widget, 'run')):
              
                    # 运行模块，采用与 execute_modules 相同的策略处理异步
                    if hasattr(item_widget, 'finished'):
                        # 模块有异步执行，使用事件循环等待完成
                        loop = QEventLoop()
                        is_finished = False
                        
                        def on_finished():
                            nonlocal is_finished
                            is_finished = True
                            loop.quit()
                        
                        item_widget.finished.connect(on_finished)
                        item_widget.run()
                        
                        # 如果还未完成，则进入事件循环等待
                        if not is_finished:
                            loop.exec_()
                    else:
                        # 同步执行
                        item_widget.run()
                
                # 收集绘图数据（参考 execute_modules 的逻辑）
                if hasattr(item_widget, 'plot_data') and callable(getattr(item_widget, 'plot_data')):
                    checkbox = getattr(item_widget, 'plot', None)
                    if checkbox is not None and checkbox.isChecked():
                        plot_data = item_widget.plot_data()
                        if len(plot_data) != 0:
                            module_name = item_widget.objectName()
                            all_plot_data.append({module_name: plot_data})
            # 绘制前置模块的综合图形
            self.plot_combined(all_plot_data)

                    
        except Exception as e:
            print(f'Error executing previous modules: {e}')
            traceback.print_exc()
        finally:
            # 无论前置模块执行是否成功，都恢复原始数据。
            self.data_list = data_list_backup
        
    
    def run_previous_modules(self, current_module):
        """运行前置模块 (确保当前模块执行前，所有前置模块都已完成)"""
        try:
            for i in range(self.inner_layout.count()):
                item_widget = self.inner_layout.itemAt(i).widget()
                
                # 检查是否为 None（可能是 QSpacerItem 等）
                if item_widget is None:
                    continue
                
                # 检查是否是当前模块，如果是则停止
                if item_widget.objectName() == current_module:
                    break
                
                # 检查模块是否有 run 方法
                if hasattr(item_widget, 'run') and callable(getattr(item_widget, 'run')):
                    continue
                
                # 运行模块，采用与 execute_modules 相同的策略处理异步
                if hasattr(item_widget, 'finished'):
                    # 模块有异步执行，使用事件循环等待完成
                    loop = QEventLoop()
                    is_finished = False
                    
                    def on_finished():
                        nonlocal is_finished
                        is_finished = True
                        loop.quit()
                    
                    item_widget.finished.connect(on_finished)
                    item_widget.run()
                    
                    # 如果还未完成，则进入事件循环等待
                    if not is_finished:
                        loop.exec_()
                else:
                    # 同步执行
                    item_widget.run()
                    
        except Exception as e:
            print(f'Error running previous modules: {e}')
            traceback.print_exc()


    def plot_combined(self, all_plot_data):
        if len(all_plot_data) != 0:
            plot_dict = {}
            for plot_data in all_plot_data:
                for key, data_list in plot_data.items():
                    for data in data_list:
                        plot_dict[f"{data['name']}_{key}"] = [data["data"][0],data["data"][1],data["x_label"],data["y_label"]]
            if not hasattr(self, 'plot_win'):
                self.plot_win = plot_window(plot_dict, None)

                self.plot_win.setup_plot_list()
                self.plot_win.show()
            else:
                self.plot_win.update_plot_data(plot_dict)
                self.plot_win.show()

    data_updated = pyqtSignal(dict)

    def module_value_changed(self, module):
        """当任一模块的值发生变化时调用"""
        if hasattr(self, 'plot_win') and self.plot_win.isVisible():
            # 启动防抖定时器
            if not hasattr(self, '_update_timer'):
                self._update_timer = QTimer()
                self._update_timer.setSingleShot(True)
                self._update_timer.timeout.connect(self.execute_modules)
            self._update_timer.start(10)  # 50ms防抖

    def save_config(self):
        """保存当前界面配置到文件"""
        try:
            config = {}
            for i in range(self.inner_layout.count()):
                module = self.inner_layout.itemAt(i).widget()
                if hasattr(module, 'get_config') and callable(getattr(module, 'get_config')):
                    module_name = module.objectName()
                    config[module_name] = module.get_config()
            options = QFileDialog.Options()
            filename, _ = QFileDialog.getSaveFileName(self, "Save Config", "", "JSON Files (*.json);;All Files (*)", options=options)
            if filename:
                # 确保文件名以 .json 结尾
                if not filename.lower().endswith('.json'):
                    filename += '.json'
                # 将配置保存到选择的文件中
                with open(filename, 'w') as config_file:
                    json.dump(config, config_file, indent=4)  # 使用 indent 参数格式化 JSON 输出
        except Exception as e:
            print(f"Error save configuration: {e}")

    def load_config(self):
        """从文件加载配置到界面"""
        try:
            # 打开文件选择对话框
            options = QtWidgets.QFileDialog.Options()
            config_file_path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Select Config File", "", "JSON Files (*.json)", options=options)
            if config_file_path:
                # 读取并加载配置文件
                with open(config_file_path, 'r', encoding='utf-8') as json_file:
                    config = json.load(json_file)
                for i in range(self.inner_layout.count()):
                    module = self.inner_layout.itemAt(i).widget()
                    if hasattr(module, 'set_config') and callable(getattr(module, 'set_config')):
                        module_name = module.objectName()
                        if module_name in config:
                            module.set_config(config[module_name])
        except FileNotFoundError:
            traceback.print_exc()  # 打印异常的堆栈跟踪
            print("Configuration file not found!")
        except Exception as e:
            traceback.print_exc()  # 打印异常的堆栈跟踪
            print(f"Error loading configuration: {e}")


class CollapsibleWidget(QFrame):
    def __init__(self, title, ui_file, parent=None):
        super(CollapsibleWidget, self).__init__(parent)

        # Set object name for styling purposes
        self.setObjectName(title.replace(" ", "").replace("(", "").replace(")", ""))
        self.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Maximum)

        # 检查模块是否有 run() 方法，以确定背景颜色
        bg_color = self._determine_bg_color(parent)

        # Style for the components in main_layout
        self.overall_stylesheet = f"""
                    QFrame#{title.replace(" ", "").replace("(", "").replace(")", "")} {{
                        background-color: {bg_color};
                        border: 1px solid #ccc;
                        border-radius: 5px;
                    }}
                    QToolButton {{
                        background-color: #e0e0e0;
                        border: 1px solid #ccc;
                        padding: 5px;
                        border-radius: 3px;
                    }}
                    QToolButton:checked {{
                        background-color: {bg_color};
                        border: none;
                    }}
                """

        self.setStyleSheet(self.overall_stylesheet)

        # Setup the toggle button
        self.toggle_button = QToolButton(self)

        # Font and setup
        font = QFont("Times New Roman", 16)
        font.setWeight(QFont.Bold)
        self.toggle_button.setFont(font)
        self.toggle_button.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.toggle_button.setArrowType(Qt.RightArrow)
        self.toggle_button.setText(title)
        self.toggle_button.setCheckable(True)
        self.toggle_button.setChecked(False)
        # self.toggle_button.clicked.connect(self.toggle_content)
        self.toggle_button.toggled.connect(self.toggle_content)

        # Set size policy for the button
        self.toggle_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        # Create a content widget as container
        self.content_area = QWidget(self)
        self.content_area.setMaximumHeight(0)
        self.content_area.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.content_area.setContentsMargins(10, 10, 10, 10)

        # Load UI and style it
        self._load_ui(ui_file)

        # Main layout setup
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setSpacing(0)
        self.main_layout.setContentsMargins(0, 0, 0, 0)  # Ensure margins for border visibility

        # Layout for the toggle button
        button_layout = QHBoxLayout()
        button_layout.setContentsMargins(0, 0, 0, 0)
        button_layout.addWidget(self.toggle_button)

        self.main_layout.addLayout(button_layout)
        self.main_layout.addWidget(self.content_area)

        # for child in self.findChildren(QWidget):
        #     print(child)

    def _determine_bg_color(self, parent):
        """根据当前类是否有 run() 方法来确定背景颜色"""
        if hasattr(self, 'run') and callable(getattr(self, 'run', None)):
            return 'lightblue'  # 有 run() 方法，使用蓝色
        else:
            return '#eaf4ff'  # 没有 run() 方法，使用柔和浅蓝色

    def _load_ui(self, ui_file):
        # Temporary widget to load .ui
        temp_widget = QWidget()
        loadUi(get_resource_path(ui_file), temp_widget)

        # Setup layout for content area
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.content_area.setLayout(layout)
        self.content_area.layout().addWidget(temp_widget)

        # Map loaded child widgets to `self` for direct access
        for child in temp_widget.findChildren(QWidget):
            setattr(self, child.objectName(), child)


    def toggle_content(self):
        if self.toggle_button.isChecked():
            self.toggle_button.setArrowType(Qt.DownArrow)
            self.content_area.setMaximumHeight(16777215)
        else:
            self.toggle_button.setArrowType(Qt.RightArrow)
            self.content_area.setMaximumHeight(0)

    def split_by_name(self, data_list):
        split_data = {}

        for item in data_list:
            runno = item["name"]

            if runno not in split_data:
                split_data[runno] = []

            split_data[runno].append(item)

        return split_data

    def get_module_list(self, items, config):
        modules_set = set()
        for data in items:
            _, modules = get_all_from_detector(data['detector'], config['group_info'],
                                               config['bank_info'])
            modules_set.update(modules)  # 将 modules 添加到集合中
        modules_list = list(modules_set)  # 将集合转换回列表
        return modules_list

    def update_data(self,items,masked_data_dict):
        # 遍历每个item，并更新module字典（假设masked_data_dict中所有key都在每个item['module']中）
        for item in items:
            module_dict = item.get('modules', {})  # 获取modules字典，默认是空字典
            # 使用字典的update方法进行批量更新
            module_dict.update((key, masked_data_dict[key]) for key in module_dict if key in masked_data_dict)

    def merge_split_data(self,split_data):
        merged_list = []
        for runno, items in split_data.items():
            merged_list.extend(items)
        return merged_list