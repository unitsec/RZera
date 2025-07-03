import numpy as np
from drneutron.python.dataSvc.data_load import create_dataset
from drneutron.python.utils.helper import getRZeraLib,get_l_theta
from ctypes import *

class AbsMsCorrNeutronData():
    def __init__(self,dataset):
        position = dataset["positions"].values
        self.l,self.theta = get_l_theta(dataset["l1"].values,position[:,0],
                            position[:,1],position[:,2],False)
        self.nd = dataset
        self.rzlib = getRZeraLib()

    def run_carpenter(self,conf):
        #print("start carpenter: ",self.nd["xvalue"].values.shape[0])
        new_data = self.nd["histogram"].values.copy()
        err_data = self.nd["error"].values.copy()
        if self.nd["xvalue"].values.ndim == 2:
            for i in range(self.nd["xvalue"].values.shape[0]):

                wave_arr = self.nd["xvalue"].values[i,:]
                input_size = len(wave_arr)
                input_array = (c_double * input_size)(*wave_arr)
                output_abs =  (c_double * input_size)()
                output_ms =  (c_double * input_size)()

                self.rzlib.calculate_abs_correction(
                    c_double(2*self.theta[i]), c_double(conf["radius"]),
                    c_double(conf['atten_xs']), c_double(conf['density_num']),
                    c_double(conf['scatt_xs']),input_array,
                    c_size_t(input_size), output_abs)
                yabs = np.array(output_abs)

                self.rzlib.calculate_ms_correction(
                    c_double(2*self.theta[i]), c_double(conf["radius"]),
                    c_double(conf['atten_xs']), c_double(conf['density_num']),
                    c_double(conf['scatt_xs']),input_array,
                    c_size_t(input_size), output_ms)
                yms = np.array(output_ms)
                new_data[i,:] = self.nd["histogram"].values[i,:]*(1/yabs-yms)
                err_data[i,:] = self.nd["error"].values[i,:]*(1/yabs-yms)
                #new_data[i,:] = self.nd["histogram"].values[i,:]*(1/yabs)
                #err_data[i,:] = self.nd["error"].values[i,:]*(1/yabs)

        dataset = create_dataset(new_data,err_data,self.nd["xvalue"].values,
                                self.nd["positions"].coords["pixel"].values,
                                self.nd["positions"].values,
                                self.nd['proton_charge'],self.nd['l1'])
        return dataset
