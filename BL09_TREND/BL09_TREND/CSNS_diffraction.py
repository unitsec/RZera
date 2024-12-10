import sys,os
from rongzai.algSvc.instrument.diffraction import Diffraction
from rongzai.algSvc.base import (rebin,strip_peaks,smooth)
import numpy as np
from rongzai.dataSvc.data_load import load_neutron_data,create_dataset
from rongzai.dataSvc import DiffractionFormat
from rongzai.dataSvc.write_format import write_ascii
from rongzai.utils import (check_dir,replace_value,check_zeros, check_file,generate_x,
                   get_all_from_detector)
from rongzai.utils.config_utils import generate_diffraction_conf
#
class CSNS_Diffraction(Diffraction):
    def __init__(self,base_configure,diffraction_configure,detector):
        self.conf = {**base_configure, **diffraction_configure}
        # self.conf = generate_diffraction_conf(base_json,diffraction_json)
        super().__init__(self.conf)
        # self.conf = configure
        self.groupname,self.moduleList = get_all_from_detector(detector,self.conf["group_info"],self.conf["bank_info"])
        self.detector = detector

        params = self.conf["d_rebin"][self.detector]
        self.xnew = generate_x(params[0], params[1], params[2], self.conf["rebin_mode"])
        self.tof = self.conf["focus_point"][self.groupname]["factor"]*self.xnew
        self.suffix = "d.dat"
        if self.conf["norm_by_pc"]:
            self.suffix = "pc_"+self.suffix
        self.conf["current_bank"]=self.groupname
        # check_dir(self.conf["save_path"])
