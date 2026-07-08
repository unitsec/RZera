from PyQt5.uic import loadUi
from PyQt5 import QtWidgets
from rongzai.utils import get_all_from_detector,generate_x
from rongzai.algSvc.neutron import mask_neutron_data,focus_neutron_data,rebin_neutron_data
from utils.browse import browse
from rongzai.dataSvc import read_cal,read_mask
# from rongzai.algSvc.neutron.pixel_offset_nd import PixelOffsetCalNeutronData
# from rongzai.algSvc.neutron.unit_convert_nd import UnitConvertNeutronData
from rongzai.algSvc.neutron.calculate_nd import CalculateNeutronData
import copy
from utils.ui.BaseUI import BaseDataProcessor

class time_focusing(BaseDataProcessor):
    def __init__(self, parent):
        super(time_focusing, self).__init__(parent)
        loadUi("utils/ui/time_focusing.ui", self)
        self.setStyleSheet(f"QFrame#time_focusing {{ background-color: lightblue; border: 1px solid black; }}")
        self.parent = parent

        self.unit_cvt = UnitConvertNeutronData()

        self.browse_run = browse()
        self.pushButton.clicked.connect(lambda: self.browse_run.select_folder(self.lineEdit))

    def run(self):
        try:
            split_data = self.split_by_name(self.parent.data_list)
            for key,items in split_data.items():
                print(key)
                modules_list = self.get_module_list(items,self.parent.config['base'])
                print(modules_list)
                backup_dict = self.get_focused_modules(modules_list, items)
                self.update_data(items,backup_dict)
                self.get_focused_detectors(items)
            self.parent.data_list = self.merge_split_data(split_data)
        except Exception as e:
            print(f'Reason: {e}')
            import traceback
            traceback.print_exc()  # 打印异常的堆栈跟踪

    def plot_data(self):
        return copy.deepcopy(self.parent.data_list)

    def get_focused_modules(self, modules_list, items):
        backup_dict = {}
        focused_dict = {}
        modules_exclude_set = set()
        for module in modules_list:
            if self.checkBox.isChecked():
                cal_fn = self.lineEdit.text() + "/" + module + "_offset.cal"
                cal_dict = read_cal(cal_fn)
                for item in items:
                    if 'modules_focused' not in item:
                        item['modules_focused'] = {}
                    for key, value in item['modules'].items():
                        if key == module and key not in modules_exclude_set:
                            value_deepcopy = copy.deepcopy(value)
                            task = PixelOffsetCalNeutronData()
                            value_d = task.correct_tof_to_d(value, cal_dict)
                            value_d_masked = mask_neutron_data(value_d, cal_dict["mask_list"])
                            value_focused = focus_neutron_data(value_d_masked)
                            modules_exclude_set.add(module)
                            item['modules_focused'][module] = value_focused
                            backup_dict[module] = value_deepcopy
                            focused_dict[module] = value_focused
                        elif key == module and key in modules_exclude_set:
                            item['modules_focused'][module] = focused_dict[module]
            else:
                for item in items:
                    if 'modules_focused' not in item:
                        item['modules_focused'] = {}
                    for key, value in item['modules'].items():
                        if key == module and key not in modules_exclude_set:
                            print(key)
                            value_deepcopy = copy.deepcopy(value)
                            value_d = self.unit_cvt.run(value, "dspacing")
                            value_focused = focus_neutron_data(value_d)
                            modules_exclude_set.add(module)
                            item['modules_focused'][module] = value_focused
                            print(modules_exclude_set)
                            backup_dict[module] = value_deepcopy
                            focused_dict[module] = value_focused
                        elif key == module and key in modules_exclude_set:
                            item['modules_focused'][module] = focused_dict[module]

        return backup_dict


    def get_focused_detectors(self,items):
        for item in items:
            group, modules = get_all_from_detector(item['detector'], self.parent.config['base']['group_info'],
                                                   self.parent.config['base']['bank_info'])
            dvalue = generate_x(self.parent.config['base']['d_rebin'][group][0],
                                self.parent.config['base']['d_rebin'][group][1],
                                self.parent.config['base']['d_rebin'][group][2], 'uniform')
            print('the number of modules_focused ', len(item['modules_focused'].values()))
            for i, module in enumerate(item['modules_focused'].values()):
                module = rebin_neutron_data(module, dvalue)
                if i == 0:
                    print(module.name)
                    item["detector_focused"] = module
                else:
                    nd_cal = CalculateNeutronData(item["detector_focused"], module)
                    item["detector_focused"] = nd_cal.add()

    def get_config(self):
        return {
            "offset": self.checkBox.isChecked(),
            "plot": self.plot.isChecked(),
            "offset_folder": self.lineEdit.text()
        }

    def set_config(self,config):
        """根据配置更新模块状态"""
        self.checkBox.setChecked(config.get("offset", False))  # 加载 QCheckBox 的选中状态
        self.plot.setChecked(config.get("plot", False))
        self.lineEdit.setText(config.get("offset_folder", ""))