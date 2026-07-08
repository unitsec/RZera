import traceback
import copy
from PyQt5.QtWidgets import  QMessageBox
from utils.ui.BaseUI import CollapsibleWidget

class normalization(CollapsibleWidget):
    def __init__(self, parent):
        super(normalization, self).__init__("Normalization", "utils/ui/normalization.ui", parent)
        self.parent = parent

    def run(self):
        try:
            if self.toggle_button.isChecked():
                if self.proton_nor.isChecked():
                    for data in self.parent.data_list:
                        proton_charge = data['detector_focused']["proton_charge"].values
                        proton_charge /= self.parent.config['base']['pc_factor']
                        data['detector_focused']["histogram"].values /= proton_charge
                        data['detector_focused']["error"].values /= proton_charge
                        data["record"]["normalization"] = "protonCharge"
                elif self.monitor_nor.isChecked():
                    for data in self.parent.data_list:
                        monitor_counts = data['detector_focused']["monitor_counts"].values
                        data['detector_focused']["histogram"].values /= monitor_counts
                        data['detector_focused']["error"].values /= monitor_counts
                        data["record"]["normalization"] = "monitorCounts"
                else:
                    QMessageBox.warning(self, "Warning", "No Normalization option is selected")
        except Exception as e:
            print(f'Reason: {e}')
            traceback.print_exc()  # 打印异常的堆栈跟踪

    def plot_data(self):
        if self.toggle_button.isChecked():
            plot_data = []
            for data in self.parent.data_list:
                if "detector_focused" in data and "interpolation" not in data["record"]: # 只绘制未插值的数据
                    plot_data.append({"name": f"{data['name']}",
                                      "data": [copy.deepcopy(data["detector_focused"]["xvalue"].values[0]),
                                               copy.deepcopy(data["detector_focused"]["histogram"].values[0]),
                                               copy.deepcopy(data["detector_focused"]["error"].values[0])],
                                      "x_label": "d (Å)",
                                      "y_label": "Intensity (a.u.)"})
            return plot_data
        else:
            return []

    def get_config(self):
        return {
            "pc_check": self.proton_nor.isChecked(),
            "monitor_check": self.monitor_nor.isChecked(),
            "is_plot": self.plot.isChecked(),
            "is_use": self.toggle_button.isChecked(),
        }

    def set_config(self,config):
        """根据配置更新模块状态"""
        self.proton_nor.setChecked(config.get("pc_check", True))  # 加载 QCheckBox 的选中状态
        self.monitor_nor.setChecked(config.get("monitor_check", False))
        self.plot.setChecked(config.get("is_plot", False))
        self.toggle_button.setChecked(config.get("is_use", False))

