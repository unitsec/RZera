import numpy as np

def read_cal(fn):
    data = {}
    data["offset_list"],data["mask_list"] = np.loadtxt(fn,usecols=(2,3),unpack=True)
    return data
