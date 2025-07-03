import numpy as np
import re

class CalSampleProperty:
    def __init__(self, nist_conf, conf=None):
        self.samConf = conf["sample_info"]
        self.vConf = conf["v_correct"]
        self.nist = nist_conf
        self.set_params_zero()

    def set_params_zero(self):
        self.atten_xs = 0.0
        self.scatt_xs = 0.0
        self.coh_xs = 0.0
        self.inc_xs = 0.0
        self.b_avg_sqrd = 0.0
        self.b_sqrd_avg = 0.0
        self.density_num = 0.0
        self.atom_num = 0.0
        self.v_factor = 0.0
        self.radius = self.samConf["radius"]

    def cal_beam_volume(self):
        if self.samConf["shape"]=="cylinder":
            height = self.samConf["height"]
            radius = self.samConf["radius"]
            if self.samConf["beam_height"]>height:
                volume = np.pi*radius**2*height
            else:
                volume = np.pi*radius**2*self.samConf['beam_height']
            return volume

    def cal_density(self):
        if self.samConf["shape"]=="cylinder":
            height = self.samConf["height"]
            radius = self.samConf["radius"]
            volume = np.pi*radius**2*height
            return self.samConf["mass"]/volume

    def cal_element_ratio(self):
        sample = self.samConf["sample_name"].split('-')
        data = {}
        numbers = re.findall(r'[-+]?\d*\.\d+|\d+', self.samConf["sample_name"])
        total_sum = sum(float(number) for number in numbers)
        for i in range(len(sample)):
            tmp = sample[i].split(":")
            data[tmp[0]] = float(tmp[1])/total_sum
        return data

    def cal_molar_mass(self):
        ele_ratio = self.cal_element_ratio()
        molar_mass = 0.0
        for key in ele_ratio:
            molar_mass += float(self.nist[key]["molarMass"])*ele_ratio[key]
        return molar_mass

    def cal_v_factor(self):
        r = self.vConf["radius"]
        h = self.vConf["beam_height"]
        volume = np.pi*r**2*h
        return self.vConf["density_num"]*volume/4/np.pi*self.vConf["scatt_xs"]

    def cal_all(self):
        self.set_params_zero()
        ele_ratio = self.cal_element_ratio()
        for key in ele_ratio:
            self.atten_xs += float(self.nist[key]["Abs_xs"])*ele_ratio[key]
            self.scatt_xs += float(self.nist[key]["Scatt_xs"])*ele_ratio[key]
            self.coh_xs += float(self.nist[key]["Coh_xs"])*ele_ratio[key]
            self.inc_xs += float(self.nist[key]["Inc_xs"])*ele_ratio[key]
        self.b_avg_sqrd = self.inc_xs/4./np.pi
        self.b_sqrd_avg = self.coh_xs/4./np.pi
        self.density_num = 0.1*self.cal_density()/self.cal_molar_mass()*6.02
        self.atom_num = self.density_num*self.cal_beam_volume()
        self.v_factor = self.cal_v_factor()
