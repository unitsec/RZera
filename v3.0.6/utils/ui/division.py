from PyQt5.QtWidgets import QMessageBox
import copy
import traceback
from utils.browse import browse
from utils.ui.BaseUI import CollapsibleWidget
from rongzai.algSvc.instrument.diffraction import calculate_neutron_data

class division(CollapsibleWidget):
    def __init__(self, name, parent):
        super(division, self).__init__(name, "utils/ui/division.ui", parent)
        self.parent = parent

        self.browse_run = browse()
        self.samload_button.clicked.connect(lambda: self.browse_run.select_utils(self.samload_text,[data['name'] for data in self.parent.data_list]))
        self.vanload_button.clicked.connect(lambda: self.browse_run.select_utils(self.vanload_text, [data['name'] for data in self.parent.data_list]))

    def run(self):
        try:
            if self.toggle_button.isChecked():
                sam_list = self.samload_text.text().split('; ')
                van_list = self.vanload_text.text().split('; ')
                data_dict = {item['name']: item for item in self.parent.data_list}
                if self.check_load_text(sam_list,data_dict, "sam") is False:
                    return
                if self.check_load_text(van_list, data_dict, "V/VNi") is False:
                    return
                if sam_list != [''] and van_list != ['']:
                    for sam in sam_list:
                        for van in van_list:
                            if data_dict[van]["detector"] == data_dict[sam]["detector"]:
                                data_dict[sam]["detector_focused"] = calculate_neutron_data('divide', data_dict[sam]["detector_focused"],data_dict[van]["detector_focused"])
                                data_dict[sam]["record"]["division"] = data_dict[van]['name']
                                if "subtraction_self" in data_dict[van]['record']:
                                    data_dict[sam]["record"]["subtraction_v"] = data_dict[van]['record']["subtraction_self"]
                                    data_dict[sam]["record"]["subtraction_scale_v"] = data_dict[van]['record']["subtraction_scale"]
                                if "correction_info" in data_dict[van].keys():
                                    data_dict[sam]["v_correction"] = data_dict[van]["correction_info"]
        except Exception as e:
            print(f'Reason: {e}')
            traceback.print_exc()  # 打印异常的堆栈跟踪

    def check_load_text(self,name_list,data_dict, data_class):
        for name in name_list:
            if name not in data_dict:
                QMessageBox().warning(self, "warning in Division",
                                f"There exists {data_class} data not loaded, please Check ")
                return False
        return True

    def plot_data(self):
        if self.toggle_button.isChecked():
            plot_data = []
            sam_list = self.samload_text.text().split('; ')
            for data in self.parent.data_list:
                if data['name'] in sam_list:
                    plot_data.append({"name": data['name'],
                                      "data": [copy.deepcopy(data["detector_focused"]["xvalue"].values[0]),
                                               copy.deepcopy(data["detector_focused"]["histogram"].values[0]),
                                               copy.deepcopy(data["detector_focused"]["error"].values[0])],
                                      "x_label": "d (Å)",
                                      "y_label": "Intensity (a.u.)"
                                      })
            return plot_data
        else:
            return []

    def get_config(self):
        return {
            "is_plot": self.plot.isChecked(),
            "samload_text": self.samload_text.text(),
            "vanload_text": self.vanload_text.text(),
            "is_use": self.toggle_button.isChecked()
        }

    def set_config(self,config):
        """根据配置更新模块状态"""
        self.plot.setChecked(config.get("is_plot", False))
        self.samload_text.setText(config.get("samload_text", ""))
        self.vanload_text.setText(config.get("vanload_text", ""))
        self.toggle_button.setChecked(config.get("is_use", False))

