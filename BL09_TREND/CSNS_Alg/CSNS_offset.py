import traceback
import numpy as np
from rongzai.dataSvc.data_load import load_neutron_data
from rongzai.algSvc.neutron.pixel_offset_nd import PixelOffsetCalNeutronData
from rongzai.utils import generateBank
from rongzai.dataSvc.read_format import read_cal
from rongzai.algSvc.neutron import mask_neutron_data
from rongzai.algSvc.base import rebin, baseline_alg
from rongzai.utils.relation_utils import get_all_from_detector
from rongzai.utils.file_utils import check_dir
from rongzai.utils.array_utils import generate_x
import matplotlib.pyplot as plt
from rongzai.utils.config_utils import generate_offset_conf
from rongzai.utils.defined_functions import linear_func,quadratic_func

class CSNS_Offset(PixelOffsetCalNeutronData):
    def __init__(self,base_json,offset_json,detector,ui=False):
        if ui is True:
            self.conf = {**base_json, **offset_json}
        else:
            self.conf = generate_offset_conf(base_json,offset_json)
        self.is_ui = ui
        self.groupInfo, self.bankInfo, self.pixelInfo = generateBank(self.conf["beamline"])
        self.groupname, self.moduleList = get_all_from_detector(detector, self.groupInfo,
                                                                self.bankInfo)
        self.detector = detector

        params = self.conf["d_rebin"][self.groupname]
        self.xnew = generate_x(params[0], params[1], params[2], self.conf["rebin_mode"])
        check_dir(self.conf["save_path"])

    def get_peaks(self):
        fit_para = self.conf["fit_para"][self.groupname]
        group_para_tof = self.conf["group_para_tof"][self.groupname]
        group_para_d = self.conf["group_para_d"][self.groupname]
        smooth_para = self.conf["smooth_para"][self.groupname]
        d_std = self.conf["d_std"][self.groupname]
        high_width_para = self.conf["high_width_para"][self.groupname]
        for module in self.moduleList:
            print("start: ", module)
            dataset = load_neutron_data(self.conf["sam_fn"], f'{self.conf["param_path"]}/{module}.txt',
                                        module, self.conf["first_flight_distance"])

            if self.pixelInfo[module]["stepbyrow"] == "x":
                pixels = self.pixelInfo[module]["xpixels"]
            else:
                pixels = self.pixelInfo[module]["ypixels"]
            self.get_multiple_peaks( dataset, d_std, high_width_para, fit_function=fit_para["fit_function"],
                                        sub_background=fit_para["sub_background"],
                                        goodness_bottom=fit_para["goodness_bottom"],
                                        is_smooth=smooth_para["is_smooth"], smooth_para=smooth_para["smooth_para"],
                                        least_peaks_num=fit_para["least_peaks_num"],
                                        group_along_tube_d=group_para_d["group_along_tube"],
                                        group_cross_tube_d=group_para_d["group_cross_tube"],
                                        group_along_tube_tof=group_para_tof["group_along_tube"],
                                        group_cross_tube_tof=group_para_tof["group_cross_tube"],
                                        group_mode=self.conf["group_mode"], pixels_per_tube=pixels,
                                        order=fit_para["order"],
                                        check_point=self.conf["check_point"],
                                        anchor_point=self.conf["anchor_point"])
    def calculate_offset(self,is_parallel=True,max_workers=8):
        fit_para = self.conf["fit_para"][self.groupname]
        group_para_tof = self.conf["group_para_tof"][self.groupname]
        group_para_d = self.conf["group_para_d"][self.groupname]
        #group_para = self.conf["group_para"][self.groupname]
        smooth_para =  self.conf["smooth_para"][self.groupname]
        d_std = self.conf["d_std"][self.groupname]
        high_width_para = self.conf["high_width_para"][self.groupname]
        plot_info_all = []
        for module in self.moduleList:
            print("start: ", module)
            dataset = load_neutron_data(self.conf["sam_fn"], f'{self.conf["param_path"]}/{module}.txt',
                                        module, self.conf["first_flight_distance"])

            if self.pixelInfo[module]["stepbyrow"] == "x":
                pixels = self.pixelInfo[module]["xpixels"]
            else:
                pixels = self.pixelInfo[module]["ypixels"]
            if self.conf["mode"] == "check":
                plot_info = self.fit_multiple_peaks(dataset, self.conf["save_path"], d_std, high_width_para,
                                        fit_function=fit_para["fit_function"],
                                        sub_background=fit_para["sub_background"],
                                        goodness_bottom=fit_para["goodness_bottom"],
                                        is_smooth=smooth_para["is_smooth"], smooth_para=smooth_para["smooth_para"],
                                        least_peaks_num=fit_para["least_peaks_num"],
                                        group_along_tube_d=group_para_d["group_along_tube"],
                                        group_cross_tube_d=group_para_d["group_cross_tube"],
                                        group_along_tube_tof=group_para_tof["group_along_tube"],
                                        group_cross_tube_tof=group_para_tof["group_cross_tube"],
                                        pixels_per_tube=pixels,
                                        order=fit_para["order"], mode=self.conf["mode"],
                                        check_point=self.conf["check_point"],
                                        anchor_point=self.conf["anchor_point"], parallel=False, max_workers=max_workers,ui=self.is_ui)
            else:
                plot_info = self.fit_multiple_peaks(dataset, self.conf["save_path"], d_std, high_width_para,
                                    fit_function=fit_para["fit_function"],sub_background = fit_para["sub_background"],
                                    goodness_bottom=fit_para["goodness_bottom"],
                                    is_smooth=smooth_para["is_smooth"], smooth_para=smooth_para["smooth_para"],
                                    least_peaks_num=fit_para["least_peaks_num"],
                                    group_along_tube_d=group_para_d["group_along_tube"],
                                    group_cross_tube_d=group_para_d["group_cross_tube"],
                                    group_along_tube_tof=group_para_tof["group_along_tube"],
                                    group_cross_tube_tof=group_para_tof["group_cross_tube"],
                                    pixels_per_tube=pixels,
                                    order=fit_para["order"], mode=self.conf["mode"], check_point=self.conf["check_point"],
                                    anchor_point=self.conf["anchor_point"],parallel=is_parallel,max_workers=max_workers)
            plot_info_all.append(plot_info)
        return plot_info_all

    def check_modules(self):
        for module in self.moduleList:
            x, y = self.__get_result_module(module)
            plt.plot(x,y,label = module)
            plt.legend()
        plt.show()

    def __get_result_module(self,module):
        data = load_neutron_data(self.conf["sam_fn"], f'{self.conf["param_path"]}/{module}.txt',
                                     module, self.conf["first_flight_distance"])
        cal_fn = self.conf["save_path"] + "/" + module + "_offset.cal"
        cal_dict = read_cal(cal_fn)
        data = self.correct_tof_to_d(data, cal_dict)
        data = mask_neutron_data(data, cal_dict["mask_list"])
        x, y = self.get_I_d(data)
        # e = np.ones(y.size)
        return x,y

    def __get_result_modules(self,modules):
        for i in range(len(modules)):
            x,y = self.__get_result_module(modules[i])
            e = np.ones(y.size)
            if i == 0:
                # print(x.shape,y.shape,self.xnew.shape)
                y_final, _ = rebin(x, y, e, self.xnew)
            else:
                y_tmp, _ = rebin(x, y, e, self.xnew)
                y_final += y_tmp
        background = baseline_alg(y_final, lam=1e5, p=0.01)
        y_final -= background
        if y_final.max()>0:
            y_final/=y_final.max()
        return self.xnew,y_final

    def sum_modules(self):
        return self.__get_result_modules(self.moduleList)

    def get_pixels(self,pixel_range):
        x_list = []
        y_list = []
        for module in self.moduleList:
            data = load_neutron_data(self.conf["sam_fn"], f'{self.conf["param_path"]}/{module}.txt',
                                     module, self.conf["first_flight_distance"])
            cal_fn = self.conf["save_path"] + "/" + module + "_offset.cal"
            cal_dict = read_cal(cal_fn)
            data = self.correct_tof_to_d(data, cal_dict)
            data = mask_neutron_data(data, cal_dict["mask_list"])
            x = data["xvalue"].values[pixel_range[0]:pixel_range[1]]
            y = data["histogram"].values[pixel_range[0]:pixel_range[1]]
            x_list.append(x)
            y_list.append(y)
        return x_list,y_list

