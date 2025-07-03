import numpy as np
from ctypes import *
import os,sys
import platform


def getRZeraLib():
    if getattr(sys, 'frozen', False):
        base_path = getattr(sys, '_MEIPASS')
        if platform.system() == 'Windows':
            dll_path = os.path.join(base_path, "libRZ.dll")
        elif platform.system() == 'Darwin':
            dll_path = os.path.join(base_path, "libRZ-x86_64.so")
        elif platform.system() == 'Linux':
            dll_path = os.path.join(base_path, "libRZ.so")
        else:
            raise OSError("Unsupported operating system")
    else:
        base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        if platform.system() == 'Windows':
            dll_path = os.path.join(base_path, "bin", "libRZ.dll")
        elif platform.system() == 'Darwin':
            dll_path = os.path.join(base_path, "bin", "libRZ-x86_64.so")
        elif platform.system() == 'Linux':
            dll_path = os.path.join(base_path, "bin", "libRZ.so")
        else:
            raise OSError("Unsupported operating system")

    rzlib = CDLL(dll_path, winmode=0)
    return rzlib

def get_l_theta(l1,x,y,z,isMonitor):
    #theta is half of scattering angle
    l2 = np.sqrt(x**2+y**2+z**2)
    if isMonitor:
        l = l1-l2
    else:
        l = l1+l2
    theta = 0.5*np.arccos(z/l2)
    return l, theta

def check_dir(path):
    if os.path.exists(path):
        pass
    else:
        os.makedirs(path)#create path

def check_file(filepath):
    if os.path.isfile(filepath):
        return True
    else:
        return False

def replace_value(arr, nan_value=0.0, inf_neg=None, inf_pos=None):
    arr = np.nan_to_num(arr,nan=nan_value)
    if inf_neg is None:
        arr[np.isneginf(arr)] = np.min(arr[np.isfinite(arr)])
    else:
        arr[np.isneginf(arr)] = inf_neg
    if inf_pos is None:
        arr[np.isposinf(arr)] = np.max(arr[np.isfinite(arr)])
    else:
        arr[np.isposinf(arr)] = inf_pos
    return arr

def check_boundaries(x, value):
    idx = np.searchsorted(x, value)
    if idx == 0 or idx == len(x) or x[idx-1] > value or x[idx] < value:
        raise ValueError(f"The value {value} is not within the bounds")
    return idx

def check_zeros(x_data,y_data,name):
    zero_indices = [index for index, value in enumerate(y_data) if value <= 0]
    if not zero_indices:
        return True
    if zero_indices[0] == 0:
        start_zeros = sum(1 for i in zero_indices if i == zero_indices[0] + len(zero_indices[:zero_indices.index(i)]))
    else:
        start_zeros = 0
    if zero_indices[-1] == len(y_data) - 1:
        end_zeros = sum(1 for i in zero_indices[::-1] if i == zero_indices[-1] - len(zero_indices[:zero_indices.index(i) + 1:-1]))
    else:
        end_zeros = 0
    if 0 in y_data[start_zeros:-end_zeros if end_zeros > 0 else None]:
        raise RuntimeError(f"please reset scale factor for {name}")
    if start_zeros > 0:
        new_start = x_data[start_zeros]
        raise RuntimeError(f"please reset x-range start with: {new_start} for {name}")
    if end_zeros > 0:
        new_end = x_data[-(end_zeros+1)]
        raise RuntimeError(f"please reset x-range end with: {new_end} for {name}")

def checkBytes2Float(value):
    if isinstance(value, np.ndarray):
        if value.dtype.type is np.bytes_:
            value = value.astype(str)
        value = value.item(0)
    elif isinstance(value, (list, tuple)) and len(value) > 0:
        value = value[0]
    if isinstance(value, bytes):
        value = value.decode('utf-8')
    return float(value)

def changePoint2Boundry(arr):
    step = arr[1]-arr[0]
    data = arr-0.5*step
    return np.append(data,data[-1]+step)

def changeBoundry2Point(arr):
    step = arr[1]-arr[0]
    data = arr+0.5*step
    return data[:-1]
