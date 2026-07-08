from utils.ui import load_beamline_config,load_focused_data, normalization,substraction_multiScale,division,save_reduced_data,d_rebin,AIndex,RongZai_Agent
from utils.ui.BaseUI import RunWidget
from utils.helper import get_resource_path

class Reduction(RunWidget):
    def __init__(self, parent=None):
        super(Reduction, self).__init__(parent)
        self.config = {}
        self.data_list = []

        # 加载并添加各个模块
        self.load_beamline_config = self.add_module(load_beamline_config)
        self.load_beamline_config.auto_config(get_resource_path("CSNS_Alg/configure/BL09_base_new.json"))

        self.load_focused_data = self.add_module(load_focused_data,name="Load Focused Data")
        self.normalization = self.add_module(normalization)
        self.d_rebin = self.add_module(d_rebin)
        self.sample_cell = self.add_module(substraction_multiScale,name="Sample-SampleCell")
        self.van_cell = self.add_module(substraction_multiScale, name="V-VanadiumCell")
        self.division = self.add_module(division,"Calibration")
        # self.AIndex = self.add_module(AIndex)
        self.RongZai_Agent = self.add_module(RongZai_Agent, name="RongZai Agent")
        self.save_reduced_data = self.add_module(save_reduced_data)
