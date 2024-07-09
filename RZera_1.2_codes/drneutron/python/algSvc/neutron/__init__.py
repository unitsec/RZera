import numpy as np
from drneutron.python.dataSvc.data_load import create_dataset
from drneutron.python.utils.helper import get_l_theta
from drneutron.python.algSvc.base.unit_convert import UnitConverter
from drneutron.python.algSvc.base import rebin,rebin_2D

def units_convert_neutron_data(dataset,unit_in,unit_out,isMonitor=False):
    pos = dataset["positions"].values
    l,theta =get_l_theta(dataset["l1"].values,pos[:,0],
                        pos[:,1],pos[:,2],isMonitor)
    xold = dataset["xvalue"].values
    method_name = f"{unit_in}_to_{unit_out}"
    x_new = np.zeros([xold.shape[0],xold.shape[1]])
    for k in range(xold.shape[0]):
        cvtUnit=UnitConverter(l[k],theta[k])
        method = getattr(cvtUnit, method_name)
        x_new[k,:] = method(xold[k,:])
    dims = dataset["xvalue"].dims
    new_dims = ["pixel",unit_out]

    if x_new[0,0]>x_new[0,-1]:
        x_new = x_new[:,::-1]
        y = dataset["histogram"].values
        y_new = y[:,::-1]
        dataset["histogram"].values = y_new
        e = dataset["error"].values
        e_new = e[:,::-1]
        dataset["error"].values = e_new

    dataset["xvalue"].values = x_new
    dataset = dataset.rename({old:new for old,new in zip(dims,new_dims) if old != new})
    dataset["xvalue"].attrs.update({"units":cvtUnit.units[unit_out]})
    return dataset

def rebin_neutron_data(dataset,x_new):
    xarr = dataset["xvalue"].values
    yarr = dataset["histogram"].values
    earr = dataset["error"].values

    xnew,ynew,enew = rebin_2D(xarr,yarr,earr,x_new)
    pos = dataset["positions"].values
    pixel = dataset['positions'].coords['pixel'].values
    data = create_dataset(ynew,enew,xnew,pixel,pos,
                        dataset['proton_charge'],dataset['l1'])
    return data

def mask_neutron_data(dataset,mask_list):
    dataset["histogram"].values[mask_list==0,:] = 0
    return dataset

def offset_neutron_data(dataset,offset_list):
    x = dataset["xvalue"].values
    dataset["xvalue"] = (dataset["xvalue"].dims,dataset["xvalue"].values*(offset_list[:,np.newaxis]+1))
    return dataset

def crop_neutron_data(dataset,xmin,xmax):
    xarr = dataset["xvalue"].values
    for i in range(xarr.shape[0]):
        xtmp = xarr[i,:]
        idxlist = np.where((xtmp<xmin)|(xtmp>xmax))[0]
    dataset["histogram"].values[:,idxlist]= 0
    dataset["error"].values[:,idxlist] = 0
    return dataset

def focus_neutron_data(dataset,pixel_index=None):
    if dataset["histogram"].values.ndim != 2:
        raise ValueError("input data histogram must be 2D")
    if pixel_index is None:
        pixel_index = dataset['positions'].coords['pixel'].values.size//2
    xnew = dataset['xvalue'].values[pixel_index,:]
    pos = dataset["positions"].values[pixel_index]
    pixel = dataset['positions'].coords['pixel'].values[pixel_index]
    ds_data = np.zeros(xnew.size)
    xarr = dataset["xvalue"].values
    for i in range(dataset["histogram"].values.shape[0]):
        xtmp = dataset['xvalue'].values[i,:]
        ynew,_ = np.histogram(xtmp,
                            weights=dataset['histogram'].values[i,:],
                            bins=xnew.size,range=(xnew[0],xnew[-1]))
        ds_data+=ynew
    if ds_data.sum() < 100:
        ds_data = np.zeros(xnew.size)
        ds_error = np.zeros(xnew.size)
        ds_xvalue = xnew.copy()
    else:
        non_zero_idxlist = ds_data != 0
        ds_data = ds_data[non_zero_idxlist]
        ds_error = np.sqrt(ds_data)
        ds_xvalue = xnew[non_zero_idxlist]
    data = create_dataset(ds_data,ds_error,ds_xvalue,pixel,pos,
                        dataset['proton_charge'],dataset['l1'])
    return data

def divide_dataset(dataset_left,dataset_right):
    yleft = dataset_left["histogram"].values
    yright = dataset_right["histogram"].values
    eleft = dataset_left["error"].values
    eright = dataset_right["error"].values
    #eleft = dataset_left["error"].values
    xleft = dataset_left["xvalue"].values
    xright = dataset_right["xvalue"].values
    xnew = dataset_left["xvalue"].values[0]
    datanew = np.zeros((yleft.shape[0],xnew.size))
    errnew = np.zeros((datanew.shape))
    xarrnew = np.zeros((datanew.shape))
    for i in range(xleft.shape[0]):
        xold = xright[i,:]
        yold = yright[i,:]
        eold = eright[i,:]
        #xnew = xright[i,:]
        ynew,enew = rebin(xold,yold,eold,xnew)
        tmp = yleft/ynew
        datanew[i,:]=tmp
        xarrnew[i,:]=xnew
        errnew[i,:]=tmp*np.sqrt((enew/ynew)**2+(eleft/yleft)**2)

    pos = dataset_left["positions"].values
    pixel = dataset_left['positions'].coords['pixel'].values
    dataset = create_dataset(datanew,errnew,xarrnew,pixel,pos,
                    dataset_left['proton_charge'],dataset_left['l1'])

    return dataset
