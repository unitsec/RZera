from drneutron.python.algSvc.neutron import (mask_neutron_data,offset_neutron_data,
                crop_neutron_data,focus_neutron_data,
                units_convert_neutron_data,divide_dataset)
from drneutron.python.algSvc.neutron.abs_ms_nd import AbsMsCorrNeutronData
from drneutron.python.algSvc.base import (strip_peaks,smooth)

class Diffraction():
    def __init__(self):
        self.pc_factor = 1E5

    def time_focusing_sample(self,dataset,wavemin,wavemax,cal_dict):
        data = units_convert_neutron_data(dataset,"tof","wavelength",False)
        data = crop_neutron_data(data,wavemin,wavemax)
        data = units_convert_neutron_data(data,"wavelength","dspacing",False)
        if cal_dict["has_cal"]:
            data = mask_neutron_data(data,cal_dict["mask_list"])
            data = offset_neutron_data(data,cal_dict["offset_list"])
        data = focus_neutron_data(data)
        return data

    def time_focusing_vanadium(self,dataset,wavemin,wavemax,cal_dict,correct_dict):
        data = units_convert_neutron_data(dataset,"tof","wavelength",False)
        data = crop_neutron_data(data,wavemin,wavemax)
        task = AbsMsCorrNeutronData(data)
        data = task.run_carpenter(correct_dict)
        data = units_convert_neutron_data(data,"wavelength","dspacing",isMonitor=False) #dataset
        if cal_dict["has_cal"]:
            data = mask_neutron_data(data,cal_dict["mask_list"])
            data = offset_neutron_data(data,cal_dict["offset_list"])
        data = focus_neutron_data(data)
        return data

    def get_monitor_wave(self,dataset,wavemin,wavemax):
        data = units_convert_neutron_data(dataset,"tof","wavelength",isMonitor=True)
        data = crop_neutron_data(data,wavemin,wavemax)
        data = focus_neutron_data(data)
        return data

    def get_monitor_nc(self,dataset,wavemin,wavemax):
        data = self.get_monitor_wave(dataset,wavemin,wavemax)
        return data["histogram"].values.sum()

    def normalization_by_wave(self,detdataset,mondataset,unit):
        detdata = units_convert_neutron_data(detdataset,unit,"wavelength",isMonitor=False)
        detdata = divide_dataset(detdata,mondataset)
        detdata = units_convert_neutron_data(detdata,"wavelength",unit)
        return detdata
