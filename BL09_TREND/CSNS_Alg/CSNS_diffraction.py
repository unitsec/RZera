import sys,os
# current_dir = os.path.dirname(os.path.abspath(__file__))
# relative_path = os.path.join(current_dir, '..','rongzai')
# if relative_path not in sys.path:
#     sys.path.append(relative_path)

from rongzai.algSvc.instrument.diffraction import Diffraction
from rongzai.algSvc.base import (rebin,strip_peaks,smooth)
import numpy as np
from rongzai.dataSvc import (load_neutron_data,create_dataset,DiffractionFormat)
from rongzai.dataSvc.write_format import write_ascii
from rongzai.utils import (check_dir,replace_value,check_zeros, check_file,generate_x,
                   get_all_from_detector)
from rongzai.utils.config_utils import generate_diffraction_conf
from utils.redisHelper import getRedisHelper
from rongzai.dataSvc.data_load import assemble_neutron_data

#
class CSNS_Diffraction(Diffraction):
    def __init__(self, base_json, diffraction_json, detector, online=False, ui=False, redis_configure=None):
        self.ui = ui
        if self.ui is True:
            self.conf = {**diffraction_json, **base_json}
        else:
            self.conf = generate_diffraction_conf(base_json,diffraction_json)
        super().__init__(self.conf)
        self.groupname,self.moduleList = get_all_from_detector(detector,self.conf["group_info"],self.conf["bank_info"])
        self.detector = detector
        if detector[:4] == "bank":
            params = self.conf["d_rebin"][self.detector]
        else:
            params = self.conf["d_rebin"][self.groupname]
        self.xnew = generate_x(params[0], params[1], params[2], self.conf["rebin_mode"])
        self.tof = self.conf["focus_point"][self.groupname]["factor"]*self.xnew
        self.suffix = "d.dat"
        if self.conf["norm_by_pc"]:
            self.suffix = "pc_"+self.suffix
        self.conf["current_bank"]=self.groupname
        if self.ui is not True:
            check_dir(self.conf["save_path"])
        #配置在线
        self.online = online
        if self.online is True:
            if redis_configure is None:
                raise ValueError("redis_configure must be provided when online is True.")
            else:
                self.rds = getRedisHelper(redis_configure)


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
        if len(fn_list)==0:
            nxsfn_list = self.conf[name+"_fn"]
        else:
            nxsfn_list = fn_list.copy()
        for i in range(len(self.moduleList)):
            txt_fn = self.conf["param_path"] + "/" + self.moduleList[i] + ".txt"
            module = self.moduleList[i]

            if self.online:
                if name == 'sam' and not self.conf['samrun_check']:
                    histogram_data = self.rds.readNumpyArray("/mpi/workspace/detector/" + module + "/value")
                    self.conf['sam_run_online']= [f'RUN{self.rds.readStr("/mpi/imacs/runno")}']
                    histogram_data = histogram_data.T
                    histogram_data = histogram_data.astype(int)
                    x_data = self.rds.readNumpyArray("/mpi/workspace/detector/" + module + "/tof")
                    error_data = np.sqrt(histogram_data)
                    neutron_data = assemble_neutron_data(x_data, histogram_data, error_data, 1.0, txt_fn, module,
                                                         self.conf['first_flight_distance'])
                else:
                    neutron_data = load_neutron_data(nxsfn_list,txt_fn,module,
                                                self.conf['first_flight_distance'],self.conf["T0_offset"])
            else:
                neutron_data = load_neutron_data(nxsfn_list, txt_fn, module,
                                                 self.conf['first_flight_distance'], self.conf["T0_offset"])

            if name=="v" and self.conf["vanadium_correction"]["do_correction"]:
                neutron_data = self.calculate_pattern(neutron_data,self.conf["vanadium_correction"])
            else:
                neutron_data = self.calculate_pattern(neutron_data)
            x,y,e = neutron_data["xvalue"].values[0],neutron_data["histogram"].values[0],neutron_data["error"].values[0]
            ytmp,etmp = rebin(x,y,e,self.xnew)
            if i == 0:
                ynew = ytmp
                enew = etmp
            else:
                ynew+=ytmp
                enew=np.sqrt(enew**2+etmp**2)
        if self.conf["norm_by_pc"]==True:
            nc = neutron_data["proton_charge"].values/self.pc_factor
            print("proton charge / 10E7 :", nc)
        else:
            txt_fn = self.conf["param_path"]+"/"+self.conf["normalization_monitor"]+".txt"

            if self.online:
                if name == 'sam' and not self.conf['samrun_check']:
                    histogram_data = self.rds.readNumpyArray(
                        "/mpi/workspace/" + self.conf["normalization_monitor"] + "/value")
                    histogram_data = histogram_data.T
                    histogram_data = histogram_data.astype(int)
                    error_data = np.sqrt(histogram_data)
                    x_data = self.rds.readNumpyArray("/mpi/workspace/" + self.conf["normalization_monitor"] + "/tof")
                    monitor_data = assemble_neutron_data(x_data, histogram_data, error_data, 1.0, txt_fn,
                                                         self.conf["normalization_monitor"],
                                                         self.conf['first_flight_distance'])
                else:
                    monitor_data = load_neutron_data(nxsfn_list, txt_fn, self.conf["normalization_monitor"],
                                                     self.conf["first_flight_distance"])
            else:

                monitor_data = load_neutron_data(nxsfn_list, txt_fn, self.conf["normalization_monitor"],
                                                 self.conf["first_flight_distance"])

            nc = self.get_monitor_nc(monitor_data)
            print("monitor counts:", nc)
        ynew /= nc
        enew /= nc

        if name=="v":
            if self.conf["vanadium_name"] == "VNi":
                pass
            else:
                ynew = strip_peaks(self.xnew, ynew, self.conf["vanadium_peaks"][self.groupname]["peaks"],
                                                      self.conf["vanadium_peaks"][self.groupname]["range"])
                # ynew = strip_peaks(self.xnew,ynew,self.conf["vanadium_peaks"][self.groupname]["peaks"],
                #                    self.conf["vanadium_peaks"][self.groupname]["left"],self.conf["vanadium_peaks"][self.groupname]["right"])
                ynew = smooth(ynew, self.conf["vanadium_smooth"][self.groupname]["npoint"], self.conf["vanadium_smooth"][self.groupname]["order"])

            enew = np.zeros(ynew.size)
        if isSave:
            runno = self.conf[name+"_run"][0]
            fn = self.conf["data_path"]+"/"+runno+"/"+name+"_"+runno+"_"+self.detector+"_"+self.suffix
            write_ascii(fn,self.xnew,ynew,enew)
        return ynew,enew

    def reduction(self):
        #import matplotlib.pyplot as plt
        other_plot_data = {}
        if len(self.conf["samBG_run"])>0:
            if self.conf["samBG_run_mode"]=="dat":
                if self.ui is True:
                    fn = self.conf["samBG_fn"][0] + "/samBG_" + self.conf["samBG_run"][
                        0] + "_" + self.detector + "_" + self.suffix
                else:
                    runno = self.conf["samBG_run"][0]
                    fn = self.conf["data_path"]+"/"+runno+"/samBG_"+self.conf["samBG_run"][0]+"_"+self.detector+"_"+self.suffix
                if check_file(fn):
                    x,y,e = np.loadtxt(fn,unpack=True)
                    y_samBG,e_samBG = rebin(x,y,e,self.xnew)
                else:
                    if self.ui is True:
                        y_samBG,e_samBG = self.process_bank("samBG",[],False)
                    else:
                        y_samBG, e_samBG = self.process_bank("samBG", [], True)
            else:
                if self.ui is True:
                    y_samBG, e_samBG = self.process_bank("samBG", [], False)
                else:
                    y_samBG,e_samBG = self.process_bank("samBG",[],True)
            print("finsih samBG for ", self.conf["samBG_run"], self.detector)
            other_plot_data['samBG'] = [self.xnew, y_samBG, e_samBG]

        if len(self.conf["v_run"])>0:
            print("start v: ", self.conf["v_run_mode"])
            if self.conf["v_run_mode"]=="dat":
                if self.ui is True:
                    fn = self.conf["v_fn"][0] + "/v_" + self.conf["v_run"][0] + "_" + self.detector + "_" + self.suffix
                else:
                    runno = self.conf["v_run"][0]
                    fn = self.conf["data_path"]+"/"+runno+"/v_"+self.conf["v_run"][0]+"_"+self.detector+"_"+self.suffix
                if check_file(fn):
                    print(f"find such file:{fn}")
                    x,y,e = np.loadtxt(fn,unpack=True)
                    y_v,e_v = rebin(x,y,e,self.xnew)
                else:
                    if self.ui is True:
                        y_v, e_v = self.process_bank("v", [], False)
                    else:
                        y_v,e_v = self.process_bank("v",[],True)
            else:
                if self.ui is True:
                    y_v, e_v = self.process_bank("v", [], False)
                else:
                    y_v,e_v = self.process_bank("v",[],True)
            other_plot_data['v'] = [self.xnew, y_v, e_v]

            if len(self.conf["vBG_run"])>0:
                if self.conf["vBG_run_mode"]=="dat":
                    if self.ui is True:
                        fn = self.conf["vBG_fn"][0] + "/vBG_" + self.conf["vBG_run"][0] + "_" + self.detector + "_" + self.suffix
                    else:
                        runno = self.conf["samBG_run"][0]
                        fn = self.conf["save_path"]+"/"+runno+"/vBG"+self.conf["vBG_run"][0]+"_"+self.detector+"_"+self.suffix
                    if check_file(fn):
                        x,y,e = np.loadtxt(fn,unpack=True)
                        y_vBG,e_vBG = rebin(x,y,e,self.xnew)
                    else:
                        if self.ui is True:
                            y_vBG,e_vBG = self.process_bank("vBG",[],False)
                        else:
                            y_vBG, e_vBG = self.process_bank("vBG", [], True)
                else:
                    if self.ui is True:
                        y_vBG, e_vBG = self.process_bank("vBG", [], False)
                    else:
                        y_vBG, e_vBG = self.process_bank("vBG", [], True)
                other_plot_data['vBG'] = [self.xnew, y_vBG, e_vBG]
                if self.conf["scale_v_bg"]>0:
                    y_v = y_v - self.conf["scale_v_bg"]*y_vBG
            print("finsih v for ",self.conf["v_run"],self.detector)

        sam_plot_data = {}
        if self.conf["is_batch"]:
            for i in range(len(self.conf["sam_fn"])):
                run_fn = self.conf["sam_fn"][i]
                y_sam, e_sam = self.process_bank("sam",[run_fn],False)
                other_plot_data[f'sam_{i}'] = [self.xnew, y_sam, e_sam]
                if len(self.conf["samBG_run"])>0:
                    y_sam = y_sam-self.conf["scale_sam_bg"]*y_samBG
                    e_sam = np.sqrt(e_sam**2+(self.conf["scale_sam_bg"]*e_samBG)**2)
                if len(self.conf["v_run"])>0:
                    y_sam = y_sam/y_v
                    e_sam = e_sam/y_v

                if 'data_scale' in self.conf and self.conf['data_scale'] is not None:
                    y_sam = y_sam * float(self.conf['data_scale'])
                    e_sam = e_sam * float(self.conf['data_scale'])

                if self.ui is True:
                    sam_plot_data[f'sam_{i}'] = [self.xnew, y_sam, e_sam]
                else:
                    if self.conf["time_slice"]:
                        runno = self.conf["sam_run"][0]
                        suffix_tmp = str(i)+self.suffix
                        self.conf["slice_series"] = i
                        sam_plot_data[runno+f'_{i}'] = [self.xnew, y_sam, e_sam]
                    else:
                        runno = self.conf["sam_run"][i]
                        suffix_tmp = self.suffix
                        sam_plot_data[runno] = [self.xnew, y_sam, e_sam]
                    path = self.conf["save_path"] + "/" + runno
                    check_dir(path)
                    fn = path+"/"+"sam_"+runno+"_"+self.detector+"_"+suffix_tmp
                    write_ascii(fn,self.xnew,y_sam,e_sam)
                    self.conf["current_runno"] = runno
                    output = DiffractionFormat(self.conf,self.tof,y_sam,e_sam)
                    fn = path+"/"+runno+"_"+self.detector
                    output.writeGSAS(fn+".gsa")
                    output.writeZR(fn+".histogramIgor")
                    output.writeFP(fn+".dat")
        else:
            y_sam, e_sam = self.process_bank("sam",[],False)
            other_plot_data['sam_0'] = [self.xnew, y_sam, e_sam]
            if len(self.conf["samBG_run"])>0:
                y_sam = y_sam-self.conf["scale_sam_bg"]*y_samBG
                e_sam = np.sqrt(e_sam**2+(self.conf["scale_sam_bg"]*e_samBG)**2)

            if len(self.conf["v_run"])>0:
                y_sam = y_sam/y_v
                e_sam = e_sam/y_v

            if 'data_scale' in self.conf and self.conf['data_scale'] is not None:
                y_sam = y_sam * float(self.conf['data_scale'])
                e_sam = e_sam * float(self.conf['data_scale'])

            if self.ui is True:
                sam_plot_data['sam_0'] = [self.xnew, y_sam, e_sam]
            else:
                runno = self.conf["sam_run"][0]
                sam_plot_data[runno] = [self.xnew, y_sam, e_sam]
                path = self.conf["save_path"]+"/"+runno
                check_dir(path)
                fn = path+"/"+"sam_"+runno+"_"+self.detector+"_"+self.suffix
                write_ascii(fn,self.xnew,y_sam,e_sam,format="%.15f")
                self.conf["current_runno"] = runno
                output = DiffractionFormat(self.conf,self.tof,y_sam,e_sam)
                fn = path + "/" + runno + "_" + self.detector
                output.writeGSAS(fn + ".gsa")
                output.writeZR(fn + ".histogramIgor")
                output.writeFP(fn + ".dat")
        return sam_plot_data, other_plot_data
        # 两个字典。key指示数据名称，ui和非ui模式下sam_plot_data中的key命名规则不同。value为列表，格式为[x,y,error],x,y,error各为一个numpy列表。
