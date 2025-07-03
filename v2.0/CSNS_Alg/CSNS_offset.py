import sys
import traceback
import numpy as np
from matplotlib.ticker import ScalarFormatter
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
from rongzai.algSvc.base import (auto_extract_peak_data,smooth,fit_gaussian,
                         rebin,baseline_alg,goodness_of_fit,get_l_theta)
from rongzai.utils.constants import *
from rongzai.dataSvc.data_creator import *
import math
class CSNS_Offset(PixelOffsetCalNeutronData):
    def __init__(self,base_json,offset_json,detector,ui=False):
        if ui is True:
            self.conf = {**base_json, **offset_json}
        else:
            self.conf = generate_offset_conf(base_json,offset_json)
        self.is_ui = ui
        #self.groupInfo, self.bankInfo, self.pixelInfo = generateBank(self.conf["beamline"])
        self.groupname,self.moduleList = get_all_from_detector(detector,self.conf["group_info"],self.conf["bank_info"])
        self.pixelInfo = self.conf["pixel_info"]
        #self.groupname, self.moduleList = get_all_from_detector(detector, self.groupInfo,
        #                                                        self.bankInfo)
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
            # print("start: ", module,self.conf["sam_fn"])
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
                                        group_along_tube_d = group_para_d["group_along_tube"],
                                        group_cross_tube_d = group_para_d["group_cross_tube"],
                                        group_along_tube_tof = group_para_tof["group_along_tube"],
                                        group_cross_tube_tof = group_para_tof["group_cross_tube"],
                                        group_mode=self.conf["group_mode"], pixels_per_tube=pixels,
                                        order=fit_para["order"],
                                        check_point=self.conf["check_point"],
                                        anchor_point=self.conf["anchor_point"])

    def calculate_offset(self,is_parallel=True,max_workers=8):
        print(self.conf["fit_para"])
        fit_para = self.conf["fit_para"][self.groupname]
        group_para_tof = self.conf["group_para_tof"][self.groupname]
        group_para_d = self.conf["group_para_d"][self.groupname]
        # group_para = self.conf["group_para"][self.groupname]
        smooth_para =  self.conf["smooth_para"][self.groupname]
        d_std = self.conf["d_std"][self.groupname]
        high_width_para = self.conf["high_width_para"][self.groupname]
        is_c0_0 = self.conf["is_c0_0"]
        plot_info_all = []
        for module in self.moduleList:
            if self.conf.get('LA_offset', False):
                self.exp = []
                self.std = []
                loop_counts = 0
                is_parallel = False
                for fn, tag, tag1 in zip(self.conf['sam_fn'], d_std, high_width_para):
                    dd_std = d_std[f'{tag}']
                    hhigh_width_para = high_width_para[f'{tag1}']
                    print("start: ", module, fn)
                    dataset = load_neutron_data(fn, f'{self.conf["param_path"]}/{module}.txt',
                                                module, self.conf["first_flight_distance"],
                                                x_offset=float(self.conf["T0_offset"]))
                    if self.pixelInfo[module]["stepbyrow"] == "x":
                        pixels = self.pixelInfo[module]["xpixels"]
                    else:
                        pixels = self.pixelInfo[module]["ypixels"]
                    if self.conf["mode"] == "check":
                        plot_info = self.fit_multiple_peaks(dataset, self.conf["save_path"], dd_std, hhigh_width_para,
                                                            fit_function=fit_para["fit_function"],
                                                            sub_background=fit_para["sub_background"],
                                                            is_c0_0=is_c0_0,
                                                            goodness_bottom=fit_para["goodness_bottom"],
                                                            is_smooth=smooth_para["is_smooth"],
                                                            smooth_para=smooth_para["smooth_para"],
                                                            least_peaks_num=fit_para["least_peaks_num"],
                                                            group_along_tube_d=group_para_d["group_along_tube"],
                                                            group_cross_tube_d=group_para_d["group_cross_tube"],
                                                            group_along_tube_tof=group_para_tof["group_along_tube"],
                                                            group_cross_tube_tof=group_para_tof["group_cross_tube"],
                                                            pixels_per_tube=pixels,
                                                            order=fit_para["order"], mode=self.conf["mode"],
                                                            check_point=self.conf["check_point"],
                                                            anchor_point=self.conf["anchor_point"], parallel=False,
                                                            max_workers=max_workers, ui=self.is_ui, LA_offset=self.conf["LA_offset"], loop_counts= loop_counts)
                    else:
                        plot_info = self.fit_multiple_peaks(dataset, self.conf["save_path"], dd_std, hhigh_width_para,
                                                            fit_function=fit_para["fit_function"],
                                                            sub_background=fit_para["sub_background"],
                                                            is_c0_0=is_c0_0,
                                                            goodness_bottom=fit_para["goodness_bottom"],
                                                            is_smooth=smooth_para["is_smooth"],
                                                            smooth_para=smooth_para["smooth_para"],
                                                            least_peaks_num=fit_para["least_peaks_num"],
                                                            group_along_tube_d=group_para_d["group_along_tube"],
                                                            group_cross_tube_d=group_para_d["group_cross_tube"],
                                                            group_along_tube_tof=group_para_tof["group_along_tube"],
                                                            group_cross_tube_tof=group_para_tof["group_cross_tube"],
                                                            pixels_per_tube=pixels,
                                                            order=fit_para["order"], mode=self.conf["mode"],
                                                            check_point=self.conf["check_point"],
                                                            anchor_point=self.conf["anchor_point"],
                                                            parallel=is_parallel, max_workers=max_workers, LA_offset=self.conf["LA_offset"], loop_counts= loop_counts)
                    loop_counts+=1
                plot_info_all.append(plot_info)
