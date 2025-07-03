from drneutron.python.algSvc.instrument.diffraction import Diffraction
from drneutron.python.algSvc.base import (rebin,strip_peaks,smooth,
                        generate_x)
import numpy as np
from drneutron.python.dataSvc.data_load import load_neutron_data,create_dataset
from drneutron.python.dataSvc.data_save import diffraction_format
from drneutron.python.dataSvc.read_format import read_cal
from drneutron.python.dataSvc.write_format import write_ascii
from drneutron.python.algSvc.neutron.abs_ms_nd import AbsMsCorrNeutronData
from drneutron.python.utils.constants import *
from drneutron.python.utils.helper import check_dir,replace_value,check_zeros
import matplotlib.pyplot as plt

class CSNS_Diffraction(Diffraction):
    def __init__(self,configure,bankname):
        super().__init__()
        self.conf = configure
        params = self.conf["diff_d_rebin"][bankname]
        self.xnew = generate_x(params[0], params[1], params[2], self.conf["rebin_mode"])
        self.tof = self.conf["focus_point"][bankname[:5]]["factor"]*self.xnew
        self.moduleList = ["module" + str(num) for num in self.conf["bank_group"][bankname]]
        self.bankname = bankname
        self.suffix = "_d"
        if self.conf["normByPC"]:
            self.suffix = "_pc"+self.suffix
        self.conf["current_bank"]=bankname


    def process_bank(self,name,fn_list=[],isSave=False):
        cal_dict = {}
        cal_dict["has_cal"] = False
        if len(fn_list)==0:
            nxsfn_list = self.conf[name+"_fn"]
        else:
            nxsfn_list = fn_list.copy()
        for i in range(len(self.moduleList)):
            txt_fn = self.conf["param_path"] + "/" + self.moduleList[i] + ".txt"
            if self.conf["has_cal"]:
                cal_fn = self.conf["cal_path"]+"/"+self.moduleList[i]+"_offset.cal"
                cal_dict = read_cal(cal_fn)
                cal_dict["has_cal"] = True
            module = self.moduleList[i]
            neutron_data = load_neutron_data(nxsfn_list,txt_fn,module,
                                        first_flight_distance_BL16,self.conf["T0offset"])
            if name=="v":
                neutron_data = self.time_focusing_vanadium(neutron_data,self.conf["wavemin"],
                                                self.conf['wavemax'],cal_dict,
                                                self.conf["v_correct"])
            else:
                neutron_data = self.time_focusing_sample(neutron_data,self.conf["wavemin"],self.conf['wavemax'],cal_dict)
            x,y,e = neutron_data["xvalue"].values[0],neutron_data["histogram"].values[0],neutron_data["error"].values[0]
            ytmp,etmp = rebin(x,y,e,self.xnew)
            if i == 0:
                ynew = ytmp
                enew = etmp
            else:
                ynew+=ytmp
                enew=np.sqrt(enew**2+etmp**2)
        if self.conf["normByPC"]==True:
            nc = neutron_data["proton_charge"].values/self.pc_factor
        else:
            txt_fn = self.conf["param_path"]+"/"+self.conf["normalization_monitor"]+".txt"
            monitor_data = load_neutron_data(nxsfn_list,txt_fn,self.conf["normalization_monitor"],
                                            first_flight_distance_BL16)
            nc = self.get_monitor_nc(monitor_data,self.conf["wavemin"],self.conf['wavemax'])
        ynew /= nc
        enew /= nc
        if name=="v":
            ynew = strip_peaks(self.xnew,ynew,self.conf["v_peaks"][self.bankname[:5]])
            ynew = smooth(ynew, self.conf["smooth"][self.bankname[:5]]["npoint"], self.conf["smooth"][self.bankname[:5]]["order"])
            enew = np.zeros(ynew.size)
        if isSave:
            runno = self.conf[name+"_run"][0]
        return ynew,enew
