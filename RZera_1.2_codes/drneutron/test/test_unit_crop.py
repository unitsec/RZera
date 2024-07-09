from dataSvc.data_load import load_neutron_data
from algSvc.neutron import (mask_neutron_data,offset_neutron_data,
                crop_neutron_data,focus_neutron_data,
                units_convert_neutron_data)
from utils.constants import *

import matplotlib.pyplot as plt
import time
# 使用示例

import time
#be = time.time()
name = "module10503"
isMonitor=False
#name = 'monitor01'
#isMonitor=True
hdf_file_path = ['/Users/kobude/RUN0020851/detector.nxs']
txt_file_path = '/Users/kobude/gitlab/redonline/BL16/pidInfo/'+name+'.txt'
neutron_data = load_neutron_data(hdf_file_path,txt_file_path,name,30)

be = time.time()
new_dataset = units_convert_neutron_data(neutron_data,"tof","wavelength",isMonitor)
print("after tof to wave: ",new_dataset["xvalue"].values)
new_dataset = crop_neutron_data(new_dataset,0.1,4.5)
print(time.time()-be," seconds for convertunits")
print("=========new_dataset for convert to wavelegnth========")
#neutron_data.coords["xaxis"].rename({"time_of_flight":"dspcing"})

new_dataset = units_convert_neutron_data(new_dataset,"wavelength",'dspacing',isMonitor)
print(new_dataset)
new_dataset = focus_neutron_data(new_dataset)

plt.plot(new_dataset["xvalue"].values,new_dataset["histogram"].values)
plt.show()
