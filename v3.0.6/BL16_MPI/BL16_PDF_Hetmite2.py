from utils.ui import load_beamline_config, reduction, load_focused_data, normalization, substraction_multiScale, division, \
    convert_sq, d_rebin, hermite_fitting,get_sq_from_pdf,save_sq, save_pdf, RongZai_Agent
from utils.ui.BaseUI import RunWidget
from utils.helper import get_resource_path

class PDFHermite(RunWidget):
    def __init__(self, parent=None):
        super(PDFHermite, self).__init__(parent)
        self.config = {}
        self.data_list = []

        # 加载并添加各个模块
        self.load_beamline_config = self.add_module(load_beamline_config)
        self.load_beamline_config.auto_config(get_resource_path("CSNS_Alg/configure/BL16_base_new.json")) # 加载配置文件

        self.quick_reduction = self.add_module(reduction, "Quick Reduction")
        self.load_focused_data = self.add_module(load_focused_data, "Load Focused Data")
        self.normalization = self.add_module(normalization)
        self.d_rebin = self.add_module(d_rebin)
        self.subtract_bkg = self.add_module(substraction_multiScale,name="Subtract Bkg")
        self.sample_cell = self.add_module(substraction_multiScale,name="Sample-SampleCell")
        self.van_cell = self.add_module(substraction_multiScale, name="V-VanadiumCell")
        self.division = self.add_module(division, "Division")
        self.convert_sq = self.add_module(convert_sq, "S(Q) Convertion")
        self.hermite_fitting = self.add_module(hermite_fitting)
        # self.rongzai_agent = self.add_module(RongZai_Agent, "RongZai Agent")
        self.save_pdf = self.add_module(save_pdf)
        self.get_sq_from_pdf = self.add_module(get_sq_from_pdf)
        self.save_sq = self.add_module(save_sq)






