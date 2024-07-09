from drneutron.python.algSvc.instrument.diffraction import Diffraction
from drneutron.python.algSvc.base.calculate_sample import CalSampleProperty
from drneutron.python.algSvc.base import (interpolate,cal_PDF,merge_all_curves,rebin,
                        generate_x,strip_peaks,smooth)
import json
from drneutron.python.dataSvc.data_load import load_neutron_data,create_dataset
from drneutron.python.dataSvc.read_format import read_cal
from drneutron.python.dataSvc.write_format import write_ascii
from drneutron.python.utils.constants import *
from drneutron.python.utils.helper import check_dir,check_zeros,replace_value
from drneutron.python.algSvc.neutron.abs_ms_nd import AbsMsCorrNeutronData
from drneutron.python.algSvc.neutron import units_convert_neutron_data

class CSNS_PDF(Diffraction):
    def __init__(self,conf,detector):
        super().__init__()
        self.conf = conf
        self.cal_sample_property()
        self.detector = detector
        if detector[:4]=="bank":
            self.bankname = detector
            self.moduleList = ["module" + str(num) for num in self.conf["bank_group"][self.bankname]]

        else:
            self.bankname = self.conf["bank_match"][detector]
            self.moduleList = [detector]
        params = self.conf["default_d_rebin"][self.bankname]
        self.xnew = generate_x(params[0], params[1], params[2], "uniform")

    def process_detector(self,fn_list,isV):
        cal_dict = {}
        cal_dict["has_cal"] = False
        for i in range(len(self.moduleList)):
            txt_fn = self.conf["param_path"] + "/" + self.moduleList[i] + ".txt"
            if self.conf["has_cal"]:
                cal_fn = self.conf["cal_path"]+"/"+self.moduleList[i]+"_offset.cal"
                cal_dict = read_cal(cal_fn)
                cal_dict["has_cal"] = True
            module = self.moduleList[i]
            neutron_data = load_neutron_data(fn_list,txt_fn,module,
                                        first_flight_distance_BL16,self.conf["T0offset"])
            if isV:
                neutron_data = self.time_focusing_vanadium(neutron_data,self.conf["wavemin"],
                                                self.conf['wavemax'],cal_dict,
                                                self.conf["v_correct"])
            else:
                neutron_data = self.time_focusing_vanadium(neutron_data, self.conf["wavemin"],
                                                           self.conf['wavemax'], cal_dict,
                                                           self.conf["sample_property"])
            x,y,e = neutron_data["xvalue"].values[0],neutron_data["histogram"].values[0],neutron_data["error"].values[0]
            ytmp,etmp = rebin(x,y,e,self.xnew)
            if i == 0:
                ynew = ytmp
                enew = etmp
            else:
                ynew+=ytmp
                enew=np.sqrt(enew**2+etmp**2)
        if isV:
            ynew = strip_peaks(self.xnew,ynew,self.conf["v_peaks"][self.bankname])
            ynew = smooth(ynew, 21, 3)
            enew = np.zeros(ynew.size)

        if self.conf["normByPC"]==True:
            nc = neutron_data["proton_charge"].values / self.pc_factor
            ynew /= nc
            enew /= nc
            neutron_data = create_dataset(ynew,enew,self.xnew,
                                    neutron_data["positions"].coords["pixel"].values,
                                    neutron_data["positions"].values,
                                    neutron_data['proton_charge'],neutron_data['l1'])
        else:
            neutron_data = create_dataset(ynew, enew, self.xnew,
                                          neutron_data["positions"].coords["pixel"].values,
                                          neutron_data["positions"].values,
                                          neutron_data['proton_charge'], neutron_data['l1'])
            txt_fn = self.conf["param_path"]+"/"+self.conf["normalization_monitor"]+".txt"
            monitor_data = load_neutron_data(fn_list,txt_fn,self.conf["normalization_monitor"],
                                                first_flight_distance_BL16)
            monitor_data = self.get_monitor_wave(monitor_data,self.conf["wavemin"],self.conf['wavemax'])

            neutron_data = self.normalization_by_wave(neutron_data,monitor_data,"dspacing")

        return neutron_data

    def cal_sample_property(self):
        with open(self.conf["nist_fn"],'r') as jf:
            nist_conf = json.load(jf)
        task = CalSampleProperty(nist_conf,self.conf)
        task.cal_all()
        samDict = {}
        attrs = ["atten_xs","scatt_xs","coh_xs","inc_xs","b_avg_sqrd",
                    "b_sqrd_avg","density_num","atom_num","v_factor","radius"]
        for item in attrs:
            samDict[item] = getattr(task,item)
        self.conf["sample_property"] = samDict

    def cal_sq_module(self):
        check_dir(self.conf["save_path"])
        suffix = "_d.dat"
        if self.conf["hold_run_mode"]=="dat":
            fn = self.conf["hold_fn"]+"/hold_"+self.conf["hold_run"]+"_"+self.bankname+suffix
            x,y,e = np.loadtxt(fn,unpack=True)
            y_hold,e_hold = rebin(x,y,e,self.xnew)
        else:
            hold_dataset = self.process_detector(self.conf["hold_fn"],False)
            runno = self.conf["hold_run"][0]
            fn = self.conf["save_path"]+"/hold_"+runno+"_"+self.bankname+suffix
            y_hold = hold_dataset["histogram"].values[0]
            e_hold = hold_dataset["error"].values[0]
            write_ascii(fn,self.xnew,y_hold,e_hold)

        if self.conf["v_run_mode"]=="dat":
            fn = self.conf["v_fn"]+"/v_"+self.conf["v_run"]+"_"+self.bankname+suffix
            x,y,e = np.loadtxt(fn,unpack=True)
            y_v,e_v = rebin(x,y,e,self.xnew)
        else:
            v_dataset = self.process_detector(self.conf["v_fn"],True)
            runno = self.conf["v_run"][0]
            fn = self.conf["save_path"]+"/v_"+runno+"_"+self.bankname+suffix
            y_v = v_dataset["histogram"].values[0]
            e_v = v_dataset["error"].values[0]
            write_ascii(fn,self.xnew,y_v,e_v)

        if self.conf["scale_v_hold"]>0:
            y_v = y_v - self.conf["scale_v_hold"]*y_hold

        sam_dataset = self.process_detector(self.conf["sam_fn"],False)
        y_sam = sam_dataset["histogram"].values[0]
        e_sam = sam_dataset["error"].values[0]
        x_sam = sam_dataset["xvalue"].values[0]

        y_sam = y_sam-self.conf["scale_sam_hold"]*y_hold
        e_sam = np.sqrt(e_sam**2+(self.conf["scale_sam_hold"]*e_hold)**2)
        y_sam = y_sam/y_v

        pixel = sam_dataset["positions"].coords["pixel"].values
        pos = sam_dataset["positions"].values
        #print(pixel,pos)
        neutron_data = create_dataset(y_sam,e_sam,x_sam,
                    pixel,pos,
                    sam_dataset['proton_charge'],sam_dataset['l1'])

        neutron_data = units_convert_neutron_data(neutron_data,"dspacing","q")

        factor = self.conf["sample_property"]["v_factor"]/self.conf["sample_property"]["atom_num"]
        bsqa = self.conf["sample_property"]["b_sqrd_avg"]
        basq = self.conf["sample_property"]["b_avg_sqrd"]
        laue = bsqa/basq
        x,y,e = neutron_data["xvalue"].values[0],neutron_data["histogram"].values[0],neutron_data["error"].values[0]
        y = y*factor
        y = y*(1/basq)-laue+1
        ave = np.mean(y[-20:])
        y = y / ave
        runno = self.conf["sam_run"][0]

        fn = self.conf["save_path"]+"/sam_"+runno+"_"+self.detector+"_sq.txt"
        write_ascii(fn,x,y,e)
        return x,y,e

    def stitch_modules(self):
        data_pairs = []
        output = "stitch"
        for module in self.conf["stitch_modules"]:
            fn = self.conf["save_path"]+"/sam_"+self.conf["sam_run"][0]+"_"+module+"_sq.txt"
            x,y,e = np.loadtxt(fn,unpack=True)
            data_pairs.append((x,y,e))

        x,y,e = merge_all_curves(data_pairs,self.conf["overlap"])
        ave = np.mean(y[-20:])
        y = y / ave
        fn = self.conf["save_path"]+"/"+output+"_sq.dat"
        write_ascii(fn,x,y,e)
        return x,y,e

    def PDF(self,q,sq,sq_e):
        newX = generate_x(self.conf["q_rebin"][0],
                    self.conf["q_rebin"][1],
                    self.conf["q_rebin"][2],"uniform")
        newY,newE = interpolate(q,sq,sq_e,newX)
        r = generate_x(self.conf["r_rebin"][0],
                    self.conf["r_rebin"][1],
                    self.conf["r_rebin"][2],
                    "uniform")
        data = cal_PDF(r, newX, newY, self.conf["PDF_type"], rho0=self.conf["sample_property"]["density_num"],
                       lorch=self.conf["lorch"])
        return r, data
