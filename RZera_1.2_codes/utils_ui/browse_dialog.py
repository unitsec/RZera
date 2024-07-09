from PyQt5 import QtCore,QtWidgets
import os


class FolderSelectionDialog(QtWidgets.QDialog):
    def __init__(self, parent=None, initial_path=None):
        super().__init__(parent)
        self.setWindowTitle('Select Folders')
        self.resize(600, 400)

        self.initial_path = initial_path if initial_path else QtCore.QDir.currentPath()

        self.treeView = QtWidgets.QTreeView(self)
        self.model = QtWidgets.QFileSystemModel()
        self.model.setRootPath('')
        self.model.setFilter(QtCore.QDir.NoDotAndDotDot | QtCore.QDir.AllDirs)

        self.treeView.setModel(self.model)
        self.treeView.setRootIndex(self.model.index(''))
        self.treeView.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.treeView.hideColumn(1)
        self.treeView.hideColumn(2)
        self.treeView.hideColumn(3)

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
            if index.column() == 0:
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

        for folder_path in folder_paths:
            folder_name = QtCore.QFileInfo(folder_path).fileName()
            for file_name in os.listdir(folder_path):
                file_path = os.path.join(folder_path, file_name)
                if os.path.isfile(file_path):
                    _, file_extension = os.path.splitext(file_name)
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