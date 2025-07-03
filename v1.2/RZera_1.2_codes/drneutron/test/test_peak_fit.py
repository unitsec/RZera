from dataSvc.data_load import load_neutron_data
from algSvc.neutron import (mask_neutron_data,offset_neutron_data,
                crop_neutron_data,focus_neutron_data,
                units_convert_neutron_data)
from algSvc.neutron.pixel_offset_nd import PixelOffsetCalNeutronData
from utils.constants import *
from dataSvc.write_format import write_cal
import matplotlib.pyplot as plt
import time
# 使用示例
import sys

import time

name = "module10503"
isMonitor=False
#name = 'monitor01'
#isMonitor=True
hdf_file_path = ['/Users/kobude/RUN0020851/detector.nxs']
txt_file_path = '/Users/kobude/paramsData/BL16/pidInfo/'+name+'.txt'
save_path = "/Users/kobude/paramsData/BL16/offsetFile_RT_202310"
neutron_data = load_neutron_data(hdf_file_path,txt_file_path,name,30)
print(neutron_data)
print(neutron_data.attrs["name"])
#sys.exit()
new_dataset = units_convert_neutron_data(neutron_data,"tof","wavelength",isMonitor)
new_dataset = crop_neutron_data(new_dataset,0.1,4.5)
new_dataset = units_convert_neutron_data(new_dataset,"wavelength",'dspacing',isMonitor)
be = time.time()
task = PixelOffsetCalNeutronData(new_dataset,save_path)
task.fit_one_peak(1.9202)
print("finish time ",time.time()-be)
#plt.plot(new_dataset["xvalue"].values,new_dataset["histogram"].values)
#plt.show()
