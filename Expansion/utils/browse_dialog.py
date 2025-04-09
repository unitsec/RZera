# 自定义的文件浏览窗口，被用于browse_file.py中的选择文件/文件夹功能


from PyQt5 import QtCore,QtWidgets
import os


class FolderSelectionDialog(QtWidgets.QDialog):
    def __init__(self, parent=None, initial_path=None):
        super().__init__(parent)
        self.setWindowTitle('Select Folders')
        self.resize(600, 400)

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

        self.listWidget = QtWidgets.QListWidget(self)
        self.listWidget.setSelectionMode(QtWidgets.QAbstractItemView.MultiSelection)

        # 遍历文件夹，添加文件到列表中
        for folder_path in folder_paths:
            folder_name = QtCore.QFileInfo(folder_path).fileName()
            for file_name in os.listdir(folder_path):
                file_path = os.path.join(folder_path, file_name)
                # 检查文件路径是否指向一个文件
                if os.path.isfile(file_path):
                    # 分离文件名和扩展名
                    _, file_extension = os.path.splitext(file_name)
                    # 检查扩展名是否为 .nxs
                    if file_extension.lower() == '.nxs':
                        self.listWidget.addItem(f"{folder_name}/{file_name}")

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