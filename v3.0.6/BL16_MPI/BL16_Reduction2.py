from utils.ui import (load_beamline_config,load_focused_data, normalization,substraction_multiScale,division,
                      save_reduced_data,d_rebin,AIndex,RongZai_Agent)
from utils.ui.BaseUI import RunWidget
from utils.helper import get_resource_path

class Reduction(RunWidget):
    def __init__(self, parent=None):
        super(Reduction, self).__init__(parent)
        self.config = {}
        self.data_list = []

        # add and load each module
        self.load_beamline_config = self.add_module(load_beamline_config)
        self.load_beamline_config.auto_config(get_resource_path("CSNS_Alg/configure/BL16_base_new.json"))

        self.load_focused_data = self.add_module(load_focused_data, "Load Focused Data")
        self.normalization = self.add_module(normalization)
        self.d_rebin = self.add_module(d_rebin)
        self.subtract_bkg = self.add_module(substraction_multiScale,name="Subtract Bkg")
        self.sample_cell = self.add_module(substraction_multiScale,name="Sample-SampleCell")
        self.van_cell = self.add_module(substraction_multiScale, name="V-VanadiumCell")
        # self.sample_bkg = self.add_module(substraction,name="Sample Bkg Subtraction")
        # self.van_bkg = self.add_module(substraction, name="V Bkg Subtraction")
        self.division = self.add_module(division,"Division")
        self.RongZai_Agent = self.add_module(RongZai_Agent, name="RongZai Agent")
        self.AIndex = self.add_module(AIndex)
        self.save_reduced_data = self.add_module(save_reduced_data)
