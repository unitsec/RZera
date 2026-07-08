from PyQt5.QtWidgets import QMainWindow, QApplication, QMessageBox, QAction, QSplashScreen
from PyQt5.QtCore import QEvent, Qt
from PyQt5.QtGui import QPixmap
import traceback
import os
import sys

if os.path.exists("/cvmfs/daas.csns.ihep.ac.cn/softwares/RZera/rzera_offline/openRongzai/plugins/platforms"):
    os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = "/cvmfs/daas.csns.ihep.ac.cn/softwares/RZera/rzera_offline/openRongzai/plugins/platforms"
    os.environ["XDG_DATA_DIRS"] = "$XDG_DATA_DIRS:/cvmfs/daas.csns.ihep.ac.cn/softwares/RZera/rzera_offline"


def _get_local_resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(__file__)
    return os.path.join(base_path, relative_path)


def create_startup_splash():
    pixmap = QPixmap(":/rzera/resized_rzera_logo.png")
    if pixmap.isNull():
        pixmap = QPixmap(_get_local_resource_path("logo/resized_rzera_logo.png"))

    if pixmap.isNull():
        return None

    splash = QSplashScreen(pixmap, Qt.WindowStaysOnTopHint)
    splash.setWindowFlag(Qt.FramelessWindowHint, True)
    splash.showMessage("Loading RZera...", Qt.AlignBottom | Qt.AlignHCenter, Qt.white)
    splash.show()
    QApplication.processEvents()
    return splash

class rzera2(QMainWindow):
    def __init__(self):
        super(rzera2, self).__init__()
        from ui_mainwindow import Ui_MainWindow
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.childWindows = []  # 用于保存打开的子窗口引用

        ############################ 将状态栏显示信息 ##############################
        self.statusBar().showMessage("technique support: wanghao96@ihep.ac.cn")
        self.ui.reduction_open.clicked.connect(self.open_reduction)

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
        # 获取 QAction "reduct_v_or_hold" 并连接到 pop_window
        # self.offset_correct.triggered.connect(lambda: pop_window(reduct_v_hold, self))
        
        # 添加Python脚本编辑器菜单项
        self.ui.actionPythonEditor.triggered.connect(self._open_code_editor)
        # 添加2D-Tof显示窗口菜单项
        self.ui.action2D_Tof_show_window.triggered.connect(self._open_tof2d_window)
        # 添加Plot Window菜单项
        self.ui.actionPlotWindow.triggered.connect(self._open_plot_window)
        self.ui.actionHow_to_Use.triggered.connect(self._open_help_pdf)

    def _open_code_editor(self):
        from utils.helper import pop_window
        from utils.ui.code_editor import CodeEditor
        pop_window(CodeEditor, self)

    def _open_tof2d_window(self):
        from utils.helper import pop_window
        from utils.ui.Tof_2d_window import Tof2dWindow
        pop_window(Tof2dWindow, self)

    def _open_help_pdf(self):
        from utils.helper import open_pdf
        open_pdf()

    def _open_plot_window(self):
        from utils.ui.plot_window import plot_window
        dialog = plot_window({}, None)
        dialog.setWindowFlag(Qt.Window, True)
        dialog.setup_plot_list()
        dialog.show()
        self.childWindows.append(dialog)

    def _start_loading(self, instru):
        """显示等待光标和状态栏提示，并立即刷新 UI。"""
        self.statusBar().showMessage(f"Loading {instru}, please wait...")
        QApplication.setOverrideCursor(Qt.WaitCursor)
        QApplication.processEvents()

    def _stop_loading(self):
        """恢复光标和状态栏默认信息。"""
        QApplication.restoreOverrideCursor()
        self.statusBar().showMessage("technique support: wanghao96@ihep.ac.cn, zhongjiajun@ihep.ac.cn")

    def open_reduction(self):
        instru = self.ui.instru_select.currentText()
        self._start_loading(instru)
        try:
            if instru == 'BL01_SANS':
                from BL01_SANS.BL01_cloud.SANS_window import BL01_SANS
                dialog = BL01_SANS()
                dialog.show()
                self.childWindows.append(dialog)
            elif instru == 'BL09_TREND':
                from BL09_TREND.BL09_window2 import BL09_TREND
                dialog = BL09_TREND()
                dialog.show()
                self.childWindows.append(dialog)
            # elif instru == 'BL13_ERNI':
            #     from BL13_ERNI.BL13_window import BL13_ERNI
            #     dialog = BL13_ERNI()
            #     dialog.show()
            #     self.childWindows.append(dialog)
            elif instru == 'BL14_VSANS':
                from BL14_VSANS.VSANS_mainwindow import BL14_VSANS
                dialog = BL14_VSANS()
                dialog.show()
                self.childWindows.append(dialog)
            elif instru == 'BL15_HPND':
                from BL15_HPND.BL15_window2 import BL15_HPND
                dialog = BL15_HPND()
                dialog.show()
                self.childWindows.append(dialog)
            elif instru == 'BL16_MPI':
                from BL16_MPI.BL16_window2 import BL16_MPI
                dialog = BL16_MPI()
                dialog.show()
                self.childWindows.append(dialog)
            # elif instru == 'BL18_GPPD':
            #     from BL18_GPPD.BL18_window import BL18_GPPD
            #     dialog = BL18_GPPD()
            #     dialog.show()
            #     self.childWindows.append(dialog)
        except Exception as e:
            print(f"An error occurred: {e}")
            traceback.print_exc()  # 打印异常的堆栈跟踪
        finally:
            self._stop_loading()

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

    def event(self, e):
        # 忽略 StatusTip 事件，防止菜单或动作悬停时覆盖状态栏中的固定消息
        if e.type() == QEvent.StatusTip:
            return True
        return super(rzera2, self).event(e)


if __name__ == "__main__":
    import multiprocessing
    multiprocessing.freeze_support()
    app = QApplication([])
    splash = create_startup_splash()
    window = rzera2()
    window.show()
    if splash is not None:
        splash.finish(window)
    app.exec_()
