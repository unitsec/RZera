from PyQt5.QtCore import QThread,pyqtSignal
from PyQt5.QtWidgets import QListWidget
import traceback
from CSNS_Alg.CSNS_time_slice import CSNS_TimeSlice
from rongzai.algSvc.base import (rebin,strip_peaks,smooth)
from rongzai.utils import check_file,generate_x
from BL16_MPI.workers.plot_item_operation import change_item
import numpy as np
from utils.process_dialog import ProgressDialog
from BL16_MPI.workers.ui_mapping import timeslice_mapping
import json
from BL16_MPI.workers.reduction_check import timeslice_reduction_check
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
                bl16_config = os.path.join(temp_dir, 'bl16_base.json')
            else:
                # 如果是在源码中运行
                temp_dir = os.path.abspath(os.path.dirname(__file__))
                bl16_config = os.path.join(os.path.dirname(temp_dir), '..', 'CSNS_Alg','configure', 'BL16_base.json')

            with open(bl16_config, 'r', encoding='utf-8') as json_file:
                bl16_configure = json.load(json_file)

            diff_config, bl16_configure = timeslice_mapping(window, diff_config, bl16_configure)
            if not timeslice_reduction_check(window, diff_config, bl16_configure):
                return

            reduction.setEnabled(False)
            reduction.setText('Reducing')
            # if diff_config['mode'] == 'offline':
            self.reduction_thread = timeslice_thread(diff_config,bl16_configure,plot_list_dict,sam_list,filterbox,other_list)
            self.change_sam_item = change_item(sam_list, plot_list_dict['sam_list'])
            self.reduction_thread.update_plot_list.connect(self.change_sam_item.setup_plot_list)
            self.reduction_thread.update_plot_list_simple.connect(self.change_sam_item.setup_plot_list)
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


class timeslice_thread(QThread):
    update_progress = pyqtSignal(int)
    add_item_signal = pyqtSignal(str)
    update_plot_list = pyqtSignal(QListWidget, dict, list)
    update_plot_list_simple = pyqtSignal(QListWidget, dict)

    def __init__(self,diff_config,bl16_config,plot_list_dict,sam_list,filterbox, other_list):
        super(timeslice_thread, self).__init__()
        self.diff_configure = diff_config
        self.bl16_configure = bl16_config
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

                    bl16 = CSNS_TimeSlice(self.bl16_configure,self.diff_configure,group,ui=True)
                    sam_plot_data, other_plot_data = bl16.reduction()

                    # 检查点：检查是否需要停止线程
                    if not self._is_running:
                        break  # 如果停止标志被设置为 False，则退出循环

                    samBG = other_plot_data.get('samBG', None) # 使用 dict.get 方法来安全地访问键
                    if samBG:
                        runno = bl16.conf["samBG_run"][0]
                        name = "samBG_" + runno + "_" + group + '_' + bl16.suffix[:-4]
                        plot_data = [
                            other_plot_data['samBG'][0],
                            other_plot_data['samBG'][1],
                            other_plot_data['samBG'][2],
                            bl16.tof,
                            runno,
                            group
                        ]
                        self.plot_list_dict['other_list'][name] = plot_data
                        self.update_plot_list_simple.emit(self.other_list, self.plot_list_dict['other_list'])

                    v = other_plot_data.get('v', None)  # 使用 dict.get 方法来安全地访问键
                    if v:
                        runno = bl16.conf["v_run"][0]
                        name = "v_" + runno + "_" + group + '_' + bl16.suffix[:-4]
                        plot_data = [
                            other_plot_data['v'][0],
                            other_plot_data['v'][1],
                            other_plot_data['v'][2],
                            bl16.tof,
                            runno,
                            group
                        ]
                        self.plot_list_dict['other_list'][name] = plot_data
                        self.update_plot_list_simple.emit(self.other_list, self.plot_list_dict['other_list'])

                    vBG = other_plot_data.get('vBG', None)  # 使用 dict.get 方法来安全地访问键
                    if vBG:
                        runno = bl16.conf["vBG_run"][0]
                        name = "vBG_" + runno + "_" + group + '_' + bl16.suffix[:-4]
                        plot_data = [
                            other_plot_data['vBG'][0],
                            other_plot_data['vBG'][1],
                            other_plot_data['vBG'][2],
                            bl16.tof,
                            runno,
                            group
                        ]
                        self.plot_list_dict['other_list'][name] = plot_data
                        self.update_plot_list_simple.emit(self.other_list, self.plot_list_dict['other_list'])

                    for i in range(len(sam_plot_data)):
                        runno = bl16.conf["sam_run"][0]
                        added_suffix = 0
                        new_suffix = bl16.suffix[:-4] + f'_{added_suffix}'
                        name = 'sam_' + runno + "_" + group + '_' + new_suffix
                        if name in self.plot_list_dict['sam_list']:
                            # 键已存在，添加一个后缀
                            added_suffix += 1
                            new_suffix = bl16.suffix[:-4] + f'_{added_suffix}'
                            new_name = 'sam_' + runno + "_" + group + '_' + new_suffix
                            while new_name in self.plot_list_dict['sam_list']:
                                added_suffix += 1
                                new_suffix = bl16.suffix[:-4] + f'_{added_suffix}'
                                new_name = 'sam_' + runno + "_" + group + '_' + new_suffix
                            name = new_name
                        plot_data = [
                            sam_plot_data[f'{bl16.label_list[i]}'][0],
                            sam_plot_data[f'{bl16.label_list[i]}'][1],
                            sam_plot_data[f'{bl16.label_list[i]}'][2],
                            bl16.tof,
                            runno,
                            group
                        ]
                        self.plot_list_dict['sam_list'][name] = plot_data
                        self.update_plot_list.emit(self.sam_list, self.plot_list_dict['sam_list'], self.filterbox.get_selected())
                        name_elements = name.split('_')
                        filter_elements = self.filterbox.get_item_names()
                        for name_element in name_elements:
                            if name_element not in filter_elements:
                                self.add_item_signal.emit(name_element)

                    j = j + 1
                    k = int(j / (len(bl16.conf["group_list"]) * len(bl16.conf['sam_run'])) * 100)
                    self.update_progress.emit(k)  # 发出进度更新信号

            except Exception as e:
                print(f"An error occurred: {e}")
                traceback.print_exc()  # 打印异常的堆栈跟踪

    def stop(self):
        self._is_running = False  # 设置标志以停止线程