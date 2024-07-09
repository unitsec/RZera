from algSvc.instrument.diffraction import CSNS_Diffraction
import matplotlib.pyplot as plt
import time
import numpy as np
# 使用示例"/User/kobude/"
params_configure={
                "mode": "offline",
                "save_path": "/Users/kobude",
                "param_path": "/Users/kobude/paramsData/BL16/pidInfo",
                "cal_path": "/Users/kobude/offsetFile_RT_202310",
                "has_cal": True,
                "is_batch": False,
                "sam_fn": [
                    "/Users/kobude/RUN0020851/detector.nxs"
                ],
                "hold_fn": [
                    "/Users/kobude/RUN0020838/detector.nxs"
                ],
                "v_fn": [
                    "/Users/kobude/RUN0020850/detector.nxs"
                ],
                "sam_run": [
                    "RUN0020851"
                ],
                "hold_run": [
                    "RUN0020838"
                ],
                "v_run": [
                    "RUN0020850"
                ],
                "wavemin": 0.1,
                "wavemax": 4.5,
                "useV": True,
                "useHold": True,
                "normByPC": True,
                "scale_sam": 0.5,
                "scale_v": 0.5,
                "T0offset": -3.97,
                "bank_name": [
                    "bank4"
                ],
                "rebin_mode": "uniform",
                "d_rebin": {
                    "bank2": [0.26,15,3000],
                    "bank3": [0.23,8,3000],
                    "bank4": [
                        0.12,
                        5.0,
                        1600
                    ],
                    "bank5": [0.09,3.3,1600],
                    "bank6": [0.07,2.5,2400],
                    "bank7": [0.06,2.2,2600]}
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
                "radius":0.4
        },
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
        "focus_point": {
                    "bank7": {"factor": 15630.28,"pixel":107030270,"2_theta":163},
                    "bank6": {"factor": 14460.68,"pixel":106030450,"2_theta":133},
                    "bank5": {"factor": 11385.43,"pixel":105030450,"2_theta":93},
                    "bank4": {"factor": 7799.17,"pixel":104030450,"2_theta":59},
                    "bank3": {"factor": 5006.04,"pixel":103030450,"2_theta":36},
                    "bank2": {"factor": 2139.82,"pixel":102030450,"2_theta":15}
                    }
}


be = time.time()
configure = {**params_configure,**bl16_configure}
#print(configure)
bl16 = CSNS_Diffraction(configure)

for bank in ["bank2"]:#"bank5","bank3","bank4","bank5","bank6","bank7"]:
    x,y,e = bl16.reduction(bank)
    plt.plot(x,y,label=bank)
# print(time.time()-be," seconds for convert2d")
plt.legend()
plt.show()