#
    def process_wavelength(self,name,fn_list=[]):
        if len(fn_list) == 0:
            nxsfn_list = self.conf[name + "_fn"]
        else:
            nxsfn_list = fn_list.copy()
        for i in range(len(self.moduleList)):
            txt_fn = self.conf["param_path"] + "/" + self.moduleList[i] + ".txt"
            module = self.moduleList[i]
            neutron_data = load_neutron_data(nxsfn_list, txt_fn, module,
                                             self.conf['first_flight_distance'], self.conf["T0_offset"])
            neutron_data = self.get_wavelength_data(neutron_data)
            if i == 0:
                x, y, e = neutron_data["xvalue"].values[0], neutron_data["histogram"].values[0], \
                    neutron_data["error"].values[0]
            else:
                xtmp,ytmp,etmp = neutron_data["xvalue"].values[0], neutron_data["histogram"].values[0], \
                    neutron_data["error"].values[0]
                ytmp, etmp = rebin(xtmp, ytmp, etmp, x)
                y += ytmp
                e = np.sqrt(e ** 2 + etmp ** 2)
            return x,y,e

    def process_bank(self,name,fn_list=[],isSave=False):
        # import matplotlib.pyplot as plt
        if len(fn_list)==0:
            nxsfn_list = self.conf[name+"_fn"]
        else:
            nxsfn_list = fn_list.copy()
        for i in range(len(self.moduleList)):
            txt_fn = self.conf["param_path"] + "/" + self.moduleList[i] + ".txt"
            module = self.moduleList[i]

            neutron_data = load_neutron_data(nxsfn_list,txt_fn,module,
                                        self.conf['first_flight_distance'],self.conf["T0_offset"])
            if name=="v" and self.conf["vanadium_correction"]["do_correction"]:
                neutron_data = self.calculate_pattern(neutron_data,self.conf["vanadium_correction"])
            else:
                neutron_data = self.calculate_pattern(neutron_data)
            x,y,e = neutron_data["xvalue"].values[0],neutron_data["histogram"].values[0],neutron_data["error"].values[0]
            ytmp,etmp = rebin(x,y,e,self.xnew)
            # if name == "sam":
            #     print(x.size,self.xnew.size)
            #     plt.plot(x,y,label="old")
            #     plt.plot(self.xnew,ytmp,label="rebin")
            #     plt.legend()
            #     plt.title(module)
            #     plt.show()
            if i == 0:
                ynew = ytmp
                enew = etmp
            else:
                ynew+=ytmp
                enew=np.sqrt(enew**2+etmp**2)
        if self.conf["norm_by_pc"]==True:
            nc = neutron_data["proton_charge"].values/self.pc_factor
        else:
            txt_fn = self.conf["param_path"]+"/"+self.conf["normalization_monitor"]+".txt"
            monitor_data = load_neutron_data(nxsfn_list,txt_fn,self.conf["normalization_monitor"],
                                            self.conf["first_flight_distance"])
            nc = self.get_monitor_nc(monitor_data)
            print(nc)
        ynew /= nc
        enew /= nc

        if name=="v":
            if self.conf["vanadium_name"] == "VNi":
                pass
            else:
                # ynew = strip_peaks(self.xnew,ynew,self.conf["vanadium_peaks"][self.groupname]["peaks"],
                #                    self.conf["vanadium_peaks"][self.groupname]["left"], self.conf["vanadium_peaks"][self.groupname]["right"])
                ynew = strip_peaks(self.xnew, ynew, self.conf["vanadium_peaks"][self.groupname]["peaks"],
                                   self.conf["vanadium_peaks"][self.groupname]["range"])
            ynew = smooth(ynew, self.conf["vanadium_smooth"][self.groupname]["npoint"], self.conf["vanadium_smooth"][self.groupname]["order"])
            enew = np.zeros(ynew.size)
        if isSave:
            runno = self.conf[name+"_run"][0]
            fn = self.conf["data_path"]+"/"+runno+"/"+name+"_"+runno+"_"+self.detector+"_"+self.suffix
            write_ascii(fn,self.xnew,ynew,enew)
        return ynew,enew

    def reduction(self):
        if len(self.conf["samBG_run"])>0:
            if self.conf["samBG_run_mode"]=="dat":
                fn = self.conf["save_path"]+"/samBG_"+self.conf["samBG_run"][0]+"_"+self.detector+"_"+self.suffix
                if check_file(fn):
                    x,y,e = np.loadtxt(fn,unpack=True)
                    y_samBG,e_samBG = rebin(x,y,e,self.xnew)
                else:
                    y_samBG,e_samBG = self.process_bank("samBG",[],True)
            else:
                y_samBG,e_samBG = self.process_bank("samBG",[],True)
            print("finsih samBG for ",self.conf["samBG_run"],self.detector)

        if len(self.conf["v_run"])>0:
            if self.conf["v_run_mode"]=="dat":
                fn = self.conf["save_path"]+"/v_"+self.conf["v_run"][0]+"_"+self.detector+"_"+self.suffix
                if check_file(fn):
                    x,y,e = np.loadtxt(fn,unpack=True)
                    y_v,e_v = rebin(x,y,e,self.xnew)
                else:
                    y_v,e_v = self.process_bank("v",[],True)
            else:
                y_v,e_v = self.process_bank("v",[],True)
            if len(self.conf["vBG_run"])>0:
                if self.conf["vBG_run_mode"]=="dat":
                    fn = self.conf["save_path"]+"/vBG"+self.conf["vBG_run"][0]+"_"+self.detector+"_"+self.suffix
                    if check_file(fn):
                        x,y,e = np.loadtxt(fn,unpack=True)
                        y_vBG,e_vBG = rebin(x,y,e,self.xnew)
                    else:
                        y_vBG,e_vBG = self.process_bank("vBG",[],True)
                else:
                    y_vBG,e_vBG = self.process_bank("vBG",[],True)
                if self.conf["scale_v_bg"]>0:
                    y_v = y_v - self.conf["scale_v_bg"]*y_vBG
            print("finsih v for ",self.conf["v_run"],self.detector)


        if self.conf["is_batch"]:
            for i in range(len(self.conf["sam_fn"])):
                run_fn = self.conf["sam_fn"][i]
                y_sam, e_sam = self.process_bank("sam",[run_fn],False)
                if len(self.conf["samBG_run"])>0:
                    y_sam = y_sam-self.conf["scale_sam_bg"]*y_samBG
                    e_sam = np.sqrt(e_sam**2+(self.conf["scale_sam_bg"]*e_samBG)**2)
                if len(self.conf["v_run"])>0:
                    y_sam = y_sam/y_v
                    e_sam = e_sam/y_v

                if self.conf["time_slice"]:
                    runno = self.conf["sam_run"][0]
                    suffix_tmp = str(i)+self.suffix
                    self.conf["slice_series"] = i
                else:
                    runno = self.conf["sam_run"][i]
                    suffix_tmp = self.suffix
                fn = self.conf["save_path"]+"/"+"sam_"+runno+"_"+self.detector+"_"+suffix_tmp
                write_ascii(fn,self.xnew,y_sam,e_sam)
                self.conf["current_runno"] = runno
                output = DiffractionFormat(self.conf,self.tof,y_sam,e_sam)
                output.writeGSAS()
                output.writeZR()
                output.writeFP()
        else:
            y_sam, e_sam = self.process_bank("sam",[],True)
            if len(self.conf["samBG_run"])>0:
                y_sam = y_sam-self.conf["scale_sam_bg"]*y_samBG
                e_sam = np.sqrt(e_sam**2+(self.conf["scale_sam_bg"]*e_samBG)**2)

            if len(self.conf["v_run"])>0:
                y_sam = y_sam/y_v
                e_sam = e_sam/y_v

            runno = self.conf["sam_run"][0]
            fn = self.conf["save_path"]+"/"+"sam_"+runno+"_"+self.detector+"_"+self.suffix
            write_ascii(fn,self.xnew,y_sam,e_sam)
            self.conf["current_runno"] = runno
            output = DiffractionFormat(self.conf,self.tof,y_sam,e_sam)
            output.writeGSAS()
            output.writeZR()
            output.writeFP()

        return self.xnew,y_sam,e_sam
