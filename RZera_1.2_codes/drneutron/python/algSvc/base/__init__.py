from drneutron.python.utils.helper import getRZeraLib,changePoint2Boundry,check_boundaries
from scipy.signal import savgol_filter
import math
from scipy.interpolate import interp1d
import numpy as np
import ctypes
from ctypes import c_double, c_size_t, POINTER


def rebin_2D(x_old, y_old, e_old, x_new):
    rzlib = getRZeraLib()
    rebin_2D = rzlib.rebin_2D
    rebin_2D.argtypes = [
        c_size_t,                    # rows
        c_size_t,                    # old_cols
        POINTER(POINTER(c_double)),  # x_old
        POINTER(POINTER(c_double)),  # y_old
        POINTER(POINTER(c_double)),  # e_old
        c_size_t,                    # new_cols
        POINTER(c_double),           # x_new
        POINTER(POINTER(c_double)),  # y_new
        POINTER(POINTER(c_double))   # e_new
    ]

    rows = len(y_old)
    old_cols = len(x_old[0])
    new_cols = len(x_new)
    # Create the ctypes arrays for x_old, y_old, and e_old
    x_old_ptrs = (POINTER(c_double) * rows)(*[ctypes.cast((c_double * old_cols)(*row), POINTER(c_double)) for row in x_old])
    y_old_ptrs = (POINTER(c_double) * rows)(*[ctypes.cast((c_double * old_cols)(*row), POINTER(c_double)) for row in y_old])
    e_old_ptrs = (POINTER(c_double) * rows)(*[ctypes.cast((c_double * old_cols)(*row), POINTER(c_double)) for row in e_old])

    # Create the ctypes arrays for y_new and e_new
    y_new_ptrs = (POINTER(c_double) * rows)()
    e_new_ptrs = (POINTER(c_double) * rows)()
    for i in range(rows):
        y_new_ptrs[i] = (c_double * new_cols)()
        e_new_ptrs[i] = (c_double * new_cols)()

    x_new_array = (c_double * new_cols)(*x_new)

    rebin_2D(
        c_size_t(rows),
        c_size_t(old_cols),
        x_old_ptrs,
        y_old_ptrs,
        e_old_ptrs,
        c_size_t(new_cols),
        x_new_array,
        y_new_ptrs,
        e_new_ptrs
    )

    y_new = np.array([np.ctypeslib.as_array(ptr, shape=(new_cols,)) for ptr in y_new_ptrs])
    e_new = np.array([np.ctypeslib.as_array(ptr, shape=(new_cols,)) for ptr in e_new_ptrs])
    x = np.tile(x_new,(rows,1))
    return x, y_new, e_new


def rebin(x_old,y_old,e_old,x_new):
    x_old_boundry = changePoint2Boundry(x_old)
    input_size = len(x_old_boundry)
    input_x = (c_double * input_size)(*x_old_boundry)
    input_y = (c_double * (input_size-1))(*y_old)
    input_e = (c_double * (input_size-1))(*e_old)
    x_new_boundry = changePoint2Boundry(x_new)
    output_size = len(x_new_boundry)
    output_x = (c_double * output_size)(*x_new_boundry)
    output_y =  (c_double * (output_size-1))()
    output_e =  (c_double * (output_size-1))()
    rzlib = getRZeraLib()
    rzlib.rebin(c_size_t(input_size),input_x,input_y,input_e,
                c_size_t(output_size),output_x,output_y,output_e)

    return np.array(output_y),np.sqrt(np.array(output_e))

def strip_peaks(x,y,peaks_dict):
    left = peaks_dict["left"]
    right = peaks_dict["right"]
    data = y.copy()
    for peak in peaks_dict["peaks"]:
        index = np.argmin(np.abs(x - peak))
        x0,y0 = x[index-left],y[index-left]
        x1,y1 = x[index+right],y[index+right]
        m = (y1 - y0) / (x1 - x0)
        b = y0 - m * x0
        x_interp = x[index-left:index+right+1]
        y_interp = m * x_interp + b
        data[index-left:index+right+1] = y_interp
    return data


def smooth(data,npoint,order):
    return savgol_filter(data, window_length=npoint, polyorder=order)

def interpolate(x_old,y_old,e_old,x_new):
    check_boundaries(x_old,x_new[0])
    check_boundaries(x_old,x_new[1])
    f = interp1d(x_old, y_old, kind='linear')  # kind 参数可以是 'linear', 'cubic', 'quadratic', 等

    y_new = f(x_new)
    y_new_err = []
    for x in x_new:
        idx = np.searchsorted(x_old, x) - 1
        x0, x1 = x_old[idx], x_old[idx + 1]
        y0_err, y1_err = e_old[idx], e_old[idx + 1]
        w0 = (x1 - x) / (x1 - x0)
        w1 = (x - x0) / (x1 - x0)
        y_err_interp = np.sqrt((w0 * y0_err) ** 2 + (w1 * y1_err) ** 2)
        y_new_err.append(y_err_interp)

    e_new = np.array(y_new_err)
    return y_new,e_new


def merge(x1, y1, e1,x2, y2,e2, start, end):
    idx1_start = check_boundaries(x1, start)
    idx1_end = check_boundaries(x1, end)
    idx2_start = check_boundaries(x2, start)
    idx2_end = check_boundaries(x2, end)

    y1_ave = np.mean(y1[idx1_start:idx1_end])
    y2_ave = np.mean(y2[idx2_start:idx2_end])

    factor = y1_ave / y2_ave
    y2_new = y2 * factor
    e2_new = e2 * factor

    xfinal = np.concatenate((x1[:idx1_start], x2[idx2_start:]))
    yfinal = np.concatenate((y1[:idx1_start], y2_new[idx2_start:]))
    efinal = np.concatenate((e1[:idx1_start], e2_new[idx2_start:]))
    return xfinal, yfinal, efinal

def merge_all_curves(data_pairs, start_end_pairs):

    x_merged, y_merged, e_merged = data_pairs[0]
    for i in range(1, len(data_pairs)):
        x2, y2, e2 = data_pairs[i]
        start, end = start_end_pairs[i-1]
        x_merged, y_merged, e_merged = merge(x_merged, y_merged, e_merged, x2, y2, e2,start, end)
    return x_merged, y_merged, e_merged

def generate_x(start,stop,num,mode):
    if mode == 'log_10':
        start_exp = math.log(start,10)
        stop_exp = math.log(stop,10)
        return np.logspace(start=start_exp,stop=stop_exp,num=num,base=10)
    elif mode == 'log_e':
        start_exp = math.log(start, np.e)
        stop_exp = math.log(stop, np.e)
        return np.logspace(start=start_exp, stop=stop_exp, num=num, base=np.e)
    else:
        return np.linspace(start,stop,num)

def cal_PDF(r, q, sq,PDF_type,rho0=1,lorch=True):
    dq = q[1]-q[0]
    qcut = q.max()
    mat = np.sin(np.outer(r,  q))
    qiq = (sq - 1.0) * q * dq
    if lorch:
        factor = np.sin(np.pi*q / qcut)/(np.pi * q / qcut)
        qiq = qiq * factor
    integral = np.inner(mat, qiq)

    if PDF_type=="G_r":
        return integral
    if PDF_type=="gr":
        return integral/(4*np.pi*r*rho0)+1
    if PDF_type=="RDF":
        return r*integral+4*np.pi*rho0*r**2
