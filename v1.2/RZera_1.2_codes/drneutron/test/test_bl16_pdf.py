from algSvc.instrument.diffraction import CSNS_PDF
import matplotlib.pyplot as plt
import time
import numpy as np
#from algSvc.base import merge
from algSvc.base import (rebin,merge,generate_x)
from scipy.interpolate import interp1d
# 使用示例"/User/kobude/"
params_configure={
                "mode": "offline",
                "save_path": "/Users/kobude/mpitest",
                "param_path": "/Users/kobude/paramsData/BL16/pidInfo",
                "nist_fn":"/Users/kobude/paramsData/BL16/elementInfo.json",
                "cal_path": "/Users/kobude/offsetFile_RT_202310",
                "has_cal": True,
                "sample_info": {
                    "sample_name":"Si:1-O:2",
                    "mass":0.5166,#g
                    "shape":"cylinder",
                    "height":3.0,#cm
                    "radius":0.446,#cm
                    "beam_height":3.0,#cm
                },
                #"is_batch": True,
                #"time_slice":False,
                "sam_fn": [
                    "/Users/kobude/RUN0020851/detector.nxs"
                ],
                "hold_fn": ["/Users/kobude/RUN0020838/detector.nxs"],
                "hold_run_mode":"nxs",
                "v_fn":["/Users/kobude/RUN0020850/detector.nxs"],
                "v_run_mode":"nxs",
                "sam_run": [
                    "RUN0020851"
                ],
                "hold_run":["RUN0020838"],
                "v_run":["RUN0020850"],
                "wavemin": 0.1,
                "wavemax": 4.5,
                "scale_sam_hold": 0.1,
                "scale_v_hold": 0.5,
                "scale_sam_bg":0,
                "scale_v_bg":0,
                "T0offset": -3.97,
                "q_rebin":[0.8,50,5000],
                "stitch_modules":["module10203","module10403","module10603"],
                "overlap":[(1.5,1.8),(3.0,3.1)],
                "r_rebin":[1.0,20,500]
}

bl16_configure={
        "beamline_name":"MPI",
        "normalization_monitor":"monitor01",
        "bank_group":{
            "bank2":[10203,11303],
            "bank3":[10303,10304,11203,11204],
            "bank4":[10403,10404,10405,11104,11105],
            #"bank4":[10403,10404,10405,11105],#202201cycle
            "bank5":[10503,10504,10505,11003,11004,11005],
            "bank6":[10602,10603,10902,10903],
            "bank7":[10701,10702,10703,10704,10801,10802,10803,10804]
            },
        "v_correct":{
                "atten_xs":2.8,
                "scatt_xs":5.1,
                "density_num":0.0721,
                "radius":0.4,
                "beam_height":3
        },
        "multiply_factor_fullprof":4,
        "v_peaks":{
        "bank7":{"peaks":[0.491458, 0.553213, 0.593559, 0.618261, 0.645433,
                        0.713775, 0.7568, 0.809288, 0.874336, 0.957499,
                        1.070304, 1.235806, 1.51329,2.1396],
                        "left":7,"right":11},
        "bank6":{"peaks":[0.617991, 0.64534,
                0.713206, 0.756761, 0.809433, 0.87426,
                0.958333, 1.070767, 1.235873, 1.513414,2.1385],
                "left":9,"right":11},
        "bank5":{"peaks":[0.712326, 0.754484, 0.808687, 0.874934, 0.955235,1.067655,
                    1.234278, 1.513321, 2.137655],
                        "left":11,"right":11},
        "bank4":{"peaks":[0.809731, 0.959275, 1.072195,1.236998,
                    1.514722,2.137311],
                "left":13,"right":11},
        "bank3":{"peaks":[1.232831, 1.516578,2.138489],
                        "left":20,"right":20},
        "bank2":{"peaks":[2.138489],
                        "left":20,"right":20},
        },
        # "focus_point": {
        #             "bank7": {"factor": 15630.28,"pixel":107030270,"2_theta":163},
        #             "bank6": {"factor": 14460.68,"pixel":106030450,"2_theta":133},
        #             "bank5": {"factor": 11385.43,"pixel":105030450,"2_theta":93},
        #             "bank4": {"factor": 7799.17,"pixel":104030450,"2_theta":59},
        #             "bank3": {"factor": 5006.04,"pixel":103030450,"2_theta":36},
        #             "bank2": {"factor": 2139.82,"pixel":102030450,"2_theta":15}
        #             },
        "d_rebin": {
            "bank2": [0.26,15,3000],
            "bank3": [0.23,8,3000],
            "bank4": [0.12,5.0,1600],
            "bank5": [0.09,3.3,1600],
            "bank6": [0.07,2.5,2400],
            "bank7": [0.06,2.2,2600]},
        "bank_match":{
        "module10203":"bank2",
        "module11303":"bank2",
        "module10303":"bank3",
        "module10304":"bank3",
        "module11203":"bank3",
        "module11204":"bank3",
        "module10403":"bank4",
        "module10404":"bank4",
        "module10405":"bank4",
        "module11104":"bank4",
        "module11105":"bank4",
        "module10503":"bank5",
        "module10504":"bank5",
        "module10505":"bank5",
        "module11003":"bank5",
        "module11004":"bank5",
        "module11005":"bank5",
        "module10602":"bank6",
        "module10603":"bank6",
        "module10902":"bank6",
        "module10903":"bank6",
        "module10701":"bank7",
        "module10702":"bank7",
        "module10703":"bank7",
        "module10704":"bank7",
        "module10801":"bank7",
        "module10802":"bank7",
        "module10803":"bank7",
        "module10804":"bank7"
        }
}




moduleList=["module10203","module10403","module10603"]

be = time.time()
configure = {**params_configure,**bl16_configure}
bl16 = CSNS_PDF(configure)

moduleList = configure["bank_match"].keys()
for module in moduleList:
    x,y,e = bl16.cal_sq_module(module)
    
q,sq = bl16.stitch_modules()
plt.plot(q,sq)
plt.show()
r,pdf = bl16.PDF(q,sq)
plt.plot(r,pdf)
plt.show()
