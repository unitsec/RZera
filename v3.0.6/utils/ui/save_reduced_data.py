from PyQt5.QtWidgets import QMessageBox
from rongzai.utils import get_all_from_detector,check_dir
from rongzai.dataSvc import write_ascii
from utils.browse import browse
from rongzai.dataSvc.diffraction_format import DiffractionFormat
import re,os
from utils.ui.BaseUI import CollapsibleWidget

class save_reduced_data(CollapsibleWidget):
    def __init__(self, parent):
        super(save_reduced_data, self).__init__("Save Reduced Data", "utils/ui/save_reduced_data.ui", parent)
        self.parent = parent

        self.browse_run = browse()
        self.pushButton.clicked.connect(lambda: self.browse_run.select_folder(self.lineEdit))

    def run(self):
        try:
            if self.toggle_button.isChecked():
                if self.lineEdit.text() == "":
                    return
                save_count = 0
                for data in self.parent.data_list:
                    if 'division' in data["record"].keys():
                        runno = self.get_runno_from_name(data['name'])
                        if "time_slice" in data.keys():
                            runno = f"{runno}_{data['time_slice']}"
                        # print(data['name'])
                        beamline = self.parent.config['base']['beamline_name']
                        runno = f"{beamline}_{runno}"
                        groupname, _ = get_all_from_detector(data['detector'],
                                                             self.parent.config['base']["group_info"],
                                                             self.parent.config['base']["bank_info"])
                        path = os.path.join(self.lineEdit.text(), runno)
                        check_dir(path)
                        if data['record']["normalization"]:
                            NorMethod = data['record']["normalization"]
                        else:
                            NorMethod = "noNorm"
                        # 保存 I-d 数据
                        fn = os.path.join(path, f"{runno}_{data['detector']}_{NorMethod}.txt")
                        x = data['detector_focused']["xvalue"].values[0]
                        y = data['detector_focused']["histogram"].values[0]
                        e = data['detector_focused']["error"].values[0]
                        write_ascii(fn, x, y, e)

                        # 保存record数据
                        fn = os.path.join(path, f"{runno}_{data['detector']}_record.txt")
                        with open(fn, 'w') as f:
                            for key, value in data['record'].items():
                                f.write(f"{key}: {value}\n")
                    

                        # 保存 refine 数据
                        difa = self.parent.config['base']["focus_point"][groupname]["DIFA"]
                        difb = self.parent.config['base']["focus_point"][groupname]["DIFB"]
                        difc = self.parent.config['base']["focus_point"][groupname]["DIFC"]
                        zero = self.parent.config['base']["focus_point"][groupname]["ZERO"]
                        fn = os.path.join(path, f"{runno}_{data['detector']}_{NorMethod}")
                        output = DiffractionFormat(data['detector_focused'], runno, data['detector'], self.parent.config['base']['beamline_name'],difa,difb,difc,zero)
                        output.writeGSAS(fn + ".gsa")
                        output.writeZR(fn + ".histogramIgor")
                        output.writeFP(fn + ".dat", self.parent.config['base']["multiply_factor_fullprof"], self.parent.config['base']["focus_point"][groupname]["2_theta"])
                        save_count += 1
                if save_count != 0:
                    QMessageBox.information(self, "Success from 'Save Reduced Data'", "The reduced data was saved successfully.")
        except Exception as e:
            print(f'Reason: {e}')
            import traceback
            traceback.print_exc()  # 打印异常的堆栈跟踪

    def get_runno_from_name(self, name):
        # 使用正则表达式匹配所有 RUN 后跟数字的字符串
        run_pattern = re.compile(r'RUN\d+')
        runnos = run_pattern.findall(name)

        # 检查是否有匹配的运行号
        if not runnos:
            return "unknown"

        # 将所有运行号用下划线连接成一个字符串
        combined_runno = '_'.join(runnos)
        return combined_runno

    def get_datatype_from_name(self, name):
        # 定义正则表达式模式
        pattern = re.compile(r'samBG|sam|vBG|v')

        # 搜索匹配
        match = pattern.search(name)

        if match:
            print(f"Matched: {match.group()}")  # 调试输出
            return match.group()
        else:
            print("Nothing matched")  # 调试输出
            return False

    def get_config(self):
        return {
            "is_use": self.toggle_button.isChecked(),
            "save_folder": self.lineEdit.text()
        }

    def set_config(self,config):
        """根据配置更新模块状态"""
        self.lineEdit.setText(config.get("save_folder", ""))
        self.toggle_button.setChecked(config.get("is_use", False))
