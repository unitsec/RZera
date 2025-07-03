from PyQt5.QtCore import QThread,pyqtSignal
import traceback
from drneutron.python.algSvc.instrument.CSNS_PDF import CSNS_PDF
from drneutron.python.algSvc.base import (interpolate,merge_all_curves,rebin,
                        generate_x,strip_peaks,smooth)
from drneutron.python.utils.helper import check_zeros
from workers.plot_item_operation import change_item
from PyQt5.QtCore import Qt
import re
from drneutron.python.utils.helper import replace_value
from drneutron.python.dataSvc.data_load import create_dataset
from drneutron.python.algSvc.neutron.abs_ms_nd import AbsMsCorrNeutronData
from drneutron.python.algSvc.neutron import units_convert_neutron_data
from drneutron.python.algSvc.base import merge_all_curves,generate_x
from workers.ui_mapping import pdf_mapping
from workers.reduction_check import sq_reduction_check
import json
import numpy as np
from utils_ui.process_dialog import ProgressDialog
import os
import sys


class start_pdf_thread:
    def __init__(self,parent=None):
        self.sqcal_thread = None  # 初始化为 None
        # 初始化进度对话框
        self.progress_dialog = ProgressDialog(parent)

    def start_sqcal(self,window,pdf_config,plot_list_dict,sam_list, other_list, pdf_cal_sq):

        try:

            pdf_config = pdf_mapping(window,pdf_config)
            if not sq_reduction_check(window,pdf_config):
                return
            # 如果是 PyInstaller 打包后的临时目录中运行
            if getattr(sys, 'frozen', False):
                # 获取 PyInstaller 打包后的临时目录路径
                temp_dir = getattr(sys, '_MEIPASS', os.path.abspath(os.path.dirname(sys.executable)))
                bl16_config = os.path.join(temp_dir, 'bl16_config.json')
            else:
                # 如果是在源码中运行
                temp_dir = os.path.abspath(os.path.dirname(__file__))
                bl16_config = os.path.join(os.path.dirname(temp_dir), 'utils_ui', 'bl16_config.json')

            with open(bl16_config, 'r', encoding='utf-8') as json_file:
                bl16_configure = json.load(json_file)
            pdf_cal_sq.setEnabled(False)
            pdf_cal_sq.setText('Calculating')
            # if pdf_config['mode'] == 'offline':
            self.sqcal_thread = sqcal_thread(pdf_config,bl16_configure,plot_list_dict,sam_list,other_list)
            # 连接信号
            self.sqcal_thread.update_progress.connect(self.progress_dialog.update_progress)
            self.sqcal_thread.finished.connect(
                lambda: self.on_sqcal_thread_finished(pdf_cal_sq))
            self.progress_dialog.update_progress(0)
            self.progress_dialog.canceled.connect(self.sqcal_thread.stop)
            self.progress_dialog.show()  # 添加这一行来显示进度对话框
            self.sqcal_thread.start()

            # else:
            #     # 需要开发在线模式数据归约时再扩展
            #     pdf_cal_sq.setText('Calculate S(Q)')
            #     pdf_cal_sq.setEnabled(True)
        except Exception as e:
            print(f"An error occurred: {e}")
            traceback.print_exc()  # 打印异常的堆栈跟踪


    def on_sqcal_thread_finished(self,pdf_cal_sq):
        try:
            pdf_cal_sq.setText('Calculate S(Q)')
            pdf_cal_sq.setEnabled(True)
            self.progress_dialog.accept()
        except Exception as e:
            print(f"An error occurred: {e}")
            traceback.print_exc()  # 打印异常的堆栈跟踪

    def start_merge(
            self,window,pdf_config,plot_list_dict,plot_list,pdf_merge):

        try:
            pdf_merge.setEnabled(False)
            pdf_merge.setText('Merging')
            pdf_config = pdf_mapping(window, pdf_config)
            self.merge_thread = merge_thread(pdf_config,plot_list_dict,plot_list)
            # 连接信号
            # self.sqcal_thread.update_progress.connect(self.progress_dialog.update_progress)
            self.merge_thread.finished.connect(
                lambda: self.on_merge_thread_finished(plot_list,plot_list_dict,pdf_merge))
            # self.progress_dialog.update_progress(0)
            # self.progress_dialog.canceled.connect(self.reduction_thread.stop)
            # self.progress_dialog.show()  # 添加这一行来显示进度对话框
            self.merge_thread.start()
        except Exception as e:
            print(f"An error occurred: {e}")
            traceback.print_exc()  # 打印异常的堆栈跟踪

    def on_merge_thread_finished(self, plot_list, plot_list_dict, pdf_merge):
        try:
            self.change_item = change_item(plot_list)
            self.change_item.setup_plot_list(plot_list, plot_list_dict)  # 设置 plot_list
            pdf_merge.setText('Merge S(Q)')
            pdf_merge.setEnabled(True)
            # self.progress_dialog.accept()
        except Exception as e:
            print(f"An error occurred: {e}")
            traceback.print_exc()  # 打印异常的堆栈跟踪


