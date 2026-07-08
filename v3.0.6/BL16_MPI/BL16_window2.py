from PyQt5.QtWidgets import QMainWindow
from PyQt5.uic import loadUi
from PyQt5.QtGui import QFont
from BL16_MPI.BL16_TimeFocusing2 import TimeFocusing
from BL16_MPI.BL16_Reduction2 import Reduction
from BL16_MPI.BL16_QuickReduction2 import QuickReduction
from BL16_MPI.BL16_PDF_Hetmite2 import PDFHermite
from BL16_MPI.BL16_PDF_Merge2 import PDFMerge
from BL16_MPI.BL16_offset import bl16_offset
from utils.helper import pop_window,get_resource_path


class BL16_MPI(QMainWindow):
    def __init__(self):
        super(BL16_MPI,self).__init__()
        loadUi(get_resource_path("BL16_MPI/ui/ui_BL16_window2.ui"),self)

        ############################ 将Tab页面加载到mainwondow中 ##############################
        self.calibration_instance = TimeFocusing(self)
        self.tabWidget.addTab(self.calibration_instance, "Time Focusing")

        self.reduction_instance = Reduction(self)
        self.tabWidget.addTab(self.reduction_instance, "Reduction")

        self.quickReduction_instance = QuickReduction(self)
        self.tabWidget.addTab(self.quickReduction_instance, "Quick Reduction")

        self.pdf_merge_instance = PDFMerge(self)
        self.tabWidget.addTab(self.pdf_merge_instance, "PDF Merge")

        self.pdf_hermite_instance = PDFHermite(self)
        self.tabWidget.addTab(self.pdf_hermite_instance, "PDF Hermite")


        # 获取 QTabBar
        tab_bar = self.tabWidget.tabBar()
        # 创建字体对象并设置字体
        font = QFont("Times New Roman", 14, QFont.Bold)
        # 直接为 QTabBar 设置字体，这将影响所有标签
        tab_bar.setFont(font)

        ########################### 设置菜单栏 ##############################
        # 获取 QAction “reduct_v_or_hold” 并连接到 pop_window
        self.offset_creation.triggered.connect(lambda: pop_window(bl16_offset, self))

    def closeEvent(self, event):
        super().closeEvent(event)