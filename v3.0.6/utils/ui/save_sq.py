from PyQt5.QtWidgets import QMessageBox
from rongzai.utils import check_dir
from rongzai.dataSvc import write_rmc
from utils.browse import browse
from utils.ui.BaseUI import CollapsibleWidget
import os
import traceback

class save_sq(CollapsibleWidget):
    def __init__(self, parent):
        super(save_sq, self).__init__("Save S(Q)", "utils/ui/save_sq.ui", parent)
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
                    if "sq_data" in data:
                        path = self.save_text.text()
                        check_dir(path)
                        fn = os.path.join(path, f"sq_{data['name'].replace(':', '')}.txt")
                        x = data["sq_data"][0]
                        y = data["sq_data"][1]
                        e = data["sq_data"][2]
                        write_rmc(fn, x, y, e)
                        save_count += 1
                if save_count != 0:
                    QMessageBox.information(self, "Success from 'Save S(Q)'", f"The S(Q) data was saved successfully.")
        except Exception as e:
            print(f'Reason: {e}')
            traceback.print_exc()  # 打印异常的堆栈跟踪

    def get_config(self):
        return {
            "is_use": self.toggle_button.isChecked(),
            "save_folder": self.save_text.text()
        }

    def set_config(self,config):
        """根据配置更新模块状态"""
        self.toggle_button.setChecked(config.get("is_use", False))
        self.save_text.setText(config.get("save_folder", ""))