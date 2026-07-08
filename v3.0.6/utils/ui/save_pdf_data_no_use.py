from rongzai.utils import check_dir
from rongzai.dataSvc import write_ascii
from utils.browse import browse
from utils.ui.BaseUI import CollapsibleWidget
from PyQt5.QtWidgets import QMessageBox
import os
import numpy as np
import copy

class save_pdf_data(CollapsibleWidget):
    def __init__(self, parent):
        super(save_pdf_data, self).__init__("Save PDF", "utils/ui/save_pdf_data.ui", parent)
        self.parent = parent

        self.browse_run = browse()
        self.save_button.clicked.connect(lambda: self.browse_run.select_folder(self.save_text))

    def get_correction_info(self,data):
        # 拿第一个字典作为基准
        try:
            first_corr = data["correction_info"][0]
        except:
            QMessageBox.warning(self, "warning",
                                "The correction info is not exist, so you only can get the G(r), can't get the g(r) and RDF.")
            return {}
        # 检查所有字典是否都与第一个字典相同
        judge = all(corr == first_corr for corr in data["correction_info"])
        if not judge:
            QMessageBox.warning(self, "warning", "The correction info from the data used to fitting are different, the first would be selected as the correct one.")
        return first_corr


    def run(self):
        try:
            if self.toggle_button.isChecked():
                for data in self.parent.data_list:
                    if data['name'] == "PDF":
                        path = self.save_text.text()
                        print(path)
                        if path != "":
                            check_dir(path)
                            data_mode = self.data_mode.currentText()
                            dr = data['pdf_data'][1]
                            correction_info = self.get_correction_info(data)
                            if correction_info != {}:
                                rho0 = correction_info["density_num"] * correction_info["scale"]
                            else:
                                rho0 = None
                            if data_mode == "G(r)":
                                # 保存 I-d 数据
                                fn = os.path.join(path, f"{data_mode}_{data['detector']}.txt")
                                x = data["pdf_data"][0]
                                y = dr
                                e = np.zeros(np.shape(y))
                                write_ascii(fn, x, y, e)
                            elif data_mode == "g(r)":
                                if rho0 is not None:
                                    # 保存 I-d 数据
                                    fn = os.path.join(path, f"{data_mode}_{data['detector']}.txt")
                                    x = data["pdf_data"][0]
                                    y = dr / (4 * np.pi * x * rho0) + 1
                                    e = np.zeros(np.shape(y))
                                    write_ascii(fn, x, y, e)
                            elif data_mode == "RDF":
                                if rho0 is not None:
                                    # 保存 I-d 数据
                                    fn = os.path.join(path, f"{data_mode}_{data['detector']}.txt")
                                    x = data["pdf_data"][0]
                                    y = x * dr + 4 * np.pi * rho0 * x ** 2
                                    e = np.zeros(np.shape(y))
                                    write_ascii(fn, x, y, e)
        except Exception as e:
            print(f'Reason: {e}')
            import traceback
            traceback.print_exc()  # 打印异常的堆栈跟踪

    def plot_data(self):
        if self.toggle_button.isChecked():
            plot_data = []
            data_mode = self.data_mode.currentText()
            for data in self.parent.data_list:
                if data['name'] == "PDF":
                    x = data["pdf_data"][0]
                    dr = data['pdf_data'][1]
                    correction_info = self.get_correction_info(data)
                    if correction_info != {}:
                        rho0 = correction_info["density_num"] * correction_info["scale"]
                    else:
                        rho0 = None
                    if data_mode == "G(r)":
                        plot_data.append({"name":"G(r)",
                                          "data":copy.deepcopy(data['pdf_data']),
                                          "x_label": 'r (Å)',
                                          "y_label": "Intensity (a.u.)"
                                          })
                    elif data_mode == "g(r)":
                        if rho0 is not None:
                            plot_data.append({"name":"g(r)", "data":copy.deepcopy(dr / (4 * np.pi * x * rho0) + 1),
                                              "x_label": 'r (Å)',
                                              "y_label": "Intensity (a.u.)"
                                              })
                    elif data_mode == "RDF":
                        if rho0 is not None:
                            plot_data.append({"name":"RDF", "data":copy.deepcopy(x * dr + 4 * np.pi * rho0 * x ** 2),
                                              "x_label": 'r (Å)',
                                              "y_label": "Intensity (a.u.)"
                                              })
            return  plot_data
        else:
            return []

    def get_config(self):
        return {
            "is_use": self.toggle_button.isChecked(),
            "save_folder": self.save_text.text(),
            "plot": self.plot.isChecked()
        }

    def set_config(self,config):
        """根据配置更新模块状态"""
        self.toggle_button.setChecked(config.get("is_use", False))
        self.save_text.setText(config.get("save_folder", ""))
        self.plot.setChecked(config.get("plot", False))