from PyQt5.QtCore import QThread,pyqtSignal
import traceback
from drneutron.python.algSvc.instrument.CSNS_diffraction import CSNS_Diffraction
from drneutron.python.algSvc.base import (rebin,strip_peaks,smooth,generate_x)
from workers.plot_item_operation import change_item
import numpy as np
from utils_ui.process_dialog import ProgressDialog
from workers.ui_mapping import diff_mapping
import json
from workers.reduction_check import diff_reduction_check
import os
import sys

class start_reduction_thread:
    def __init__(self,parent=None):
        self.reduction_thread = None  # 初始化为 None
        # 初始化进度对话框
        self.progress_dialog = ProgressDialog(parent)

    def start_reduction(self,window,diff_config,plot_list_dict,sam_list,other_list,reduction):
        try:
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

            diff_config = diff_mapping(window, diff_config, bl16_configure)
            if not diff_reduction_check(window, diff_config):
                return

            reduction.setEnabled(False)
            reduction.setText('Reducing')
            # if diff_config['mode'] == 'offline':
            self.reduction_thread = reduction_thread(diff_config,bl16_configure,plot_list_dict,sam_list,other_list)
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

    def __init__(self,diff_config,bl16_config,plot_list_dict,sam_list,other_list):
        super(reduction_thread, self).__init__()
        self.diff_configure = diff_config
        if diff_config['time_slice']:
            diff_config['slice_series'] = range(len(self.diff_configure["sam_fn"]))[-1]
        self.bl16_configure = bl16_config
        self.plot_list_dict = plot_list_dict
        self.sam_list = sam_list
        self.other_list = other_list
        self.change_item = change_item(sam_list)
        self.change_other_item = change_item(other_list)
        self._is_running = True  # 控制线程运行的标志

    def run(self):
        # if self.diff_configure['mode'] == 'offline':
            try:
                self.diff_configure = {**self.diff_configure, **self.bl16_configure}
                j = 0
                for bank in self.diff_configure["bank_name"]:

                    # 检查点：检查是否需要停止线程
                    if not self._is_running:
                        break  # 如果停止标志被设置为 False，则退出循环

                    bl16 = CSNS_Diffraction(self.diff_configure,bank)

                    if self.diff_configure["useHold"]:
                        if self.diff_configure["hold_run_mode"] == "dat":
                            fn = self.diff_configure["hold_fn"] + "/hold_" + self.diff_configure["hold_run"] + "_" + bank + bl16.suffix + '.dat'
                            x, y, e = np.loadtxt(fn, unpack = True)
                            y_hold,e_hold = rebin(x,y,e,bl16.xnew)
                        else:
                            y_hold, e_hold = bl16.process_bank('hold',[], True)

                            runno = self.diff_configure["hold_run"][0]
                            name = "hold_" + runno + "_" + bank + bl16.suffix
                            # if name in self.plot_list_dict:
                            #     # 键已存在，添加一个后缀
                            #     added_suffix = 1
                            #     new_name = "hold_" + runno + "_" + bank + '_' + bl16.suffix + str(added_suffix)
                            #     while new_name in self.plot_list_dict:
                            #         added_suffix += 1
                            #         new_name = "hold_" + runno + "_" + bank +f'_{added_suffix}_'+ bl16.suffix[:-4]
                            #     name = new_name
                            self.plot_list_dict['other_list'][name] = [bl16.xnew, y_hold, e_hold, bl16.tof, runno, bank]
                            self.change_other_item.setup_plot_list(self.other_list, self.plot_list_dict['other_list'])  # 设置 plot_list

                    if self.diff_configure["useV"]:
                        if self.diff_configure["v_run_mode"] == "dat":
                            fn = self.diff_configure["v_fn"] + "/v_" + self.diff_configure["v_run"] + "_" + bank + bl16.suffix + '.dat'
                            x, y, e = np.loadtxt(fn,unpack=True)
                            y_v, e_v = rebin(x, y, e, bl16.xnew)
                        else:
                            y_v,e_v = bl16.process_bank("v",[],True)

                            runno = self.diff_configure["v_run"][0]
                            name = "v_" + runno + "_" + bank + bl16.suffix
                            # if name in self.plot_list_dict:
                            #     # 键已存在，添加一个后缀
                            #     added_suffix = 1
                            #     new_name = "v_" + runno + "_" + bank +f'_{added_suffix}_'+ bl16.suffix[:-4]
                            #     while new_name in self.plot_list_dict:
                            #         added_suffix += 1
                            #         new_name = "v_" + runno + "_" + bank +f'_{added_suffix}_'+ bl16.suffix[:-4]
                            #     name = new_name
                            self.plot_list_dict['other_list'][name] = [bl16.xnew, y_v, e_v, bl16.tof, runno, bank]
                            self.change_other_item.setup_plot_list(self.other_list, self.plot_list_dict['other_list'])  # 设置 plot_list

                        if self.diff_configure["useHold"] and self.diff_configure["scale_v_hold"] > 0:
                            y_v = y_v - self.diff_configure["scale_v_hold"] * y_hold

                    if self.diff_configure["is_batch"]:
                        for i in range(len(self.diff_configure["sam_fn"])):

                            # 检查点：检查是否需要停止线程
                            if not self._is_running:
                                break  # 如果停止标志被设置为 False，则退出循环

                            run_fn = self.diff_configure["sam_fn"][i]
                            y_sam, e_sam = bl16.process_bank('sam', [run_fn], False)
                            if self.diff_configure["useHold"]:
                                y_sam = y_sam - self.diff_configure["scale_sam_hold"] * y_hold
                                e_sam = np.sqrt(e_sam ** 2 + (self.diff_configure["scale_sam_hold"] * e_hold) ** 2)
                            if self.diff_configure["useV"]:
                                y_sam = y_sam / y_v
                                e_sam = e_sam / y_v

                            if self.diff_configure["time_slice"]:
                                runno = self.diff_configure["sam_run"][0]
                                suffix_tmp = '_' + str(i) + bl16.suffix
                                self.diff_configure["slice_series"] = i
                            else:
                                runno = self.diff_configure["sam_run"][i]
                                suffix_tmp = bl16.suffix
                            name = 'sam_' + runno + "_" + bank + suffix_tmp
                            if name in self.plot_list_dict['sam_list']:
                                # 键已存在，添加一个后缀
                                added_suffix = 1
                                new_suffix_tmp = suffix_tmp[:-2] + f'_{added_suffix}' + suffix_tmp[-2:]
                                new_name = 'sam_' + runno + "_" + bank + new_suffix_tmp
                                while new_name in self.plot_list_dict['sam_list']:
                                    added_suffix += 1
                                    new_suffix_tmp = suffix_tmp[:-2] + f'_{added_suffix}' + suffix_tmp[-2:]
                                    new_name = 'sam_' + runno + "_" + bank + new_suffix_tmp
                                name = new_name
                            self.plot_list_dict['sam_list'][name] = [bl16.xnew, y_sam, e_sam, bl16.tof, runno, bank]
                            self.change_item.setup_plot_list(self.sam_list, self.plot_list_dict['sam_list'])  # 设置 plot_list
                            j = j + 1
                            k = int(j / (len(self.diff_configure["bank_name"])*len(self.diff_configure['sam_run'])) * 100)
                            self.update_progress.emit(k)  # 发出进度更新信号
                    else:

                        # 检查点：检查是否需要停止线程
                        if not self._is_running:
                            break  # 如果停止标志被设置为 False，则退出循环

                        y_sam, e_sam = bl16.process_bank('sam', [], True)
                        if self.diff_configure["useHold"]:
                            y_sam = y_sam - self.diff_configure["scale_sam_hold"] * y_hold
                            e_sam = np.sqrt(e_sam ** 2 + (self.diff_configure["scale_sam_hold"] * e_hold) ** 2)

                        if self.diff_configure["useV"]:
                            y_sam = y_sam / y_v
                            e_sam = e_sam / y_v

                        runno = self.diff_configure["sam_run"][0]
                        name = 'sam_' + runno + "_" + bank + bl16.suffix
                        if name in self.plot_list_dict['sam_list']:
                            # 键已存在，添加一个后缀
                            added_suffix = 1
                            new_suffix_tmp = bl16.suffix[:-2] + f'_{added_suffix}' + bl16.suffix[-2:]
                            new_name = 'sam_' + runno + "_" + bank + new_suffix_tmp
                            while new_name in self.plot_list_dict['sam_list']:
                                added_suffix += 1
                                new_suffix_tmp = bl16.suffix[:-2] + f'_{added_suffix}' + bl16.suffix[-2:]
                                new_name = 'sam_' + runno + "_" + bank + new_suffix_tmp
                            name = new_name
                        self.plot_list_dict['sam_list'][name] = [bl16.xnew, y_sam, e_sam, bl16.tof, runno, bank]
                        self.change_item.setup_plot_list(self.sam_list, self.plot_list_dict['sam_list'])  # 设置 plot_list
                        j = j + 1
                        k = int(j / len(self.diff_configure["bank_name"]) * 100)
                        self.update_progress.emit(k)  # 发出进度更新信号

                    # 检查点：检查是否需要停止线程
                    if not self._is_running:
                        break  # 如果停止标志被设置为 False，则退出循环

            except Exception as e:
                print(f"An error occurred: {e}")
                traceback.print_exc()  # 打印异常的堆栈跟踪

    def stop(self):
        self._is_running = False  # 设置标志以停止线程