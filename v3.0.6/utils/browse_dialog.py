# 自定义的文件浏览窗口，被用于browse_file.py中的选择文件/文件夹功能
from PyQt5 import QtWidgets, QtCore, QtGui
import os,re

class FolderSelectionDialog(QtWidgets.QDialog):
    def __init__(self, parent=None, initial_path=None):
        super().__init__(parent)
        self.setWindowTitle('Select Folders')
        self.resize(600, 400)

        # 设置字体大小
        font = QtGui.QFont()
        font.setPointSize(14)  # 设置字体大小为10，这个值可以根据需要调整
        self.setFont(font)

        # 如果提供了初始路径，则使用它，否则使用当前运行目录
        self.initial_path = initial_path if initial_path else QtCore.QDir.currentPath()

        self.treeView = QtWidgets.QTreeView(self)
        self.model = QtWidgets.QFileSystemModel()
        self.model.setRootPath('')  # 设置为空字符串以显示所有驱动器
        self.model.setFilter(QtCore.QDir.NoDotAndDotDot | QtCore.QDir.AllDirs)

        self.treeView.setModel(self.model)
        self.treeView.setRootIndex(self.model.index(''))  # 设置为空字符串以显示所有驱动器
        self.treeView.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.treeView.hideColumn(1)  # 隐藏大小列
        self.treeView.hideColumn(2)  # 隐藏类型列
        self.treeView.hideColumn(3)  # 隐藏修改日期列

        # 如果有初始路径，定位到该路径
        if self.initial_path:
            index = self.model.index(self.initial_path)
            self.treeView.setCurrentIndex(index)
            self.treeView.expand(index)
            self.treeView.scrollTo(index)

        self.buttonBox = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel,
                                                    self)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.treeView)
        layout.addWidget(self.buttonBox)

        self.setLayout(layout)

    def selectedFolders(self):
        indexes = self.treeView.selectionModel().selectedIndexes()
        folders = []
        for index in indexes:
            if index.column() == 0:  # 只添加目录（第0列是名称）
                path = self.model.filePath(index)
                folders.append(path)
        return folders


class FileSelectionDialog(QtWidgets.QDialog):
    def __init__(self, folder_paths, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Select Files')
        self.resize(400, 300)

        # 字体
        font = QtGui.QFont()
        font.setPointSize(14)
        self.setFont(font)

        self.listWidget = QtWidgets.QListWidget(self)
        self.listWidget.setSelectionMode(QtWidgets.QAbstractItemView.MultiSelection)

        # 收集全部文件（folder/filename）
        all_files = []
        for folder_path in folder_paths:
            folder_name = os.path.basename(os.path.normpath(folder_path))
            try:
                for file_name in os.listdir(folder_path):
                    if not os.path.isfile(os.path.join(folder_path, file_name)):
                        continue
                    if not file_name.lower().endswith('.nxs'):
                        continue
                    all_files.append(f"{folder_name}/{file_name}")
            except FileNotFoundError:
                continue

        # 自然排序：对路径的每个部分（文件夹、文件名）分别做“数字按数值”+“字母忽略大小写”
        def natural_key(s: str):
            parts = s.split('/')  # ["folder", "file.ext"]
            def chunk_key(text):
                return [int(t) if t.isdigit() else t for t in re.split(r'(\d+)', text.lower())]
            # 展平：对每个段生成一串 key，再拼成一个大元组作为排序键
            return tuple(x for seg in parts for x in chunk_key(seg))

        all_files.sort(key=natural_key)

        # 一次性添加（排序后）
        self.listWidget.addItems(all_files)

        # 按钮与布局
        self.buttonBox = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel, self
        )
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.listWidget)
        layout.addWidget(self.buttonBox)
        self.setLayout(layout)

    def selectedFiles(self):
        return [item.text() for item in self.listWidget.selectedItems()]


class DetectorSelectionDialog(QtWidgets.QDialog):
    def __init__(self, group_info, bank_info, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Select Detectors')
        self.resize(400, 300)

        # 设置字体大小
        font = QtGui.QFont()
        font.setPointSize(14)  # 设置字体大小为10，这个值可以根据需要调整
        self.setFont(font)

        self.listWidget = QtWidgets.QListWidget(self)
        self.listWidget.setSelectionMode(QtWidgets.QAbstractItemView.MultiSelection)

        #添加detector name到列表中
        for name in group_info.keys():
            self.listWidget.addItem(f"{name}")
        for name in bank_info.keys():
            self.listWidget.addItem(f"{name}")
        for names in bank_info.values():
            for name in names:
                self.listWidget.addItem(f"{name}")

        self.buttonBox = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel,
                                                    self)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.listWidget)
        layout.addWidget(self.buttonBox)

        self.setLayout(layout)

    def selectedFiles(self):
        selected_items = self.listWidget.selectedItems()
        selected_files = [item.text() for item in selected_items]
        return selected_files


class UtilsSelectionDialog(QtWidgets.QDialog):
    def __init__(self, detectors_list, window_title="Select Files", parent=None, single_selection=False):
        super().__init__(parent)
        self.setWindowTitle(window_title)

        # 设置字体大小
        font = QtGui.QFont()
        font.setPointSize(14)  # 设置字体大小为10，这个值可以根据需要调整
        self.setFont(font)

        self.listWidget = QtWidgets.QListWidget(self)

        # 根据参数设置单选或多选模式
        if single_selection:
            self.listWidget.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        else:
            self.listWidget.setSelectionMode(QtWidgets.QAbstractItemView.MultiSelection)

        # 添加detector name到列表中
        for detector in detectors_list:
            self.listWidget.addItem(f"{detector}")

        self.buttonBox = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel,
            self
        )
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.listWidget)
        layout.addWidget(self.buttonBox)
        self.setLayout(layout)

        self._resize_to_contents(detectors_list)

    def _resize_to_contents(self, detectors_list):
        """根据内容自动调整对话框大小，并限制到当前屏幕范围内。"""
        font_metrics = QtGui.QFontMetrics(self.font())
        longest_item = max(detectors_list, key=len, default="")
        list_width = font_metrics.horizontalAdvance(longest_item) + 120

        row_height = self.listWidget.sizeHintForRow(0)
        if row_height <= 0:
            row_height = font_metrics.height() + 8

        visible_rows = max(4, min(len(detectors_list), 18))
        list_height = row_height * visible_rows + 24

        button_height = self.buttonBox.sizeHint().height()
        dialog_width = max(520, list_width)
        dialog_height = list_height + button_height + 80

        screen = QtWidgets.QApplication.primaryScreen()
        if screen is not None:
            available = screen.availableGeometry()
            dialog_width = min(dialog_width, int(available.width() * 0.85))
            dialog_height = min(dialog_height, int(available.height() * 0.85))

        self.resize(dialog_width, dialog_height)

    def selectedFiles(self):
        selected_items = self.listWidget.selectedItems()
        selected_files = [item.text() for item in selected_items]
        return selected_files