class Offset_Plot():

    def plot_check(self, name, x, y, smoothed_y, peak, all_d_peak, all_I_peak, peaks_position):
        fig, ax = plt.subplots()
        ax.plot(x, y, 'g-', label='intensity')
        ax.plot(x, smoothed_y, 'b-', label='smoothed_intensity')
        for i in range(len(peak)):
            ax.plot(peak[i][0], peak[i][1], 'r-', label='Fitted Gaussian')
            ax.plot(all_d_peak[i], all_I_peak[i], 'rx')
        for j in peaks_position:
            ax.axvline(x=j, color='black', linestyle='--', linewidth=1,
                            label='Standard Peak Position' if j == peaks_position[0] else "")
        ax.grid(True)
        ax.set_title(name)
        ax.legend()
        return fig, ax

    def plot_fitted_curve(self, std, exp, offset_para, order):
        fig, ax = plt.subplots()
        C0 = offset_para[0]
        C1 = offset_para[1]
        C2 = offset_para[2]
        if order == 'linear':
            tof_fitted = linear_func(std, C0, C1)
            ax.set_title('Linear Fit: tof = C0 + C1 * d')
        elif order == 'quadratic':
            tof_fitted = quadratic_func(std, C0, C1, C2)
            ax.set_title('Quadratic Fit: tof = C0 + C1 * d + C2 * d^2')
        ax.scatter(std, exp, color='blue', label='Original Data')
        ax.plot(std, tof_fitted, color='red', label='Fitted Curve')
        ax.set_xlabel('d_std')
        ax.set_ylabel('Time-of-Flight (tof_exp)')
        ax.legend()
        ax.grid(True)
        return fig, ax

    def plot_offset_data(self, x, y, smoothed_y, d_offset, peaks_position):
        fig, ax = plt.subplots()
        ax.plot(x, y, 'g-', label='Original Data')
        ax.plot(x, smoothed_y, 'b-', label='Original Data (smoothed)')
        ax.plot(d_offset, smoothed_y, 'r-', label='Offset Data (smoothed)')
        for j in peaks_position:
            ax.axvline(x=j, color='black', linestyle='--', linewidth=1,
                            label='Standard Peak Position' if j == peaks_position[0] else "")
        ax.grid(True)
        ax.legend()
        return fig, ax

    def plot_result_data(self, plot_para, d_std):
        try:
            fig, ax = plt.subplots()
            for i, para in enumerate(plot_para):
                ax.plot(para[1], para[2], label=para[0])
                if len(para) > 3:
                    for j in range(len(para[3][0][:,0])):
                        x = para[3][0][j,:]
                        y = para[4][0][j,:]
                        if np.any(y != 0):
                            y = y / np.max(y)
                        ax.plot(x, y, label= int(para[5][0])+j+1)
            for j in d_std:
                ax.axvline(x=j, linestyle='--', linewidth=1,
                           label='Standard Peak Position' if j == d_std[0] else "")
            ax.grid(True)
            ax.legend()

            return fig, ax
        except:
            traceback.print_exc()


