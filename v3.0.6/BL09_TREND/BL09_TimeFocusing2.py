from utils.ui import load_beamline_config, load_and_focus, cut_peaks, smooth, save_focused_data
from utils.ui.BaseUI import RunWidget
from utils.helper import get_resource_path


class TimeFocusing(RunWidget):
    def __init__(self, parent=None):
        super(TimeFocusing, self).__init__(parent)
        self.config = {}
        self.data_list = []
        """
        self.data_list = [{
                            "name":str,
                            "runno":"{runno}"(str),
                            "time_slice"(optional):"{start_time}_{end_time}"(str),
                            "detector":str,
                            "data_focused":(dataset), 注：dataset的格式可以查看rongzai在load_neutron_data方法中的行为
                            "monitor":(dataset), 注：monitor数据会进行record中的crop，但不会进行mask,carpenter_correction和offset
                            "monitor_counts" = sum count of monitor data(float),
                            "record":{
                                    "mask"(optional):"{mask_folder}"(str),
                                    "crop"(optional):"{wavemin}_{wavemax}"(str),
                                    “carpenterCorrection”(optional):{
                                                                "sample_name":(str),
                                                                "mass"(str),
                                                                "volume":{
                                                                        "type":"cylinder"(str),
                                                                        "height":sample_height(float),
                                                                        "radius":sample_radius(float),
                                                                        "beam_height":beam_height(float),
                                                                        "thickness": 0(float)}
                                                                        }(dict)
                                                                "scale":1(float)
                                                                }(dict),
                                    "offset"(optional):"{offset_folder}"(str),
                                    ...,
                                    "":str
                                      },
                            },
                            ...,{}]
        """

        # 加载并添加各个模块
        self.load_beamline_config = self.add_module(load_beamline_config)
        self.load_beamline_config.auto_config(get_resource_path("CSNS_Alg/configure/BL09_base_new.json"))

        self.load_and_focus = self.add_module(load_and_focus,"Load and Time Focusing")
        self.cut_peaks = self.add_module(cut_peaks,"Cut Peaks")
        self.smooth = self.add_module(smooth, "Smooth")
        self.save_focused_data = self.add_module(save_focused_data, "Save Focused Data")