class sqcal_thread(QThread):
    update_progress = pyqtSignal(int)
    def __init__(self,pdf_config,bl16_config,plot_list_dict,sam_list,other_list):
        super(sqcal_thread, self).__init__()
        self.pdf_configure = pdf_config
        self.bl16_configure = bl16_config
        self.plot_list_dict = plot_list_dict
        self.sam_list = sam_list
        self.other_list = other_list
        self.change_sam_item = change_item(sam_list)
        self.change_other_item = change_item(other_list)
        self._is_running = True  # 控制线程运行的标志

    def run(self):
        # if self.pdf_configure['mode'] == 'offline':

            try:
                configure = {**self.pdf_configure, **self.bl16_configure}
                moduleList = list(configure["bank_match"].keys())
                bankList = ['bank3','bank5']
                detectorList = bankList + moduleList
                print(detectorList)
                j = 0
                for detector in detectorList:
                    bl16 = CSNS_PDF(configure,detector)
                    suffix = '_d'
                    if configure['hold_run_mode']=='dat':
                        fn = configure['hold_fn']+'/hold_'+configure['hold_run']+'_'+bl16.detector+suffix + '.dat'
                        x, y, e = np.loadtxt(fn, unpack=True)
                        y_hold, e_hold = rebin(x, y, e, bl16.xnew)
                    else:
                        hold_dataset = bl16.process_detector(configure["hold_fn"], False)
                        runno = configure["hold_run"][0]
                        name = "hold_" + runno + "_" + bl16.detector + suffix
                        y_hold = hold_dataset["histogram"].values[0]
                        e_hold = hold_dataset["error"].values[0]
                        self.plot_list_dict['other_list'][name] = [bl16.xnew, y_hold, e_hold, runno]
                        self.change_other_item.setup_plot_list(self.other_list, self.plot_list_dict['other_list'])  # 设置 plot_list

                    if configure['v_run_mode']=='dat':
                        fn = configure["v_fn"]+"/v_"+configure["v_run"]+"_"+bl16.detector + suffix + '.dat'
                        x, y, e = np.loadtxt(fn, unpack=True)
                        y_v, e_v = rebin(x, y, e, bl16.xnew)
                    else:
                        v_dataset = bl16.process_detector(configure["v_fn"], True)
                        runno = configure["v_run"][0]
                        name = "v_" + runno + "_" + bl16.detector + suffix
                        # if name in self.plot_list_dict:
                        #     # 键已存在，添加一个后缀
                        #     added_suffix = 1
                        #     new_name = f"{name}_{added_suffix}"
                        #     while new_name in self.plot_list_dict:
                        #         added_suffix += 1
                        #         new_name = f"{name}_{added_suffix}"
                        #     name = new_name
                        y_v = v_dataset["histogram"].values[0]
                        e_v = v_dataset["error"].values[0]
                        self.plot_list_dict['other_list'][name] = [bl16.xnew, y_v, e_v, runno]

                        self.change_other_item.setup_plot_list(self.other_list, self.plot_list_dict['other_list'])  # 设置 plot_list

                    if configure['scale_v_hold']>0:
                        y_v = y_v - configure['scale_v_hold']*y_hold

                    sam_dataset = bl16.process_detector(configure["sam_fn"], False)
                    y_sam = sam_dataset["histogram"].values[0]
                    e_sam = sam_dataset["error"].values[0]
                    x_sam = sam_dataset["xvalue"].values[0]

                    y_sam = y_sam - configure["scale_sam_hold"] * y_hold
                    e_sam = np.sqrt(e_sam ** 2 + (configure["scale_sam_hold"] * e_hold) ** 2)
                    y_sam = y_sam / y_v
                    pixel = sam_dataset["positions"].coords["pixel"].values
                    pos = sam_dataset["positions"].values
                    neutron_data = create_dataset(y_sam, e_sam, x_sam,
                                                  pixel, pos,
                                                  sam_dataset['proton_charge'], sam_dataset['l1'])
                    # task = AbsMsCorrNeutronData(neutron_data)
                    # neutron_data = task.run_carpenter(configure["sample_property"])
                    neutron_data = units_convert_neutron_data(neutron_data, "dspacing", "q")
                    factor = configure["sample_property"]["v_factor"] / configure["sample_property"]["atom_num"]
                    bsqa = configure["sample_property"]["b_sqrd_avg"]
                    basq = configure["sample_property"]["b_avg_sqrd"]
                    laue = bsqa / basq
                    x, y, e = neutron_data["xvalue"].values[0], neutron_data["histogram"].values[0], neutron_data["error"].values[0]
                    y = y * factor
                    y = y * (1 / basq) - laue + 1
                    # y = replace_value(y)
                    ave = np.mean(y[-20:])
                    # print(self.detector,ave,y[-20:])
                    y = y / ave
                    # print(len(x),len(y),len(e))

                    runno = configure["sam_run"][0]
                    name = "sam_" + runno + "_" + bl16.detector + '_sq'
                    if name in self.plot_list_dict['sam_list']:
                        # 键已存在，添加一个后缀
                        suffix = 1
                        new_name = f"{name}_{suffix}"
                        while new_name in self.plot_list_dict['sam_list']:
                            suffix += 1
                            new_name = f"{name}_{suffix}"
                        name = new_name
                    self.plot_list_dict['sam_list'][name] = [x, y, e, runno]

                    self.change_sam_item.setup_plot_list(self.sam_list, self.plot_list_dict['sam_list'])  # 设置 plot_list
                    j = j+1
                    k = int(j / len(detectorList) * 100)
                    self.update_progress.emit(k)  # 发出进度更新信号

                    # 检查点：检查是否需要停止线程
                    if not self._is_running:
                        break  # 如果停止标志被设置为 False，则退出循环

            except Exception as e:
                print(f"An error occurred: {e}")
                traceback.print_exc()  # 打印异常的堆栈跟踪

    def stop(self):
        self._is_running = False  # 设置标志以停止线程


