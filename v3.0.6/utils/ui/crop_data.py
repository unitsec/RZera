from PyQt5.uic import loadUi
from PyQt5 import QtGui
from utils.ui.BaseUI import  BaseDataProcessor
from rongzai.algSvc.neutron import crop_neutron_data
# from rongzai.algSvc.neutron.unit_convert_nd import UnitConvertNeutronData
import traceback

class crop_data(BaseDataProcessor):
    def __init__(self, parent):
        super(crop_data, self).__init__(parent)
        loadUi("utils/ui/crop_data.ui", self)
        self.parent = parent

        # 初始化crop开关
        self.use.stateChanged.connect(self.toggle_style)
        self.use.setChecked(False)

        self.unit_cvt = UnitConvertNeutronData()

        doubleValidator = QtGui.QDoubleValidator()
        self.wave_min.setValidator(doubleValidator)  # 将 doubleValidator 设置到 QLineEdit 控件上 (只能输入浮点数)
        self.wave_max.setValidator(doubleValidator)

        self.set_default_crop()

    def run(self):
        try:
            if self.use.isChecked():
                split_data = self.split_by_name(self.parent.data_list)
                for items in split_data.values():
                    modules_list = self.get_module_list(items,self.parent.config['base'])
                    croped_data_dict = self.get_cropped_data(modules_list,items)
                    self.update_data(items, croped_data_dict)
                self.parent.data_list = self.merge_split_data(split_data)
        except Exception as e:
            print(f'Reason: {e}')
            traceback.print_exc()  # 打印异常的堆栈跟踪

    def get_cropped_data(self, modules_list, items):
        cropped_data_dict = {}
        modules_exclude_set = set()
        for module in modules_list:
            for item in items:
                for key, value in item['modules'].items():
                    if key == module and key not in modules_exclude_set:
                        value_wave = self.unit_cvt.run(value, "wavelength")
                        value_wave_cropped = crop_neutron_data(value_wave, float(self.wave_min.text()), float(self.wave_max.text()))
                        value_cropped = self.unit_cvt.run(value_wave_cropped, "tof")
                        modules_exclude_set.add(module)
                        cropped_data_dict[module] = value_cropped
        return cropped_data_dict

    def toggle_style(self):
        if self.use.isChecked():
            # Set active style
            self.setStyleSheet(f"QFrame#crop_data {{ background-color: lightblue; border: 1px solid black; }}")
        else:
            # Set inactive style
            self.setStyleSheet(f"QFrame#crop_data {{ background-color: lightgrey; }}")

    def set_default_crop(self):
        try:
            wave_max = self.parent.config["base"]["wave_max"]
            wave_min = self.parent.config["base"]["wave_min"]
            self.wave_min.setText(str(wave_min))
            self.wave_max.setText(str(wave_max))
        except Exception as e:
            print(f'Reason: {e}')
            traceback.print_exc()  # 打印异常的堆栈跟踪

    def get_config(self):
        return {
            "use": self.use.isChecked(),
            "wave_min": self.wave_min.text(),
            "wave_max": self.wave_max.text()
        }

    def set_config(self,config):
        """根据配置更新模块状态"""
        self.use.setChecked(config.get("use", False))  # 加载 QCheckBox 的选中状态
        self.wave_min.setText(config.get("wave_min", ""))
        self.wave_max.setText(config.get("wave_max", ""))