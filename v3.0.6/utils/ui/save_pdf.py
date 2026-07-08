from PyQt5.QtWidgets import QMessageBox
from rongzai.utils import check_dir
from rongzai.dataSvc import write_rmc
from utils.browse import browse
from utils.ui.BaseUI import CollapsibleWidget
import os
import numpy as np

class save_pdf(CollapsibleWidget):
    def __init__(self, parent):
        super(save_pdf, self).__init__("Save PDF", "utils/ui/save_pdf.ui", parent)
        self.parent = parent

        self.browse_run = browse()
        self.save_button.clicked.connect(lambda: self.browse_run.select_folder(self.save_text))

    def run(self):
        try:
            if self.toggle_button.isChecked():
                if self.save_text.text() == "":
                    return
                save_count = 0
                for data in self.parent.data_list:
                    if "pdf_data" in data:
                        path = self.save_text.text()
                        check_dir(path)
                        fn = os.path.join(path, f"{data['pdf_type']}_{data['name'].replace(':', '')}.txt")
                        x = data["pdf_data"][0]
                        y = data["pdf_data"][1]
                        e = np.zeros(np.shape(y))
                        write_rmc(fn, x, y, e)
                        save_count += 1
                if save_count != 0:
                    QMessageBox.information(self, "Success from 'Save PDF'", "The PDF data was saved successfully.")
        except Exception as e:
            print(f'Reason: {e}')
            import traceback
            traceback.print_exc()  # 打印异常的堆栈跟踪

    def get_config(self):
        return {
            "save_folder": self.save_text.text(),
            "is_use": self.toggle_button.isChecked()
        }

    def set_config(self,config):
        """根据配置更新模块状态"""
        self.save_text.setText(config.get("save_folder", ""))
        self.toggle_button.setChecked(config.get("is_use", False))