import numpy as np

def write_cal(info_dict):
    combined_data = np.column_stack((info_dict["index"],
                                    info_dict["pixel"],
                                    info_dict["offset"],
                                    info_dict["mask"],
                                    info_dict["group"]))
    formats = ["%d","%d","%.7f","%d","%d"]
    np.savetxt(info_dict["save_file"],combined_data,fmt=formats, comments="#",
                header="Format: number    UDET     offset    select    group")

def write_ascii(fn,*args, format="%.8f"):
    if not args:
        raise ValueError("No data provided to write to the file.")
    length = len(args[0])
    if not all(len(arr) == length for arr in args):
        raise ValueError("All input arrays must have the same length.")
    combined_array = np.column_stack(args)
    np.savetxt(fn, combined_array, fmt=format)
