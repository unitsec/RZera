from PyQt5.QtWidgets import QMainWindow
from PyQt5.uic import loadUi
from PyQt5.QtGui import QFont
from BL09_TREND.BL09_TimeFocusing2 import TimeFocusing
from BL09_TREND.BL09_Reduction2 import Reduction
from BL09_TREND.BL09_QuickReduction2 import QuickReduction
# from BL09_TREND.BL09_PDF_Hetmite2 import PDFHermite
from BL09_TREND.BL09_PDF_Merge2 import PDFMerge
from utils.helper import get_resource_path


class BL09_TREND(QMainWindow):
    def __init__(self):
        super(BL09_TREND,self).__init__()
        loadUi(get_resource_path("BL09_TREND/ui/ui_BL09_window2.ui"),self)

        ############################ 将Tab页面加载到mainwondow中 ##############################
        self.calibration_instance = TimeFocusing(self)
        self.tabWidget.addTab(self.calibration_instance, "Time Focusing")

        self.reduction_instance = Reduction(self)
        self.tabWidget.addTab(self.reduction_instance, "Reduction")

        self.quick_reduction_instance = QuickReduction(self)
        self.tabWidget.addTab(self.quick_reduction_instance, "Quick Reduction")

        # self.pdf_hermite_instance = PDFHermite(self)
        # self.tabWidget.addTab(self.pdf_hermite_instance, "PDF Hermite")

        self.pdf_merge_instance = PDFMerge(self)
        self.tabWidget.addTab(self.pdf_merge_instance, "PDF Merge")

        # 获取 QTabBar
        tab_bar = self.tabWidget.tabBar()
        # 创建字体对象并设置字体
        font = QFont("Times New Roman", 14, QFont.Bold)
        # 直接为 QTabBar 设置字体，这将影响所有标签
        tab_bar.setFont(font)

        ########################### 设置菜单栏 ##############################
        # 获取 QAction “reduct_v_or_hold” 并连接到 pop_window
        # self.offset_creation.triggered.connect(lambda: pop_window(BL09_offset, self))
        # self.how_to_use.triggered.connect(open_pdf)

    def closeEvent(self, event):
        super().closeEvent(event)