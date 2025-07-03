import os
from PyQt5 import QtWidgets,QtCore
import posixpath
from utils_ui.browse_dialog import FileSelectionDialog,FolderSelectionDialog


class browse_file:
    def __init__(self):
        self.last_selected_path = None

    def select_nxsfile(self, run_filePaths, run_text, parent=None):
        options = QtWidgets.QFileDialog.Options()
        selected_file_paths, _ = QtWidgets.QFileDialog.getOpenFileNames(
            parent, "Select Files", "", "NeXus files (*.nxs)", options=options)
        if selected_file_paths:
            run_filePaths.extend(selected_file_paths)
            fileNamesWithParents = []
            for filePath in run_filePaths:
                folder_name = os.path.basename(os.path.dirname(filePath))
                file_name = os.path.basename(filePath)
                fileNamesWithParents.append(f"{folder_name}/{file_name}")
            fileNamesStr = '; '.join(fileNamesWithParents)
            run_text.setText(fileNamesStr)

    def select_folder(self, lineEdit, parent=None):
        folder_path = QtWidgets.QFileDialog.getExistingDirectory(parent, "Select Folder")
        if folder_path:
            lineEdit.setText(folder_path)

    def select_nxsfiles(self, lineEdit,run_filePaths,parent=None):
        dialog = FolderSelectionDialog(parent, self.last_selected_path or QtCore.QDir.currentPath())
        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            folder_paths = dialog.selectedFolders()
            if folder_paths:
                self.last_selected_path = folder_paths[-1]
                file_dialog = FileSelectionDialog(folder_paths, parent)
                if file_dialog.exec_() == QtWidgets.QDialog.Accepted:
                    selected_files = file_dialog.selectedFiles()
                    lineEdit.setText('; '.join(selected_files))
                    run_filePaths.clear()
                    for folder_path in folder_paths:
                        folder_name = QtCore.QFileInfo(folder_path).fileName()
                        for file_name in os.listdir(folder_path):
                            if f"{folder_name}/{file_name}" in selected_files:
                                run_filePaths.append(posixpath.join(folder_path, file_name))

