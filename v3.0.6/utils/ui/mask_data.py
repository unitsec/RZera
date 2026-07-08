from PyQt5.uic import loadUi
from rongzai.dataSvc import read_mask
from rongzai.algSvc.neutron import mask_neutron_data
from utils.browse import browse
from utils.ui.BaseUI import BaseDataProcessor

class mask_data(BaseDataProcessor):
    def __init__(self, parent):
        super(mask_data, self).__init__(parent)
        loadUi("utils/ui/mask_data.ui", self)
        self.parent = parent

        # 初始化mask开关
        self.use.stateChanged.connect(self.toggle_style)
        self.use.setChecked(False)

        self.browse_run = browse()
        self.pushButton.clicked.connect(lambda: self.browse_run.select_folder(self.lineEdit))

    def run(self):
        try:
            if self.use.isChecked():
                split_data = self.split_by_name(self.parent.data_list)
                for items in split_data.values():
                    modules_list = self.get_module_list(items,self.parent.config['base'])
                    masked_data_dict = self.get_masked_data(modules_list,items)
                    self.update_data(items,masked_data_dict)
                self.parent.data_list = self.merge_split_data(split_data)
        except Exception as e:
            print(f'Reason: {e}')
            import traceback
            traceback.print_exc()  # 打印异常的堆栈跟踪

    def get_masked_data(self, modules_list, items):
        masked_data_dict = {}
        modules_exclude_set = set()
        for module in modules_list:
            mask_file = self.lineEdit.text() + "/" + module + "_mask.txt"
            cal_dict = read_mask(mask_file)
            for item in items:
                for key, value in item['modules'].items():
                    if key == module and key not in modules_exclude_set:
                        masked_data = mask_neutron_data(value, cal_dict["mask_list"])
                        modules_exclude_set.add(module)
                        masked_data_dict[module] = masked_data
        return masked_data_dict

    def toggle_style(self):
        if self.use.isChecked():
            # Set active style
            self.setStyleSheet(f"QFrame#mask_data {{ background-color: lightblue; border: 1px solid black; }}")
        else:
            # Set inactive style
            self.setStyleSheet(f"QFrame#mask_data {{ background-color: lightgrey; }}")

    def get_config(self):
        return {
            "folder_path": self.lineEdit.text(),  # 保存mask文件路径
            "use": self.use.isChecked()
        }

    def set_config(self,config):
        """根据配置更新模块状态"""
        self.use.setChecked(config.get("use", False))  # 加载 QCheckBox 的选中状态
        self.lineEdit.setText(config.get("folder_path", ""))