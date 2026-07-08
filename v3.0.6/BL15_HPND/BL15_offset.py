from PyQt5.QtWidgets import QDialog
from BL16_MPI.ui.ui_BL16_offset import Ui_Form   # 导入弹出窗口的 UI 类
from BL16_MPI.online.workers.browse_file import browse_file
import BL16_MPI.workers.offset_thread

# 这是您的弹出窗口类

class bl16_offset(QDialog, Ui_Form):
    def __init__(self, parent=None):
        super(bl16_offset, self).__init__(parent)
        self.setupUi(self)  # 初始化 UI

        self.run_filePaths = []
        self.browser = browse_file()
        self.select_run.clicked.connect(lambda:self.browser.select_nxsfile(self.run_filePaths, self.select_run_text))
        self.select_pid.clicked.connect(lambda: self.browser.select_folder(self.select_pid_text))
        self.save_path.clicked.connect(lambda: self.browser.select_folder(self.save_path_text))
        self.select_Si.toggled.connect(self.select_d_peaks)
        self.select_other.toggled.connect(self.select_d_peaks)
        self.offset_thread = BL16_MPI.workers.offset_thread.start_offset_thread()
        self.run_button.clicked.connect(lambda: self.offset_thread.start_offset(self, self.run_filePaths, self.run_button))
        self.check_thread = BL16_MPI.workers.offset_thread.start_check_process(self, self.run_filePaths, self.check_button)
        self.check_button.clicked.connect(lambda: self.check_thread.start_check())

    def select_d_peaks(self, checked):
        # 获取发出信号的 QRadioButton
        radio_button = self.sender()
        if checked:
            if radio_button.text() == 'Si':
                self.peaks_info_line.setDisabled(True)
                self.peaks_info_line.setText('3.14292303,1.92463943,1.64133802,1.36092559,1.24887097,1.11119109,1.04764101,0.96231972,0.92015364,0.86072492')
                self.smooth_points_bank2.setText('40')
                # self.smooth_order_bank2.setDisabled(True)
                self.smooth_points_bank3.setText('51')
                self.smooth_points_bank4.setText('30')
                self.smooth_points_bank5.setText('51')
                self.smooth_points_bank6.setText('51')
                self.smooth_points_bank7.setText('40')
                self.smooth_order_bank2.setText('6')
                self.smooth_order_bank3.setText('8')
                self.smooth_order_bank4.setText('8')
                self.smooth_order_bank5.setText('8')
                self.smooth_order_bank6.setText('8')
                self.smooth_order_bank7.setText('8')
                self.peakfind_bank2.setText('[0.5,0.14][0.2,0.05][0.4,0.06][0.4,0.06][0.5,0.05][0.2,0.05]')
                self.peakfind_bank3.setText('[0.5,0.14][0.5, 0.08][0.2,0.03][0.4,0.06][0.5,0.05][0.2,0.05]')
                self.peakfind_bank4.setText('[0.5,0.14][0.5,0.08][0.2,0.06][0.4,0.06][0.5,0.05][0.2,0.05][0.3,0.1][0.1,0.02][0.2,0.02][0.1,0.02]')
                self.peakfind_bank5.setText('[0.5,0.5][0.5,0.03][0.4,0.06][0.5,0.05][0.5,0.05][0.5,0.05]')
                self.peakfind_bank6.setText('[0.5,0.5][0.5,0.03][0.4,0.06][0.5,0.05][0.5,0.05][0.5,0.05]')
                self.peakfind_bank7.setText('[0.5,0.5][0.5,0.03][0.4,0.06][0.5,0.05][0.5,0.05][0.5,0.05]')
                self.bank2_order.setCurrentText('quadratic')
                self.bank3_order.setCurrentText('quadratic')
                self.bank4_order.setCurrentText('quadratic')
                self.bank5_order.setCurrentText('linear')
                self.bank6_order.setCurrentText('linear')
                self.bank7_order.setCurrentText('linear')
            elif radio_button.text() == 'other':
                self.peaks_info_line.setDisabled(False)