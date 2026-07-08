from PyQt5.QtWidgets import QMessageBox
from rongzai.dataSvc import save_dataset
from rongzai.utils import check_dir
from utils.browse import browse
from utils.ui.BaseUI import CollapsibleWidget
import json
import traceback

class save_focused_data(CollapsibleWidget):
    def __init__(self, name, parent):
        super(save_focused_data, self).__init__(name, "utils/ui/save_focused_data.ui", parent)
        self.dataType = "unknown"
        self.parent = parent

        self.browse_run = browse()
        self.pushButton.clicked.connect(lambda: self.browse_run.select_folder(self.lineEdit))


    def run(self):
        try:
            if self.toggle_button.isChecked():
                if self.lineEdit.text() == "":
                    return
                if not self.get_datatype():
                    return
                save_count = 0
                for data in self.parent.data_list:
                    if 'detector_focused' in data.keys():
                        data['detector_focused'].attrs["name"] = data['detector']
                        data['detector_focused'].attrs["runno"] = data['runno']
                        try:
                            data['detector_focused']['monitor_counts'] = data['monitor_counts']
                        except:
                            pass

                        # 将字典转换为JSON字符串后，存储为属性
                        record_str = json.dumps(data["record"])
                        data["detector_focused"].attrs["record"] = record_str

                        if "time_slice" in data.keys():
                            data["detector_focused"].attrs['time_slice'] = data["time_slice"]
                        if "start_time" in data.keys():
                            data["detector_focused"].attrs['start_time'] = data["start_time"]
                        if "end_time" in data.keys():
                            data["detector_focused"].attrs['end_time'] = data["end_time"]
                            
                        try:
                            check_dir(self.lineEdit.text())
                        except:
                            QMessageBox.warning(self, "warning in Save Data", "The save path is not correct, please check!")
                            return
                        fn = f"{self.lineEdit.text()}/{self.dataType}_{data['name'].replace(':', '')}_{data['detector']}.nc"
                        save_dataset(data['detector_focused'], fn)
                        save_count += 1
                if save_count != 0:
                    QMessageBox.information(self, "Success from 'Save Focused Data'", f"The focused data was saved successfully.")
        except Exception as e:
            print(f'Reason: {e}')
            traceback.print_exc()  # 打印异常的堆栈跟踪

    def get_datatype(self):
        if self.sam_radio.isChecked():
            self.dataType = 'sam'
            return True
        elif self.v_radio.isChecked():
            self.dataType = 'v'
            return True
        elif self.vCell_radio.isChecked():
            self.dataType = 'vCell'
            return True
        elif self.samCell_radio.isChecked():
            self.dataType = 'samCell'
            return True
        elif self.bkg_radio.isChecked():
            self.dataType = 'bkg'
            return True
        else:
            QMessageBox.warning(self, "warning", "Please select one data type!")
            return False

    def get_config(self):
        return {
            "save_folder": self.lineEdit.text(),
            "sam_radio": self.sam_radio.isChecked(),
            "v_radio": self.v_radio.isChecked(),
            "samCell_radio": self.samCell_radio.isChecked(),
            "vCell_radio": self.vCell_radio.isChecked(),
            "bkg_radio": self.bkg_radio.isChecked(),
            "is_use": self.toggle_button.isChecked()
        }

    def set_config(self,config):
        """根据配置更新模块状态"""
        self.lineEdit.setText(config.get("save_folder", ""))
        self.sam_radio.setChecked(config.get("sam_radio", False))
        self.v_radio.setChecked(config.get("v_radio", False))
        self.samCell_radio.setChecked(config.get("samCell_radio", False))
        self.vCell_radio.setChecked(config.get("vCell_radio", False))
        self.bkg_radio.setChecked(config.get("bkg_radio", False))
        self.toggle_button.setChecked(config.get("is_use", False))