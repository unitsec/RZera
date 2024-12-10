from PyQt5.QtWidgets import QDialog,QFileDialog,QTextEdit
from PyQt5.QtCore import Qt
from BL09_TREND.ui.ui_BL09_offset import Ui_Form   # 导入弹出窗口的 UI 类
from BL09_TREND.workers.browse_file import browse_file
from BL09_TREND.workers.ui_mapping import save_offset_config,load_offset_config
import BL09_TREND.workers.offset_thread
import traceback
from utils.NonZeroIntValidator import NonZeroIntValidator

# 这是您的弹出窗口类

class BL09_offset(QDialog, Ui_Form):
    def __init__(self, parent=None):
        super(BL09_offset, self).__init__(parent)
        self.setupUi(self)  # 初始化 UI
        # 设置窗口标志，确保显示最小化、最大化和关闭按钮
        self.setWindowFlags(self.windowFlags() | Qt.WindowMinMaxButtonsHint | Qt.WindowCloseButtonHint)
        # 限制group参数只能输入正整数
        self.nozerointvalidator = NonZeroIntValidator(1, 2147483647)  # 实例化自定义的NonZeroIntValidator
        self.group_along_tof.setValidator(self.nozerointvalidator)  # 将NonZeroIntValidator设置到 QLineEdit 控件上(只能输入正整数)
        self.group_cross_tof.setValidator(self.nozerointvalidator)
        self.group_along_d.setValidator(self.nozerointvalidator)
        self.group_cross_d.setValidator(self.nozerointvalidator)

        self.run_filePaths = []
        self.browser = browse_file()
        self.select_run.clicked.connect(lambda:self.browser.select_nxsfile(self.run_filePaths, self.select_run_text))
        self.select_pid.clicked.connect(lambda: self.browser.select_folder(self.select_pid_text))
        self.select_path.clicked.connect(lambda: self.browser.select_folder(self.select_path_text))
        self.offset_thread = BL09_TREND.workers.offset_thread.start_offset_thread()
        self.run_button.clicked.connect(lambda: self.offset_thread.start_offset(self, self.run_filePaths, self.run_button))
        self.paracheck_thread = BL09_TREND.workers.offset_thread.start_paracheck_process(self, self.paracheck_button)
        self.paracheck_button.clicked.connect(lambda: self.paracheck_thread.start_check(self.run_filePaths,))
        self.resultcheck_thread = BL09_TREND.workers.offset_thread.start_resultcheck_process(self, self.resultcheck_button)
        self.resultcheck_button.clicked.connect(lambda: self.resultcheck_thread.start_check(self.run_filePaths))

        ######################################### 配置 save_config  #######################################################
        self.save_config.clicked.connect(lambda: save_offset_config(self,self.run_filePaths))

        ######################################### 配置 load_config  #######################################################
        self.load_config.clicked.connect(lambda: load_offset_config(self))  # 从配置文件读取配置


    def closeEvent(self, event):
        try:
            if self.offset_thread.offset_thread != None and self.offset_thread.offset_thread.isRunning():
                # 在窗口关闭时停止线程
                self.offset_thread.offset_thread.stop()
                self.offset_thread.offset_thread.wait()  # 等待线程真正结束
        except Exception as e:
            print(f"An error occurred: {e}")
            traceback.print_exc()  # 打印异常的堆栈跟踪
        super().closeEvent(event)