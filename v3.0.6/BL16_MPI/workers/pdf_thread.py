from PyQt5.QtCore import QThread,pyqtSignal
import traceback
from CSNS_Alg.CSNS_PDF import CSNS_PDF
from rongzai.algSvc.base import rebin
from BL16_MPI.workers.plot_item_operation import change_item
from PyQt5.QtCore import Qt
import re
from rongzai.utils import merge_all_curves
from rongzai.algSvc.base.calculate_sample import CalSampleProperty
from BL16_MPI.workers.ui_mapping import pdf_mapping
from BL16_MPI.workers.reduction_check import sq_reduction_check
import json
import numpy as np
from utils.process_dialog import ProgressDialog
import os
import sys


class start_pdf_thread:
    def __init__(self,sam_list,other_list,plot_list_dict,parent=None):
        self.sqcal_thread = None  # 初始化为 None
        # 初始化进度对话框
        self.parent = parent
        self.sam_list = sam_list
        self.other_list = other_list
        self.progress_dialog = ProgressDialog(parent)
        self.change_sam_item = change_item(sam_list, plot_list_dict['sam_list'])
        self.change_other_item = change_item(other_list, plot_list_dict['other_list'])

    def start_sqcal(self,window,pdf_config,num_dens, pdf_cal_sq):

        try:
            # 如果是 PyInstaller 打包后的临时目录中运行
            if getattr(sys, 'frozen', False):
                # 获取 PyInstaller 打包后的临时目录路径
                temp_dir = getattr(sys, '_MEIPASS', os.path.abspath(os.path.dirname(sys.executable)))
                bl16_config = os.path.join(temp_dir, 'BL16_base.json')
            else:
                # 如果是在源码中运行
                temp_dir = os.path.abspath(os.path.dirname(__file__))
                bl16_config = os.path.join(temp_dir, '..', '..', 'CSNS_Alg', 'configure', 'BL16_base.json')

            with open(bl16_config, 'r', encoding='utf-8') as json_file:
                bl16_configure = json.load(json_file)

            pdf_config,bl16_configure = pdf_mapping(window,pdf_config,bl16_configure)
            if not sq_reduction_check(window,pdf_config,bl16_configure):
                return

            pdf_cal_sq.setEnabled(False)
            pdf_cal_sq.setText('Calculating')
            # if pdf_config['mode'] == 'offline':
            self.sqcal_thread = sqcal_thread(pdf_config,bl16_configure)
            # 连接信号
            self.sqcal_thread.update_text_signal.connect(num_dens.setText)
            self.sqcal_thread.update_list_signal.connect(self.set_list)
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
            self,window,pdf_config,plot_list,plot_list_dict,pdf_merge):

        try:
            pdf_merge.setEnabled(False)
            pdf_merge.setText('Merging')

            if getattr(sys, 'frozen', False):
                # 获取 PyInstaller 打包后的临时目录路径
                temp_dir = getattr(sys, '_MEIPASS', os.path.abspath(os.path.dirname(sys.executable)))
                bl16_config = os.path.join(temp_dir, 'BL16_base.json')
            else:
                # 如果是在源码中运行
                temp_dir = os.path.abspath(os.path.dirname(__file__))
                bl16_config = os.path.join(temp_dir, '..', '..', 'CSNS_Alg', 'configure', 'BL16_base.json')

            with open(bl16_config, 'r', encoding='utf-8') as json_file:
                bl16_configure = json.load(json_file)

            pdf_config,bl16_configure = pdf_mapping(window, pdf_config,bl16_configure)
            self.merge_thread = merge_thread(pdf_config, bl16_configure,plot_list,plot_list_dict)
            # 连接信号
            self.merge_thread.update_list_signal.connect(self.set_list)
            # self.sqcal_thread.update_progress.connect(self.progress_dialog.update_progress)
            self.merge_thread.finished.connect(
                lambda: self.on_merge_thread_finished(pdf_merge))
            # self.progress_dialog.update_progress(0)
            # self.progress_dialog.canceled.connect(self.reduction_thread.stop)
            # self.progress_dialog.show()  # 添加这一行来显示进度对话框
            self.merge_thread.start()
        except Exception as e:
            print(f"An error occurred: {e}")
            traceback.print_exc()  # 打印异常的堆栈跟踪

    def on_merge_thread_finished(self, pdf_merge):
        try:
            pdf_merge.setText('Merge S(Q)')
            pdf_merge.setEnabled(True)
            # self.progress_dialog.accept()
        except Exception as e:
            print(f"An error occurred: {e}")
            traceback.print_exc()  # 打印异常的堆栈跟踪

    def set_list(self,name,info):
        try:
            if name[:4] == 'sam_':
                if name in self.parent.plot_list_dict['sam_list']:
                    # 键已存在，添加一个后缀
                    suffix = 1
                    new_name = f"{name}_{suffix}"
                    while new_name in self.parent.plot_list_dict['sam_list']:
                        suffix += 1
                        new_name = f"{name}_{suffix}"
                    name = new_name
                self.parent.plot_list_dict['sam_list'][name] = info
                self.change_sam_item.setup_plot_list(self.sam_list, self.parent.plot_list_dict['sam_list'])
            elif name[0:6] == "stitch":
                if name in self.parent.plot_list_dict:
                    # 键已存在，添加一个后缀
                    suffix = 1
                    new_name = f"{name}_{suffix}"
                    while new_name in self.parent.plot_list_dict:
                        suffix += 1
                        new_name = f"{name}_{suffix}"
                    name = new_name
                self.parent.plot_list_dict['sam_list'][name] = info
                self.change_sam_item.setup_plot_list(self.sam_list, self.parent.plot_list_dict['sam_list'])
            else:
                self.parent.plot_list_dict['other_list'][name] = info
                self.change_other_item.setup_plot_list(self.other_list, self.parent.plot_list_dict['other_list'])

        except Exception as e:
            print(f"An error occurred: {e}")
            traceback.print_exc()  # 打印异常的堆栈跟踪



