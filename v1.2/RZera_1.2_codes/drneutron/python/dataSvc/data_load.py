import xarray as xr
import numpy as np
import h5py
from drneutron.python.utils.helper import checkBytes2Float

def assemble_neutron_data(x_data,y_data,e_data,pc,txt_file_path,module,l1,x_offset=0):
    len_y = y_data.shape[1]
    len_x = x_data.size
    if len_x != len_y:
        x_data = x_data[:-1]+(x_data[1]-x_data[0])*0.5
    x_data = np.tile(x_data,(y_data.shape[0],1))
    pixel_ids,positions = get_pixel_positions(txt_file_path)
    neutron_data = create_dataset(y_data,e_data,x_data,pixel_ids,positions,pc,l1,module)
    return neutron_data

def load_neutron_data(hdf_file_list,txt_file_path,module,l1,x_offset=0):
    histogram_data,error_data,x_data,pc = get_data_from_hdf(hdf_file_list,module,x_offset)
    neutron_data = assemble_neutron_data(x_data,histogram_data,error_data,pc,txt_file_path,module,l1,x_offset=0)
    return neutron_data

def get_pixel_positions(txt_file_path):
    data = np.loadtxt(txt_file_path)
    if data.ndim==1:
        pixel_ids = np.expand_dims(data[0].astype(int),axis=0)
        positions = np.expand_dims(data[1:4],axis=0)

    else:
        pixel_ids = data[:, 0].astype(int)
        positions = data[:, 1:4]
    return pixel_ids,positions

def create_dataArray(data, dim_names, coords=None,name=None, units=None):
    if data.ndim == 1:
        dims = (dim_names[0],)
        coords_dict = {dim_names[0]: coords[dim_names[0]]} if coords else None
    elif data.ndim == 2:
        dims = (dim_names[0], dim_names[1])
        coords_dict = {
            dim_names[0]: coords[dim_names[0]],
            dim_names[1]: coords[dim_names[1]]
        } if coords else None
    else:
        print(data)
        raise ValueError("Input data must be 1D or 2D.")

    da = xr.DataArray(data, dims=dims, coords=coords_dict, name=name)
    if units:
        da.attrs['units'] = units
    return da

def create_dataset(hist, error, x, pixel, pos, pc, l1, module=None):
    if hist.ndim == 1:
        hist = np.expand_dims(hist,axis=0)
        error = np.expand_dims(error,axis=0)
        x = np.expand_dims(x,axis=0)
    if pixel.ndim == 0:
        pixel = np.expand_dims(pixel,axis=0)
    if pos.ndim ==1:
        pos = np.expand_dims(pos,axis=0)

    histogram_dataArray = create_dataArray(hist, ['pixel', 'xaxis'],coords=None,
                                        name="histogram", units="counts")
    x_dataArray = create_dataArray(x, ["pixel","xboundry"], coords=None,
                                    name="xvalue", units="us")#['pixel', 'xboundry'], coords=None,

    error_dataArray = create_dataArray(error,['pixel', 'xaxis'],coords=None,
                                        name="error", units=None)
    positions_dataArray = create_dataArray(pos, ['pixel', 'coordinate'],
                                           coords={'pixel': pixel,'coordinate':['x','y','z']},
                                           name="positions", units="meter")
    da_set = xr.Dataset({
        'histogram': histogram_dataArray,
        'error': error_dataArray,
        'xvalue': x_dataArray,
        "positions": positions_dataArray,
        "l1": l1,
        "proton_charge": pc
    })
    da_set.attrs["name"] = module
    return da_set

def get_data_from_hdf(hdf_file_list,module,offset):
    for i in range(len(hdf_file_list)):
        if i == 0:
            with h5py.File(hdf_file_list[i], 'r') as hdf:
                pc = hdf["/csns/proton_charge"][()]
                pc = checkBytes2Float(pc)
                histogram_data = hdf['/csns/instrument/'+module+'/histogram_data'][:]
                tof_data = hdf['/csns/instrument/'+module+'/time_of_flight'][:]+offset
                tof_data = tof_data.flatten()[:-1]+(tof_data[1]-tof_data[0])*0.5
        else:
            with h5py.File(hdf_file_list[i], 'r') as hdf:
                histogram_data += hdf['/csns/instrument/'+module+'/histogram_data'][:]
                pc+= checkBytes2Float(hdf["/csns/proton_charge"][()])
    return histogram_data,np.sqrt(histogram_data),tof_data,pc
