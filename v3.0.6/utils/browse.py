# 打开文件浏览窗口，选择文件/文件夹路径

import os
from PyQt5 import QtWidgets,QtCore
import posixpath
from utils.browse_dialog import FileSelectionDialog, FolderSelectionDialog, DetectorSelectionDialog,  UtilsSelectionDialog
import traceback


class browse:
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

    # def select_folder(self, lineEdit, parent=None):
    #     # 创建一个 QFileDialog 对象
    #     dialog = QtWidgets.QFileDialog(parent, "Select Folder")
    #     # 设置文件模式为 Directory 和 Files 模式
    #     dialog.setFileMode(QtWidgets.QFileDialog.Directory)
    #     # 设置视图模式（可选）
    #     dialog.setViewMode(QtWidgets.QFileDialog.List)
    #     # 配置选项，允许显示所有文件和文件夹，但可以选择目录
    #     dialog.setOption(QtWidgets.QFileDialog.ShowDirsOnly, False)
    #     dialog.setOption(QtWidgets.QFileDialog.DontUseNativeDialog, True)
    #     dialog.setOption(QtWidgets.QFileDialog.DontResolveSymlinks, True)
    #     dialog.setOption(QtWidgets.QFileDialog.DontUseCustomDirectoryIcons, True)
    #     # 添加过滤器（可选）
    #     dialog.setNameFilter("All Files (*)")
    #     # 设置确定按钮的功能，使其在选择文件夹时也可以使用
    #     dialog.setFileMode(QtWidgets.QFileDialog.Directory)
    #     dialog.setOption(QtWidgets.QFileDialog.ReadOnly, True)
    #     # 获取所选路径
    #     if dialog.exec_():
    #         selected_path = dialog.selectedFiles()[0]
    #         if selected_path:
    #             # 确保选择的是目录
    #             if os.path.isdir(selected_path):
    #                 lineEdit.setText(selected_path)
    #             else:
    #                 lineEdit.setText(os.path.dirname(selected_path))

    def select_nxsfiles(self,lineEdit,run_filePaths,parent=None):
        try:
            dialog = FolderSelectionDialog(None, self.last_selected_path or QtCore.QDir.currentPath())
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
        except Exception as e:
            print(f'Reason: {e}')
            traceback.print_exc()  # 打印异常的堆栈跟踪

    def select_detectors(self,lineEdit,group_info,bank_info,parent=None):
        detector_dialog = DetectorSelectionDialog(group_info,bank_info, parent)
        if detector_dialog.exec_() == QtWidgets.QDialog.Accepted:
            selected_files = detector_dialog.selectedFiles()
            lineEdit.setText('; '.join(selected_files)) # 更新 QLineEdit 控件的文本

    def select_utils(self,lineEdit,file_list,parent=None):
        dialog = UtilsSelectionDialog(file_list, parent)
        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            selected_files = dialog.selectedFiles()
            lineEdit.setText('; '.join(selected_files)) # 更新 QLineEdit 控件的文本

    def select_ncfiles(self, nc_files_path, parent=None):
        try:
            # 设置文件对话框选项
            options = QtWidgets.QFileDialog.Options()
            # 打开多文件选择对话框，只显示后缀名为.nc的文件
            selected_file_paths, _ = QtWidgets.QFileDialog.getOpenFileNames(
                parent, "Select NetCDF Files", self.last_selected_path or "", "NetCDF files (*.nc)", options=options)
            if selected_file_paths:
                nc_files_path.clear()
                # 如果用户选择了文件，记录最后一次选择的目录
                self.last_selected_path = os.path.dirname(selected_file_paths[0])
                nc_files_path.extend(selected_file_paths)
            return selected_file_paths
        except Exception as e:
            print(f'Reason: {e}')
            traceback.print_exc()
            return []

    def select_datfiles(self, dat_files_path, parent=None):
        try:
            # 设置文件对话框选项
            options = QtWidgets.QFileDialog.Options()
            # 打开多文件选择对话框，只显示后缀名为.nc的文件
            selected_file_paths, _ = QtWidgets.QFileDialog.getOpenFileNames(
                parent, "Select dat Files", self.last_selected_path or "", "dat files (*.dat)", options=options)
            if selected_file_paths:
                dat_files_path.clear()
                # 如果用户选择了文件，记录最后一次选择的目录
                self.last_selected_path = os.path.dirname(selected_file_paths[0])
                dat_files_path.extend(selected_file_paths)
            return selected_file_paths
        except Exception as e:
            print(f'Reason: {e}')
            traceback.print_exc()
            return []


