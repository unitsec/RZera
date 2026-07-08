from PyQt5.uic import loadUi
import traceback
from utils.ui.BaseUI import  BaseDataProcessor
from PyQt5.QtGui import QDoubleValidator
# from rongzai.algSvc.instrument.diffraction import correct_abs_ms,calculate_material_property
# from rongzai.algSvc.neutron.unit_convert_nd import UnitConvertNeutronData


class carpenterCorrection(BaseDataProcessor):
    def __init__(self, parent):
        super(carpenterCorrection, self).__init__(parent)
        loadUi("utils/ui/carpenterCorrection.ui", self)
        self.parent = parent

        self._setup_validators() # 设置输入验证器

        # 初始化correction开关
        self.is_correction.stateChanged.connect(self.toggle_style)
        self.is_correction.setChecked(False)

        # 连接滑块信号
        self.scale.valueChanged.connect(self.update_scale_label)
        self.scale.valueChanged.connect(self.update_num_density_label)
        self.scale.valueChanged.connect(self._notify_parent)

        # 单位转换工具
        self.unit_cvt = UnitConvertNeutronData()

    def toggle_style(self):
        if self.is_correction.isChecked():
            # Set active style
            self.setStyleSheet(f"QFrame#carpenterCorrection {{ background-color: lightblue; border: 1px solid black; }}")
        else:
            # Set inactive style
            self.setStyleSheet(f"QFrame#carpenterCorrection {{ background-color: lightgrey; }}")

    def _setup_validators(self):
        """设置输入验证器"""
        validator = QDoubleValidator(0.0, float('inf'), 8, self) #创建一个浮点数验证器，限制输入范围在 [0.0, +∞)，且最多允许 8 位小数
        validator.setNotation(QDoubleValidator.StandardNotation) #强制使用标准十进制表示法（避免科学计数法）

        self.mass.setValidator(validator)
        self.mass.setText("1.0")
        self.sam_height.setValidator(validator)
        self.sam_height.setText("3.0")
        self.radius_text.setValidator(validator)
        self.radius_text.setText("0.5")
        self.beam_height.setValidator(validator)
        self.beam_height.setText("3.0")
        self.num_density_text.setValidator(validator)
        self.num_density_text.setText("0.01")
        self.num_density_check.stateChanged.connect(lambda state: self.num_density_text.setEnabled(state == 2))
        self.num_density_check.setChecked(False)

        self.mass.textChanged.connect(self.update_num_density_label)
        self.sam_height.textChanged.connect(self.update_num_density_label)
        self.radius_text.textChanged.connect(self.update_num_density_label)
        self.beam_height.textChanged.connect(self.update_num_density_label)

    def update_scale_label(self):
        """更新缩放比例标签"""
        value = self.scale.value()
        self.scale_value.setText(f"{value / 100:.2f}")

    def update_num_density_label(self):
        try:
            info = self._get_correction_info()
            cal_info = calculate_material_property(info)
            cal_num_density = cal_info["density_num"]
            value = self.scale.value()
            self.num_density_label.setText(f"Calculated Num Density:{cal_num_density*value/100:.6f} Å⁻³")
        except:
            self.num_density_label.setText(f"Calculated Num Density:0.000000 Å⁻³")

    def _get_correction_info(self):
        """获取校正参数"""
        return {
            "sample_name": self.sample_name.text(),
            "mass": float(self.mass.text()),
            "volume": {
                "type": "cylinder",
                "height": float(self.sam_height.text()),
                "radius": float(self.radius_text.text()),
                "beam_height": float(self.beam_height.text()),
                "thickness": 0},
            "scale": self.scale.value() / 100
        }

    def _notify_parent(self):
        """通知父窗口数据已更新"""
        if hasattr(self.parent, 'module_value_changed'):
            self.parent.module_value_changed(self)

    def run(self):
        if not self.is_correction.isChecked():
            return
        try:
            correction_info = self._get_correction_info()
            if self.num_density_check.isChecked():
                correction_info["density_num"] = float(self.num_density_text.text())
            split_data = self.split_by_name(self.parent.data_list)
            for items in split_data.values():
                modules_list = self.get_module_list(items,self.parent.config['base'])
                corrected_data_dict = self.get_corrected_data(modules_list,items,correction_info)
                self.update_data(items, corrected_data_dict)
            self.parent.data_list = self.merge_split_data(split_data)
        except Exception as e:
            print(f"Error in run(): {e}")
            traceback.print_exc()

    def get_corrected_data(self, modules_list, items, correction_info):
        corrected_data_dict = {}
        modules_exclude_set = set()
        for module in modules_list:
            for item in items:
                for key,value in item['modules'].items():
                    if key == module and key not in modules_exclude_set:
                        value_wave = self.unit_cvt.run(value, "wavelength")
                        value_wave_corrected = correct_abs_ms(value_wave, correction_info)
                        value_corrected = self.unit_cvt.run(value_wave_corrected, "tof")
                        modules_exclude_set.add(module)
                        corrected_data_dict[module] = value_corrected
                item["correction_info"] = correction_info
        return corrected_data_dict


    def get_config(self):
        """获取当前配置"""
        return {
            "is_correction": self.is_correction.isChecked(),
            "sample_name": self.sample_name.text(),
            "mass": self.mass.text(),
            "radius": self.radius_text.text(),
            "sam_height": self.sam_height.text(),
            "beam_height": self.beam_height.text(),
            "scale": self.scale.value(),
        }

    def set_config(self, config):
        """设置配置"""
        self.is_correction.setChecked(config.get("is_correction", False))
        self.sample_name.setText(config.get("sample_name", ""))
        self.mass.setText(config.get("mass", "1.0"))
        self.radius_text.setText(config.get("radius", "0.5"))
        self.sam_height.setText(config.get("sam_height", "3.0"))
        self.beam_height.setText(config.get("beam_height", "3.0"))
        self.scale.setValue(config.get("scale", 100))

