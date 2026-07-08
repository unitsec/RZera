from PyQt5.QtWidgets import QMainWindow
from PyQt5.uic import loadUi
from PyQt5.QtGui import QFont
from BL15_HPND.BL15_TimeFocusing2 import TimeFocusing
from BL15_HPND.BL15_Reduction2 import Reduction
from BL15_HPND.BL15_QuickReduction2 import QuickReduction
from utils.helper import get_resource_path


class BL15_HPND(QMainWindow):
    def __init__(self):
        super(BL15_HPND,self).__init__()
        loadUi(get_resource_path("BL15_HPND/ui/ui_BL15_window2.ui"),self)

        ############################ 将Tab页面加载到mainwondow中 ##############################
        self.calibration_instance = TimeFocusing(self)
        self.tabWidget.addTab(self.calibration_instance, "Time Focusing")

        self.reduction_instance = Reduction(self)
        self.tabWidget.addTab(self.reduction_instance, "Reduction")

        self.quickReduction_instance = QuickReduction(self)
        self.tabWidget.addTab(self.quickReduction_instance, "Quick Reduction")

        # 获取 QTabBar
        tab_bar = self.tabWidget.tabBar()
        # 创建字体对象并设置字体
        font = QFont("Times New Roman", 14, QFont.Bold)
        # 直接为 QTabBar 设置字体，这将影响所有标签
        tab_bar.setFont(font)

        ########################### 设置菜单栏 ##############################
        # 获取 QAction “reduct_v_or_hold” 并连接到 pop_window
        # self.offset_creation.triggered.connect(lambda: pop_window(bl16_offset, self))

    def closeEvent(self, event):
        super().closeEvent(event)