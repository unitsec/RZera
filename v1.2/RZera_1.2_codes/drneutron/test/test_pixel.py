from dataSvc.data_load import get_pixel_positions
from utils.helper import get_l_theta
import time
import numpy as np
# 使用示例
name="module10203"
txt_file_path = '/Users/kobude/gitlab/redonline/BL16/pidInfo/'+name+'.txt'

pixel,pos = get_pixel_positions(txt_file_path)
l,theta = get_l_theta(30,pos[:,0],pos[:,1],pos[:,2],False)
data = np.zeros(pixel.size)
idx = pixel.size//2+49
for i in range(pixel.size):
    data[i] = l[i]*np.sin(theta[i])*505.4
print(data[idx],180/np.pi*2*theta[idx],pixel[idx])

#calculate bl16 focus point
bank_factor = {
            "bank7":{"factor": 15630.28,"pixel":107030270,"2_theta":163},
            "bank6": {"factor": 14460.68,"pixel":106030450,"2_theta":133},
            "bank5": {"factor": 11385.43,"pixel":105030450,"2_theta":93},
            "bank4": {"factor": 7799.17,"pixel":104030450,"2_theta":59},
            "bank3": {"factor": 5006.04,"pixel":103030450,"2_theta":36},
            "bank2": {"factor": 2139.82,"pixel":102030450,"2_theta":15}
            }
