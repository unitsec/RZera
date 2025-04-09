# 进度条
from PyQt5.QtWidgets import (QProgressBar,QVBoxLayout, QDialog)
from PyQt5.QtCore import pyqtSignal

class ProgressDialog(QDialog):
    # 定义一个信号，当对话框关闭时发射
    canceled = pyqtSignal()
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('calculating')
        self.layout = QVBoxLayout(self)
        self.progressBar = QProgressBar(self)
        self.progressBar.setMaximum(100)
        self.layout.addWidget(self.progressBar)
        self.resize(300, 100)  # 调整对话框大小

    def update_progress(self, value):
        self.progressBar.setValue(value)

    # 重写 closeEvent 方法
    def closeEvent(self, event):
        self.canceled.emit()  # 发射取消信号
        super().closeEvent(event)