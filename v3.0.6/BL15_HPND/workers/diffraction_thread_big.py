from PyQt5.QtCore import QThread,pyqtSignal
from PyQt5.QtWidgets import QListWidget
import traceback
from BL15_HPND.workers.CSNS_diffraction import CSNS_Diffraction
from rongzai.algSvc.base import (rebin,strip_peaks,smooth)
from rongzai.utils import check_file,generate_x
from BL15_HPND.workers.plot_item_operation import change_item
import numpy as np
from utils.process_dialog import ProgressDialog
from BL15_HPND.workers.ui_mapping_big import diff_mapping
import json
from BL15_HPND.workers.reduction_check import diff_reduction_check
import os
import sys

class start_reduction_thread:
    def __init__(self,parent=None):
        self.reduction_thread = None  # 初始化为 None
        # 初始化进度对话框
        self.progress_dialog = ProgressDialog(parent)

    def start_reduction(self,window,diff_config,plot_list_dict,sam_list,filterbox,other_list,reduction):
        try:
            # 如果是 PyInstaller 打包后的临时目录中运行
            if getattr(sys, 'frozen', False):
                # 获取 PyInstaller 打包后的临时目录路径
                temp_dir = getattr(sys, '_MEIPASS', os.path.abspath(os.path.dirname(sys.executable)))
                bl15_config = os.path.join(temp_dir, 'BL15_big_base.json')
            else:
                # 如果是在源码中运行
                temp_dir = os.path.abspath(os.path.dirname(__file__))
                bl15_config = os.path.join(os.path.dirname(temp_dir), '..', 'CSNS_Alg','configure', 'BL15_big_base.json')

            with open(bl15_config, 'r', encoding='utf-8') as json_file:
                bl15_configure = json.load(json_file)

            diff_config, bl15_configure = diff_mapping(window, diff_config, bl15_configure)
            if not diff_reduction_check(window, diff_config, bl15_configure):
                return

            reduction.setEnabled(False)
            reduction.setText('Reducing')
            # if diff_config['mode'] == 'offline':
            self.reduction_thread = reduction_thread(diff_config,bl15_configure,plot_list_dict,sam_list,filterbox,other_list)
            self.change_sam_item = change_item(sam_list, plot_list_dict['sam_list'])
            self.reduction_thread.update_plot_list.connect(self.change_sam_item.setup_plot_list)
            self.reduction_thread.add_item_signal.connect(filterbox.add_item)
            # 连接信号
            self.reduction_thread.update_progress.connect(self.progress_dialog.update_progress)
            self.reduction_thread.finished.connect(
                lambda: self.on_reduction_thread_finished(reduction))
            self.progress_dialog.update_progress(0)
            self.progress_dialog.canceled.connect(self.reduction_thread.stop)
            self.progress_dialog.show()  # 添加这一行来显示进度对话框
            self.reduction_thread.start()

            # else:
            #     需要开发在线模式数据归约时再扩展
            #     reduction.setText('Reduction')
            #     reduction.setEnabled(True)
        except Exception as e:
            print(f"An error occurred: {e}")
            traceback.print_exc()  # 打印异常的堆栈跟踪

    def on_reduction_thread_finished(self, reduction):
        try:
            # self.change_item = change_item(plot_list)
            # self.change_item.setup_plot_list(plot_list,save_path)  # 设置 plot_list
            reduction.setText('Reduction')
            reduction.setEnabled(True)
            self.progress_dialog.accept()
        except Exception as e:
            print(f"An error occurred: {e}")
            traceback.print_exc()  # 打印异常的堆栈跟踪


