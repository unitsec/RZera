from PyQt5.uic import loadUi
from PyQt5 import QtWidgets
from utils.helper import get_resource_path
import json,traceback

class load_beamline_config(QtWidgets.QWidget):
    def __init__(self, parent):
        super(load_beamline_config, self).__init__(parent)
        self.parent = parent  # 保存传递的 Reduction 实例
        loadUi(get_resource_path("utils/ui/load_beamline_config.ui"), self)
        self.setStyleSheet(f"QFrame#load_beamline_config {{ background-color: #eaf4ff; border: 1px solid #ccc;border-radius: 5px;  }}")
        self.label.setText("未导入")
        self.button.clicked.connect(self.load_config)

    def load_config(self):
        # 打开文件选择对话框
        options = QtWidgets.QFileDialog.Options()
        config_file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Select Config File", "", "JSON Files (*.json)", options=options)
        try:
            if config_file_path:
                # 读取并加载配置文件
                with open(config_file_path, 'r', encoding='utf-8') as json_file:
                    base_configure = json.load(json_file)
                self.parent.config['base'] = base_configure
                self.label.setText(f"Instrument configure file has been loaded. Beamline name {self.parent.config['base']['beamline']}:{self.parent.config['base']['beamline_name']}")

        except Exception as e:
            QtWidgets.QMessageBox.information(self, 'Error',
                                              'uncorrected json file')
            print(f'Failed to plot. Reason: {e}')
            traceback.print_exc()  # 打印异常的堆栈跟踪

    def auto_config(self,config_path):
        with open(config_path, 'r', encoding='utf-8') as json_file:
            base_configure = json.load(json_file)
        self.parent.config['base'] = base_configure
        self.label.setText(
            f"Instrument configure file has been loaded. Beamline name {self.parent.config['base']['beamline']}:{self.parent.config['base']['beamline_name']}")
        # self.button.setEnabled(False)
        self.button.setText('Reload')