class sqcal_thread(QThread):
    update_progress = pyqtSignal(int)
    update_text_signal = pyqtSignal(str)
    update_list_signal = pyqtSignal(str,list)
    def __init__(self,pdf_config,bl16_config):
        super(sqcal_thread, self).__init__()
        self.pdf_configure = pdf_config
        self.bl16_configure = bl16_config
        self._is_running = True  # 控制线程运行的标志

    def run(self):
        try:
            bl16 = CSNS_PDF(self.bl16_configure,self.pdf_configure,auto_save=False)
            groupList = list(bl16.conf["group_info"].keys())
            detectorList = groupList  + bl16.moduleList

            # 对样品判断使用原子数密度的计算值还是给定值
            if bl16.conf['num_dens_text'] != '' and bl16.conf['num_dens_check'] is True:
                with open(bl16.conf["nist_fn"], 'r') as jf:
                    nist_conf = json.load(jf)
                task = CalSampleProperty(nist_conf, bl16.conf)
                bl16.conf['sample_property']['atom_num'] = float(
                    bl16.conf['num_dens_text']) * task.cal_beam_volume()
            elif bl16.conf['num_dens_check'] is False or bl16.conf['num_dens_text'] == '':
                text_to_set = str(bl16.conf['sample_property']['density_num'])
                self.update_text_signal.emit(text_to_set)

            j = 0
            bl16.calibration()
            for detector in detectorList:
                x,y,e, x_v, y_v, e_v, x_samBG, y_samBG, e_samBG, x_vBG, y_vBG, e_vBG = bl16.cal_sq_detector(detector)

                suffix = '_d'
                if bl16.conf["norm_by_pc"]:
                    suffix = "_pc" + suffix
                runno = bl16.conf["v_run"][0]
                name = "v_" + runno + "_" + detector + suffix
                self.update_list_signal.emit(name,[x_v, y_v, e_v, runno])

                runno = bl16.conf["samBG_run"][0]
                name = "samBG_" + runno + "_" + detector + suffix
                self.update_list_signal.emit(name, [x_samBG, y_samBG, e_samBG, runno])

                runno = bl16.conf["vBG_run"][0]
                name = "vBG_" + runno + "_" + detector + suffix
                self.update_list_signal.emit(name, [x_vBG, y_vBG, e_vBG, runno])

                runno = bl16.conf["sam_run"][0]
                if bl16.conf["norm_by_pc"]:
                    name = "sam_" + runno + "_" + detector + '_pc_sq'
                else:
                    name = "sam_" + runno + "_" + detector + '_sq'
                self.update_list_signal.emit(name, [x, y, e, runno])

                # 更新进度条
                j = j + 1
                k = int(j / len(detectorList) * 100)
                self.update_progress.emit(k)

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
    update_list_signal = pyqtSignal(str, list)
    def __init__(self, pdf_config,bl16_config, plot_list, plot_list_dict):
        super(merge_thread, self).__init__()
        self.pdf_configure = pdf_config
        self.bl16_configure = bl16_config
        self.plot_list = plot_list
        self.plot_list_dict = plot_list_dict
        self._is_running = True  # 控制线程运行的标志

    def run(self):
        try:
            bl16 = CSNS_PDF(self.bl16_configure, self.pdf_configure, auto_save=False)
            data_pairs = []
            stitch_detectors = []
            for index in range(1, self.plot_list.count()):  # 从 1 开始，跳过 "ALL" 条目
                item = self.plot_list.item(index)
                if item.checkState() == Qt.Checked:
                    [x,y,e,_] = self.plot_list_dict[item.text()]
                    data_pairs.append((x, y, e))
                    if '_pc' in self.plot_list.item(index).text():
                        stitch_detectors.append(re.findall(r'module\d+_pc|group\d+_pc', self.plot_list.item(index).text())[-1])
                    else:
                        stitch_detectors.append(re.findall(r'module\d+|group\d+', self.plot_list.item(index).text())[-1])
            x, y, e = bl16.stitch_modules_ui(data_pairs)
            name = "stitch_" + '_'.join(stitch_detectors) + "_sq"
            self.update_list_signal.emit(name, [x, y, e, stitch_detectors])

        except Exception as e:
            print(f"An error occurred: {e}")
            traceback.print_exc()  # 打印异常的堆栈跟踪

    def stop(self):
        self._is_running = False  # 设置标志以停止线程