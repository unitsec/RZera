from PyQt5.QtWidgets import QMainWindow, QApplication, QWidget
from BL15_HPND.ui.ui_BL15_window import Ui_MainWindow
# import os
# import sys
# # 使用 os.sep 或者直接将路径分割成多个参数传递给 os.path.join
# subfolder_path = os.path.join(os.path.dirname(__file__), 'drneutron', 'python')

# sys.path.insert(0, subfolder_path)
from BL15_HPND.BL15_diffraction_small import diffraction_small
from BL15_HPND.BL15_diffraction_big import diffraction_big
import traceback
from utils.helper import pop_window


class BL15_HP(QMainWindow, Ui_MainWindow):
    def __init__(self):
        super(BL15_HP, self).__init__()
        self.setupUi(self)

        ############################ 将Tab页面加载到mainwondow中 ##############################
        # 创建Tab"diffraction" "diffraction_small" "diffraction_big"的实例
        # self.diffraction_instance = diffraction(self)
        self.diffraction_instance_small = diffraction_small(self)
        self.diffraction_instance_big = diffraction_big(self)

        # 将Tab"diffraction"添加到QTabWidget中
        # self.tabWidget.addTab(self.diffraction_instance, "Diffraction")

        self.tabWidget.addTab(self.diffraction_instance_small, "Hutch1")

        self.tabWidget.addTab(self.diffraction_instance_big, "Hutch2")

        # self.pdf_instance = pdf(self)

        # self.tabWidget.addTab(self.pdf_instance, 'PDF')

        ########################## 设置菜单栏 ##############################
        # 获取 QAction “reduct_v_or_hold” 并连接到 pop_window
        # self.offset_creation.triggered.connect(lambda: pop_window(bl16_offset, self))

    def closeEvent(self, event):
        try:
            # if self.diffraction_instance.reduction_thread.reduction_thread != None and self.diffraction_instance.reduction_thread.reduction_thread.isRunning():
            #     # 在窗口关闭时停止线程
            #     self.diffraction_instance.reduction_thread.reduction_thread.stop()
            #     self.diffraction_instance.reduction_thread.reduction_thread.wait()  # 等待线程真正结束

            if self.diffraction_instance_small.reduction_thread.reduction_thread != None and self.diffraction_instance_small.reduction_thread.reduction_thread.isRunning():
                # 在窗口关闭时停止线程
                self.diffraction_instance_small.reduction_thread.reduction_thread.stop()
                self.diffraction_instance_small.reduction_thread.reduction_thread.wait()  # 等待线程真正结束

            if self.diffraction_instance_big.reduction_thread.reduction_thread != None and self.diffraction_instance_big.reduction_thread.reduction_thread.isRunning():
                # 在窗口关闭时停止线程
                self.diffraction_instance_big.reduction_thread.reduction_thread.stop()
                self.diffraction_instance_big.reduction_thread.reduction_thread.wait()  # 等待线程真正结束
            # if self.pdf_instance.cal_sq_thread.sqcal_thread != None and self.pdf_instance.cal_sq_thread.sqcal_thread.isRunning():
            #     # 在窗口关闭时停止线程
            #     self.pdf_instance.cal_sq_thread.sqcal_thread.stop()
            #     self.pdf_instance.cal_sq_thread.sqcal_thread.wait()  # 等待线程真正结束
        except Exception as e:
            print(f"An error occurred: {e}")
            traceback.print_exc()  # 打印异常的堆栈跟踪
        super().closeEvent(event)