class reduction_thread(QThread):
    update_progress = pyqtSignal(int)
    add_item_signal = pyqtSignal(str)
    update_plot_list = pyqtSignal(QListWidget, dict, list)

    def __init__(self,diff_config,bl15_config,plot_list_dict,sam_list,filterbox, other_list):
        super(reduction_thread, self).__init__()
        self.diff_configure = diff_config
        if diff_config['time_slice']:
            diff_config['slice_series'] = range(len(self.diff_configure["sam_fn"]))[-1]
        self.bl15_configure = bl15_config
        self.plot_list_dict = plot_list_dict
        self.sam_list = sam_list
        self.filterbox = filterbox
        self.other_list = other_list
        self.change_item = change_item(sam_list,plot_list_dict['sam_list'])
        self.change_other_item = change_item(other_list,plot_list_dict['other_list'])
        self._is_running = True  # 控制线程运行的标志

    def run(self):
        # if self.diff_configure['mode'] == 'offline':
            try:
                j = 0
                for group in self.diff_configure["group_list"]:

                    # 检查点：检查是否需要停止线程
                    if not self._is_running:
                        break  # 如果停止标志被设置为 False，则退出循环

                    bl15 = CSNS_Diffraction(self.bl15_configure,self.diff_configure,group)

                    if len(bl15.conf['samBG_run'])>0:
                        if bl15.conf["samBG_run_mode"] == "dat":
                            fn = bl15.conf["samBG_fn"][0] + "/samBG_" + bl15.conf["samBG_run"][0] + "_" + group + '_' + bl15.suffix
                            if check_file(fn):
                                x, y, e = np.loadtxt(fn, unpack=True)
                                y_samBG,e_samBG = rebin(x,y,e,bl15.xnew)
                            else:
                                y_samBG, e_samBG = bl15.process_bank("samBG", [], False)
                        else:
                            y_samBG, e_samBG = bl15.process_bank('samBG',[], False)

                        runno = bl15.conf["samBG_run"][0]
                        name = "samBG_" + runno + "_" + group + '_' + bl15.suffix[:-4]
                        self.plot_list_dict['other_list'][name] = [bl15.xnew, y_samBG, e_samBG, bl15.tof, runno, group]
                        self.change_other_item.setup_plot_list(self.other_list, self.plot_list_dict['other_list'])  # 设置 plot_list

                    # 检查点：检查是否需要停止线程
                    if not self._is_running:
                        break  # 如果停止标志被设置为 False，则退出循环

                    if bl15.conf["useV"]:
                        if bl15.conf["v_run_mode"] == "dat":
                            fn = self.diff_configure["v_fn"][0] + "/v_" + self.diff_configure["v_run"][0] + "_" + group + '_' + bl15.suffix
                            if check_file(fn):
                                x, y, e = np.loadtxt(fn,unpack=True)
                                y_v, e_v = rebin(x, y, e, bl15.xnew)
                            else:
                                y_v, e_v = bl15.process_bank("v", [], False)
                        else:
                            y_v,e_v = bl15.process_bank("v",[],False)
                        runno = self.diff_configure["v_run"][0]
                        name = "v_" + runno + "_" + group + '_' + bl15.suffix[:-4]
                        self.plot_list_dict['other_list'][name] = [bl15.xnew, y_v, e_v, bl15.tof, runno, group]
                        self.change_other_item.setup_plot_list(self.other_list, self.plot_list_dict['other_list'])  # 设置 plot_list

                        # 检查点：检查是否需要停止线程
                        if not self._is_running:
                            break  # 如果停止标志被设置为 False，则退出循环

                        if bl15.conf["useVBG"]:
                            if bl15.conf["vBG_run_mode"] == "dat":
                                fn = bl15.conf["vBG_fn"][0] + "/vBG_" + self.diff_configure["vBG_run"][0] + "_" + group + '_' + bl15.suffix
                                if check_file(fn):
                                    x, y, e = np.loadtxt(fn, unpack=True)
                                    y_vBG, e_vBG = rebin(x, y, e, bl15.xnew)
                                else:
                                    y_vBG, e_vBG = bl15.process_bank("vBG", [], False)
                            else:
                                y_vBG, e_vBG = bl15.process_bank("vBG", [], False)
                            runno = self.diff_configure["vBG_run"][0]
                            name = "vBG_" + runno + "_" + group + '_' + bl15.suffix[:-4]
                            self.plot_list_dict['other_list'][name] = [bl15.xnew, y_vBG, e_vBG, bl15.tof, runno, group]
                            self.change_other_item.setup_plot_list(self.other_list,
                                                                   self.plot_list_dict['other_list'])  # 设置 plot_list
                            if bl15.conf["scale_v_bg"]>0:
                                y_v = y_v - self.diff_configure["scale_v_bg"] * y_vBG

                    if bl15.conf["is_batch"]:
                        for i in range(len(bl15.conf["sam_fn"])):

                            # 检查点：检查是否需要停止线程
                            if not self._is_running:
                                break  # 如果停止标志被设置为 False，则退出循环

                            run_fn = bl15.conf["sam_fn"][i]
                            y_sam, e_sam = bl15.process_bank('sam', [run_fn], False)
                            if bl15.conf["useSamBG"]:
                                y_sam = y_sam - bl15.conf["scale_sam_bg"] * y_samBG
                                e_sam = np.sqrt(e_sam ** 2 + (bl15.conf["scale_sam_bg"] * e_samBG) ** 2)
                            if bl15.conf["useV"]:
                                y_sam = y_sam / y_v
                                e_sam = e_sam / y_v

                            if bl15.conf["time_slice"]:
                                runno = bl15.conf["sam_run"][0]
                                suffix_tmp = 't' + str(i) + '_' + bl15.suffix
                                bl15.conf["slice_series"] = i
                            else:
                                runno = bl15.conf["sam_run"][i]
                                suffix_tmp = bl15.suffix
                            added_suffix = 0
                            new_suffix_tmp = suffix_tmp[:-4] + f'_{added_suffix}'
                            name = 'sam_' + runno + "_" + group + '_' + new_suffix_tmp
                            if name in self.plot_list_dict['sam_list']:
                                # 键已存在，添加一个后缀
                                added_suffix += 1
                                new_suffix_tmp = suffix_tmp[:-4] + f'_{added_suffix}'
                                new_name = 'sam_' + runno + "_" + group + '_' + new_suffix_tmp
                                while new_name in self.plot_list_dict['sam_list']:
                                    added_suffix += 1
                                    new_suffix_tmp = suffix_tmp[:-4] + f'_{added_suffix}'
                                    new_name = 'sam_' + runno + "_" + group + '_' + new_suffix_tmp
                                name = new_name
                            self.plot_list_dict['sam_list'][name] = [bl15.xnew, y_sam, e_sam, bl15.tof, runno, group]
                            self.change_item.setup_plot_list(self.sam_list, self.plot_list_dict['sam_list'],self.filterbox.get_selected())  # 设置 plot_list

                            name_elements = name.split('_')
                            for name_element in name_elements:
                                if name_element not in self.filterbox.get_item_names():
                                    self.add_item_signal.emit(name_element)

                            j = j + 1
                            k = int(j / (len(bl15.conf["group_list"])*len(bl15.conf['sam_run'])) * 100)
                            self.update_progress.emit(k)  # 发出进度更新信号
                    else:

                        # 检查点：检查是否需要停止线程
                        if not self._is_running:
                            break  # 如果停止标志被设置为 False，则退出循环

                        y_sam, e_sam = bl15.process_bank('sam', [], False)
                        if bl15.conf["useSamBG"]:
                            y_sam = y_sam - bl15.conf["scale_sam_bg"] * y_samBG
                            e_sam = np.sqrt(e_sam ** 2 + (bl15.conf["scale_sam_bg"] * e_samBG) ** 2)

                        if bl15.conf["useV"]:
                            y_sam = y_sam / y_v
                            e_sam = e_sam / y_v

                        runno = self.diff_configure["sam_run"][0]

                        added_suffix = 0
                        new_suffix_tmp = bl15.suffix[:-4] + f'_{added_suffix}'
                        name = 'sam_' + runno + "_" + group + '_' + new_suffix_tmp
                        if name in self.plot_list_dict['sam_list']:
                            # 键已存在，添加一个后缀
                            added_suffix += 1
                            new_suffix_tmp = bl15.suffix[:-4] + f'_{added_suffix}'
                            new_name = 'sam_' + runno + "_" + group + '_' + new_suffix_tmp
                            while new_name in self.plot_list_dict['sam_list']:
                                added_suffix += 1
                                new_suffix_tmp = bl15.suffix[:-4] + f'_{added_suffix}'
                                new_name = 'sam_' + runno + "_" + group + '_' + new_suffix_tmp
                            name = new_name
                        self.plot_list_dict['sam_list'][name] = [bl15.xnew, y_sam, e_sam, bl15.tof, runno, group]
                        selected = self.filterbox.get_selected()
                        self.update_plot_list.emit(self.sam_list, self.plot_list_dict['sam_list'], selected)
                        # self.change_item.setup_plot_list(self.sam_list, self.plot_list_dict['sam_list'], selected)  # 设置 plot_list

                        name_elements = name.split('_')
                        for name_element in name_elements:
                            if name_element not in self.filterbox.get_item_names():
                                self.add_item_signal.emit(name_element)

                        j = j + 1
                        k = int(j / len(bl15.conf["group_list"]) * 100)
                        self.update_progress.emit(k)  # 发出进度更新信号

                    # 检查点：检查是否需要停止线程
                    if not self._is_running:
                        break  # 如果停止标志被设置为 False，则退出循环

            except Exception as e:
                print(f"An error occurred: {e}")
                traceback.print_exc()  # 打印异常的堆栈跟踪

    def stop(self):
        self._is_running = False  # 设置标志以停止线程py