#####################  施工中  #######################################
            else:
                print("start: ", module, self.conf["sam_fn"])
                dataset = load_neutron_data(self.conf["sam_fn"], f'{self.conf["param_path"]}/{module}.txt',
                                            module, self.conf["first_flight_distance"], x_offset=float(self.conf["T0_offset"]))
                if self.pixelInfo[module]["stepbyrow"] == "x":
                    pixels = self.pixelInfo[module]["xpixels"]
                else:
                    pixels = self.pixelInfo[module]["ypixels"]
                if self.conf["mode"] == "check":
                    plot_info = self.fit_multiple_peaks(dataset, self.conf["save_path"], d_std, high_width_para,
                                            fit_function=fit_para["fit_function"],
                                            sub_background=fit_para["sub_background"],
                                            is_c0_0 = is_c0_0,
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
                                        is_c0_0=is_c0_0,
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
        if 'LA_offset' in self.conf:
            if self.conf['LA_offset']:
                if self.conf['check_second']:
                    data = load_neutron_data(self.conf["sam_fn"][1], f'{self.conf["param_path"]}/{module}.txt',
                                             module, self.conf["first_flight_distance"])
                else:
                    data = load_neutron_data(self.conf["sam_fn"][0], f'{self.conf["param_path"]}/{module}.txt',
                                             module, self.conf["first_flight_distance"])
            else:
                data = load_neutron_data(self.conf["sam_fn"][0], f'{self.conf["param_path"]}/{module}.txt', module,
                                         self.conf["first_flight_distance"])
        else:
            data = load_neutron_data(self.conf["sam_fn"], f'{self.conf["param_path"]}/{module}.txt', module,
                                     self.conf["first_flight_distance"])
        cal_fn = self.conf["save_path"] + "/" + module + "_offset.cal"
        print(cal_fn)
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
        # background = baseline_alg(cleaned_data, lam=1e5, p=0.01)
        # y_final -= background
        cleaned_y_final = [x for x in y_final if not math.isnan(x)]
        if max(cleaned_y_final)>0:
            y_final/=max(cleaned_y_final)
        return self.xnew,y_final

    def sum_modules(self):
        return self.__get_result_modules(self.moduleList)

    def get_pixels(self,pixel_range):
        x_list = []
        y_list = []
        for module in self.moduleList:
            if 'LA_offset' in self.conf:
                if self.conf['LA_offset']:
                    if self.conf['check_second']:
                        data = load_neutron_data(self.conf["sam_fn"][1], f'{self.conf["param_path"]}/{module}.txt',
                                                 module, self.conf["first_flight_distance"])
                    else:
                        data = load_neutron_data(self.conf["sam_fn"][0], f'{self.conf["param_path"]}/{module}.txt',
                                                 module, self.conf["first_flight_distance"])
                else:
                    data = load_neutron_data(self.conf["sam_fn"][0], f'{self.conf["param_path"]}/{module}.txt', module,
                                             self.conf["first_flight_distance"])
            else:
                data = load_neutron_data(self.conf["sam_fn"], f'{self.conf["param_path"]}/{module}.txt', module,
                                         self.conf["first_flight_distance"])
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

        # filename = f'D:\PostDoctoral\Works\Paper\RZera_Series_Expansion\submit/review\zjj/{name}.txt'
        # max_length = max(len(x), len(y), len(smoothed_y), len(peak), len(peaks_position))
        # with open(filename, 'w') as file:
        #     # 写入每个列的标题
        #     file.write("X\tY\tSmoothed_Y\tPeak\tPeaks_Position\n")
        #
        #     # 逐行写入每个参数的每个元素
        #     for i in range(max_length):
        #         # 对于每一行，将每个属性相应的值写入，如果列表短，写空值
        #         row = [
        #             str(x[i]) if i < len(x) else '',
        #             str(y[i]) if i < len(y) else '',
        #             str(smoothed_y[i]) if i < len(smoothed_y) else '',
        #             str(peak[i]) if i < len(peak) else '',
        #             str(peaks_position[i]) if i < len(peaks_position) else ''
        #         ]
        #         file.write("\t".join(row) + "\n")

        fig, ax = plt.subplots()
        # ax.plot(x, y, 'g-',linewidth=3, label='intensity')
        ax.scatter(x, y, color='green', marker='o', label='intensity')
        ax.plot(x, smoothed_y, 'b-',linewidth=3, label='smoothed_intensity')
        # for i in range(len(peak)):
        i = 2
        ax.plot(peak[i][0], peak[i][1], 'r-',linewidth=3, label='Fitted Gaussian')
        # ax.plot(all_d_peak[i], all_I_peak[i], 'rx')
        for j in peaks_position:
            ax.axvline(x=j, color='black', linestyle='--', linewidth=3,
                            label='Standard Peak Position' if j == peaks_position[0] else "")
        ax.grid(False)
        ax.set_title(name)
        ax.set_xlabel('d (Å)', fontsize = 24)
        ax.set_ylabel('Normalize (a.u.)', fontsize = 24)
        ax.legend(fontsize=18, ncol=1, loc='upper right')
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
        ax.plot(std, tof_fitted, color='red',linewidth=3, label='Fitted Curve')

        # x = np.array(std)
        # x_pos ,y_pos , z_pos = 0.84481, 1.04200, 2.00000 # 10301
        # # x_pos, y_pos, z_pos = 0.86498, 0.68675, 1.03963  # 11001
        # theta = np.arcsin(np.sqrt(x_pos ** 2 + y_pos ** 2) / np.sqrt(x_pos ** 2 + y_pos ** 2 + z_pos ** 2))
        # print(theta)
        # theory = 506.4895 * (78 + np.sqrt(x_pos **2 + y_pos**2 + z_pos**2)) * np.sin((np.pi - theta)/2) * x
        # # theory = 506.4895 * (78 + np.sqrt(x_pos ** 2 + y_pos ** 2 + z_pos ** 2)) * np.sin(theta / 2) * x
        # ax.plot(std, theory , color='blue', linewidth=3, label='Theoretical Curve')

        ax.set_xlabel('d_std (Å)', fontsize = 24)
        ax.set_ylabel('Time-of-Flight-exp (us)', fontsize = 24)
        ax.legend(fontsize=18)
        ax.grid(False)

        # 创建插图
        # inset_ax = fig.add_axes([0.6, 0.20, 0.25, 0.25])  # 插图位置：[x0, y0, width, height]
        # inset_ax.scatter(std, exp, color='blue')
        # inset_ax.plot(std, tof_fitted, color='red', linewidth=2)
        # inset_ax.plot(std, theory, color='blue', linewidth=2)
        #
        # # 设置插图显示的 x 范围
        # inset_x_start, inset_x_end = 2.9, 3.0  # 调整此范围以显示特定的 x 范围
        # inset_ax.set_xlim(inset_x_start, inset_x_end)
        #
        # # 也可以设置插图的 y 轴范围，保持一致性，选择适合的值
        # inset_y_start, inset_y_end = 110000, 120000  # 调整此范围以显示特定的 x 范围
        # inset_ax.set_ylim(inset_y_start, inset_y_end)
        #
        # inset_ax.set_title('Inset', fontsize=20)
        # inset_ax.tick_params(axis='both', which='major', labelsize=20)
        #
        # # 启用主图和插图的科学计数法
        # formatter = ScalarFormatter(useMathText=True)
        # formatter.set_scientific(True)
        # formatter.set_powerlimits((-2, 2))
        #
        # ax.xaxis.set_major_formatter(formatter)
        # ax.yaxis.set_major_formatter(formatter)
        # inset_ax.xaxis.set_major_formatter(formatter)
        # inset_ax.yaxis.set_major_formatter(formatter)
        return fig, ax

    def plot_offset_data(self, x, y, smoothed_y, d_offset, peaks_position):
        fig, ax = plt.subplots()
        # ax.plot(x, y, 'g-',linewidth=3, label='Original Data')
        ax.scatter(x, y, color='green', marker='o', label='Original Data')
        ax.plot(x, smoothed_y, 'b-',linewidth=3, label='Original Data (smoothed)')
        ax.plot(d_offset, smoothed_y, 'r-',linewidth=3, label='Offset Data (smoothed)')
        for j in peaks_position:
            ax.axvline(x=j, color='black', linestyle='--', linewidth=3,
                            label='Standard Peak Position' if j == peaks_position[0] else "")
        ax.grid(False)
        ax.legend(fontsize=18, ncol=1, loc='upper right')
        ax.set_xlabel('d (Å)', fontsize = 24)
        ax.set_ylabel('Normalize (a.u.)', fontsize = 24)
        return fig, ax

    def plot_result_data(self, plot_para, d_std):
        try:
            plt.rcParams.update({
                'font.size': 20,  # 设置为所需的字体大小
                'font.family': 'serif',  # 设置字体系列，如 'serif', 'sans-serif', 'monospace' 等
                'font.serif': ['Times New Roman']
            })
            fig, ax = plt.subplots()
            for i, para in enumerate(plot_para):
                print(para[1], para[2])
                ax.plot(para[1], para[2], label=para[0])
                if len(para) > 3:
                    for j in range(len(para[3][0][:,0])):
                        x = para[3][0][j,:]
                        y = para[4][0][j,:]
                        if np.any(y != 0):
                            y = y / np.max(y)
                        ax.plot(x, y, linewidth=3, label= int(para[5][0])+j+1)
            for j in d_std:
                ax.axvline(x=j, linestyle='--', linewidth=3,
                           label='Standard Peak Position' if j == d_std[0] else "")
            ax.grid(False)
            ax.legend(fontsize=16)

            # Set the font size for the tick labels on both axes
            ax.tick_params(axis='both', which='major')
            ax.tick_params(axis='both', which='minor')
            ax.set_xlabel('d (Å)', fontsize = 24)
            ax.set_ylabel('Normalize (a.u.)', fontsize = 24)
            return fig, ax
        except:
            traceback.print_exc()