class merge_thread(QThread):
    # update_progress = pyqtSignal(int)
    def __init__(self, pdf_config,plot_list_dict,plot_list):
        super(merge_thread, self).__init__()
        self.pdf_configure = pdf_config
        self.plot_list_dict = plot_list_dict
        self.plot_list = plot_list
        self.change_item = change_item(plot_list)
        self._is_running = True  # 控制线程运行的标志

    def run(self):
        try:
            data_pairs = []
            stitch_detectors = []
            for index in range(1, self.plot_list.count()):  # 从 1 开始，跳过 "ALL" 条目
                item = self.plot_list.item(index)
                if item.checkState() == Qt.Checked:
                    [x,y,e,_] = self.plot_list_dict[item.text()]
                    data_pairs.append((x, y, e))
                    stitch_detectors.append(re.findall(r'module\d+|bank\d+', self.plot_list.item(index).text())[-1])
            x, y, e = merge_all_curves(data_pairs, self.pdf_configure["overlap"])
            ave = np.mean(y[-20:])
            # print(self.detector,ave,y[-20:])
            y = y / ave
            name = "stitch_" + '_'.join(stitch_detectors) + "_sq"
            if name in self.plot_list_dict:
                # 键已存在，添加一个后缀
                suffix = 1
                new_name = f"{name}_{suffix}"
                while new_name in self.plot_list_dict:
                    suffix += 1
                    new_name = f"{name}_{suffix}"
                name = new_name
            self.plot_list_dict[name] = [x, y, e, stitch_detectors]

        except Exception as e:
            print(f"An error occurred: {e}")
            traceback.print_exc()  # 打印异常的堆栈跟踪

    def stop(self):
        self._is_running = False  # 设置标志以停止线程