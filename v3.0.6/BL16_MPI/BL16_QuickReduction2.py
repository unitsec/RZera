from utils.ui import load_beamline_config,reduction,save_reduced_data,AIndex,RongZai_Agent
from utils.ui.BaseUI import RunWidget
from utils.helper import get_resource_path

class QuickReduction(RunWidget):
    def __init__(self, parent=None):
        super(QuickReduction, self).__init__(parent)
        self.config = {}
        self.data_list = []

        # 加载并添加各个模块
        self.load_beamline_config = self.add_module(load_beamline_config)
        self.load_beamline_config.auto_config(get_resource_path("CSNS_Alg/configure/BL16_base_new.json"))
        self.quickReduction = self.add_module(reduction,"Quick Reduction")
        self.RongZai_Agent = self.add_module(RongZai_Agent, name="RongZai Agent")
        # self.AIndex = self.add_module(AIndex)
        self.save_reduced_data = self.add_module(save_reduced_data)
