import os
from PyQt5 import QtWidgets,QtCore
import posixpath
from utils.browse_dialog import FileSelectionDialog,FolderSelectionDialog


class browse_file:
    def __init__(self):
        self.last_selected_path = None  # 初始化为 None

    def select_nxsfile(self, run_filePaths, run_text, parent=None):
        # 打开 QFileDialog 来选择文件
        options = QtWidgets.QFileDialog.Options()
        selected_file_paths, _ = QtWidgets.QFileDialog.getOpenFileNames(
            parent, "Select Files", "", "NeXus files (*.nxs)", options=options)
        if selected_file_paths:
            # 添加新选择的文件路径到列表中
            run_filePaths.extend(selected_file_paths)
            # 更新 QLineEdit 控件显示的包含文件名和上一级文件夹名的文件路径
            fileNamesWithParents = []
            for filePath in run_filePaths:
                folder_name = os.path.basename(os.path.dirname(filePath))  # 上一级文件夹名
                file_name = os.path.basename(filePath)  # 文件名
                fileNamesWithParents.append(f"{folder_name}/{file_name}")  # 组合上一级文件夹名和文件名
            fileNamesStr = '; '.join(fileNamesWithParents)
            run_text.setText(fileNamesStr)

    def select_folder(self, lineEdit, parent=None):
        # 打开文件夹选择对话框
        folder_path = QtWidgets.QFileDialog.getExistingDirectory(parent, "Select Folder")
        if folder_path:
            # 设置对应的 QLineEdit 控件的文本为选择的文件夹路径
            lineEdit.setText(folder_path)

    def select_nxsfiles(self, lineEdit, run_filePaths,parent=None):
        dialog = FolderSelectionDialog(parent, self.last_selected_path or QtCore.QDir.currentPath())
        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            folder_paths = dialog.selectedFolders()
            if folder_paths:
                # 记忆最后一个选择的路径
                self.last_selected_path = folder_paths[-1]
                # 显示文件选择对话框
                file_dialog = FileSelectionDialog(folder_paths, parent)
                if file_dialog.exec_() == QtWidgets.QDialog.Accepted:
                    selected_files = file_dialog.selectedFiles()
                    # 更新 QLineEdit 控件的文本
                    lineEdit.setText('; '.join(selected_files))
                    run_filePaths.clear()
                    # 保存完整的文件路径
                    for folder_path in folder_paths:
                        folder_name = QtCore.QFileInfo(folder_path).fileName()
                        for file_name in os.listdir(folder_path):
                            if f"{folder_name}/{file_name}" in selected_files:
                                run_filePaths.append(posixpath.join(folder_path, file_name))

