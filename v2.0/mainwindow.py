from PyQt5.QtWidgets import QMainWindow,QApplication,QMessageBox
from ui_mainwindow import Ui_MainWindow
from BL09_TREND.BL09_window import BL09_HRD
import subprocess
from utils.helper import pop_window
import traceback

class MainWindow(QMainWindow, Ui_MainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
        self.setupUi(self)
        self.childWindows = []  # 用于保存打开的子窗口引用

        ############################ 将状态栏显示信息 ##############################
        self.statusBar().showMessage("technique support: zhongjiajun@ihep.ac.cn or 2550239498@qq.com")

        self.reduction_open.clicked.connect(self.open_reduction)

        ############################ 将Tab页面加载到mainwondow中 ##############################
        # # 创建Tab"diffraction"的实例
        # self.diffraction_instance = diffraction(self)
        #
        # # 将Tab"diffraction"添加到QTabWidget中
        # self.tabWidget.addTab(self.diffraction_instance, "Diffraction")
        #
        # self.pdf_instance = pdf(self)
        #
        # self.tabWidget.addTab(self.pdf_instance, 'PDF')

        ########################### 设置菜单栏 ##############################
        # 获取 QAction “reduct_v_or_hold” 并连接到 pop_window
        # self.offset_correct.triggered.connect(lambda: pop_window(reduct_v_hold, self))

    def open_reduction(self):
        try:
            instru = self.instru_select.currentText()
            if instru == 'BL09_TREND':
                dialog = BL09_HRD()
                dialog.show()
                self.childWindows.append(dialog)
        except Exception as e:
            print(f"An error occurred: {e}")
            traceback.print_exc()  # 打印异常的堆栈跟踪

    def closeEvent(self, event):
        try:
            reply = QMessageBox.question(self, 'Close Confirmation', 'Do you want to close the RZera?',
                                         QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if reply == QMessageBox.Yes:
                for window in self.childWindows:
                    window.close()
                event.accept()
            else:
                event.ignore()
        except Exception as e:
            print(f"An error occurred: {e}")
            traceback.print_exc()  # 打印异常的堆栈跟踪


if __name__ == "__main__":
    app = QApplication([])
    window = MainWindow()
    window.show()
    app.exec_()