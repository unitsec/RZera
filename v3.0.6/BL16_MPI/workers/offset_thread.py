from PyQt5.QtCore import QThread,pyqtSignal,Qt
from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QSplitter
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
import traceback
import numpy as np
from rongzai.algSvc.instrument.timefocus_correction import correct_tof_to_d
from rongzai.dataSvc import load_histogram_data
from rongzai.dataSvc import read_cal
from rongzai.algSvc.neutron import mask_neutron_data,focus_neutron_data,calculate_neutron_data
from CSNS_Alg.CSNS_offset_new import CSNS_Offset, Offset_Plot
from utils.process_dialog import ProgressDialog
from BL16_MPI.workers.ui_mapping import mapping, offset_mapping, resultcheck_mapping
import json
from BL16_MPI.workers.offset_check import offset_run_check, offset_check_check, offset_result_check
import os
import sys


class start_offset_thread:
    def __init__(self,parent=None):
        self.offset_thread = None  # 初始化为 None
        # 初始化进度对话框
        self.progress_dialog = ProgressDialog(parent)
        self.offset_config = {}

    def start_offset(self,window,run_filePaths, run_button):
        try:
            self.offset_config = mapping(window,self.offset_config)

            # 添加这一行的原因是：由于界面的开发时间较早，后续代码中增加了一些新参数，界面中是没有的。所以在这里手动添加这些参数防止界面运行代码出错。
            # 这只是权宜之计，因为这样设置参数相当于关闭了这些参数的相关功能，用户无法调节。
            self.offset_config["is_c0_0"] = False
            self.offset_config["T0_offset"] = 0.0
            self.offset_config["parallel"] = True

            if not offset_run_check(window, self.offset_config):
                return

            # 如果是 PyInstaller 打包后的临时目录中运行
            if getattr(sys, 'frozen', False):
                # 获取 PyInstaller 打包后的临时目录路径
                temp_dir = getattr(sys, '_MEIPASS', os.path.abspath(os.path.dirname(sys.executable)))
                bl16_config = os.path.join(temp_dir, 'CSNS_Alg', 'configure', 'BL16_base_new.json')
            else:
                # 如果是在源码中运行
                temp_dir = os.path.abspath(os.path.dirname(__file__))
                bl16_config = os.path.join(os.path.dirname(temp_dir), '..', 'CSNS_Alg', 'configure',
                                           'BL16_base_new.json')
            with open(bl16_config, 'r', encoding='utf-8') as json_file:
                bl16_configure = json.load(json_file)

            self.offset_config = offset_mapping(run_filePaths,self.offset_config)

            run_button.setEnabled(False)
            run_button.setText('Running')
            self.offset_thread = offset_thread(self.offset_config, bl16_configure)
            # 连接信号
            self.offset_thread.update_progress.connect(self.progress_dialog.update_progress)
            self.offset_thread.finished.connect(lambda: self.on_offset_thread_finished(run_button))
            self.progress_dialog.update_progress(0)
            self.progress_dialog.canceled.connect(self.offset_thread.stop)
            self.progress_dialog.show()  # 添加这一行来显示进度对话框
            self.offset_thread.start()
        except Exception as e:
            print(f"An error occurred: {e}")
            traceback.print_exc()  # 打印异常的堆栈跟踪

    def on_offset_thread_finished(self, run_button):
        try:
            run_button.setText('Run')
            run_button.setEnabled(True)
            self.progress_dialog.accept()

        except Exception as e:
            print(f"An error occurred: {e}")
            traceback.print_exc()  # 打印异常的堆栈跟踪


class offset_thread(QThread):
    update_progress = pyqtSignal(int)

    def __init__(self,  offset_config, base_config):
        super(offset_thread, self).__init__()
        self.offset_config = offset_config
        self.base_config = base_config
        self.detector_list = self.offset_config['selected_group']
        self._is_running = True  # 控制线程运行的标志

    def run(self):
        try:
            j = 0
            j_sum = len(self.detector_list)
            for group in self.detector_list:

                # 检查点：检查是否需要停止线程
                if not self._is_running:
                    break  # 如果停止标志被设置为 False，则退出循环

                task = CSNS_Offset(self.base_config, self.offset_config, group, ui=True)
                task.calculate_offset()
                j = j + 1
                k = int(j / j_sum * 100)
                self.update_progress.emit(k)  # 发出进度更新信号
        except:
            traceback.print_exc()

    def stop(self):
        self._is_running = False  # 设置标志以停止线程


class start_paracheck_process:
    def __init__(self, window,run_button):
        self.window = window

        self.run_button = run_button
        self.bank_group = {
            "group2": [10203, 11303],
            "group3": [10303, 10304, 11203, 11204],
            "group4": [10403, 10404, 10405, 11104, 11105],
            "group5": [10503, 10504, 10505, 11003, 11004, 11005],
            "group6": [10602, 10603, 10902, 10903],
            "group7": [10701, 10702, 10703, 10704, 10801, 10802, 10803, 10804]
        }
        self.offset_config = {}

    def start_check(self, run_filePaths):
        try:
            self.offset_config = mapping(self.window,self.offset_config)

            self.offset_config["is_c0_0"] = False
            self.offset_config["T0_offset"] = 0.0
            self.offset_config["parallel"] = False

            if not offset_check_check(self.window, self.offset_config, self.bank_group):
                return

            # 如果是 PyInstaller 打包后的临时目录中运行
            if getattr(sys, 'frozen', False):
                # 获取 PyInstaller 打包后的临时目录路径
                temp_dir = getattr(sys, '_MEIPASS', os.path.abspath(os.path.dirname(sys.executable)))
                bl16_config = os.path.join(temp_dir, 'bl16_base.json')
            else:
                # 如果是在源码中运行
                temp_dir = os.path.abspath(os.path.dirname(__file__))
                bl16_config = os.path.join(os.path.dirname(temp_dir), '..', 'CSNS_Alg', 'configure',
                                           'BL16_base.json')
            with open(bl16_config, 'r', encoding='utf-8') as json_file:
                bl16_configure = json.load(json_file)

            self.offset_config = offset_mapping(run_filePaths, self.offset_config, mode='check',bank_group=self.bank_group)

            self.run_button.setEnabled(False)
            self.run_button.setText('Checking')

            task = CSNS_Offset(bl16_configure, self.offset_config, self.offset_config['selected_module'][0],ui=True)
            plot_info_all = task.calculate_offset()
            plot_info = plot_info_all[0][self.offset_config['check_point']]
            dialog = PlotWindow(plot_info, parent=self.window)
            dialog.exec_()


            self.run_button.setText('Check Parameter')
            self.run_button.setEnabled(True)

        except Exception as e:
            print(f"An error occurred: {e}")
            traceback.print_exc()  # 打印异常的堆栈跟踪

class PlotWindow(QtWidgets.QDialog):
    def __init__(self, plot_info, parent=None):
        super().__init__(parent)
        self.setWindowTitle(plot_info[0][0])
        self.setGeometry(100, 100, 1200, 800)  # 设置窗口初始大小

        # 设置窗口标志，确保显示最小化、最大化和关闭按钮
        self.setWindowFlags(self.windowFlags() | Qt.WindowMinMaxButtonsHint | Qt.WindowCloseButtonHint)

        self.plotter = Offset_Plot()

        self.figure1, self.ax1 = self.plotter.plot_check(
            plot_info[0][0], plot_info[0][1], plot_info[0][2], plot_info[0][3],
            plot_info[0][4], plot_info[0][5], plot_info[0][6], plot_info[0][7]
        )
        if len(plot_info) > 1:
            self.figure2, self.ax2 = self.plotter.plot_fitted_curve(
                plot_info[1][0], plot_info[1][1], plot_info[1][2], plot_info[1][3]
            )
        if len(plot_info) > 2:
            self.figure3, self.ax3 = self.plotter.plot_offset_data(
                plot_info[2][0], plot_info[2][1], plot_info[2][2], plot_info[2][3], plot_info[2][4]
            )

        self.canvas1 = FigureCanvas(self.figure1)
        self.toolbar1 = NavigationToolbar(self.canvas1, self)
        if len(plot_info) > 1:
            self.canvas2 = FigureCanvas(self.figure2)
            self.toolbar2 = NavigationToolbar(self.canvas2, self)
        if len(plot_info) > 2:
            self.canvas3 = FigureCanvas(self.figure3)
            self.toolbar3 = NavigationToolbar(self.canvas3, self)

        splitter = QSplitter(Qt.Vertical)
        splitter.addWidget(self.canvas1)
        splitter.addWidget(self.toolbar1)
        if len(plot_info) > 1:
            splitter.addWidget(self.canvas2)
            splitter.addWidget(self.toolbar2)
        if len(plot_info) > 2:
            splitter.addWidget(self.canvas3)
            splitter.addWidget(self.toolbar3)

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(splitter)
        self.setLayout(layout)

        self.canvas1.draw()
        if len(plot_info) > 1:
            self.canvas2.draw()
        if len(plot_info) > 2:
            self.canvas3.draw()

class start_resultcheck_process:
    def __init__(self, window, run_button, parent=None):
        self.resultcheck_thread = None  # 初始化为 None
        # 初始化进度对话框
        self.progress_dialog = ProgressDialog(parent)
        self.window = window
        self.run_button = run_button
        self.bank_group = {
            "group2": [10203, 11303],
            "group3": [10303, 10304, 11203, 11204],
            "group4": [10403, 10404, 10405, 11104, 11105],
            "group5": [10503, 10504, 10505, 11003, 11004, 11005],
            "group6": [10602, 10603, 10902, 10903],
            "group7": [10701, 10702, 10703, 10704, 10801, 10802, 10803, 10804]
        }
        self.offset_config = {}

    def start_check(self,run_filePaths):
        try:
            self.offset_config = mapping(self.window,self.offset_config)
            self.offset_config["T0_offset"] = 0.0
            if not offset_result_check(self.window, self.offset_config):
                return

            # 如果是 PyInstaller 打包后的临时目录中运行
            if getattr(sys, 'frozen', False):
                # 获取 PyInstaller 打包后的临时目录路径
                temp_dir = getattr(sys, '_MEIPASS', os.path.abspath(os.path.dirname(sys.executable)))
                bl16_config = os.path.join(temp_dir, 'BL16_base_new.json')
            else:
                # 如果是在源码中运行
                temp_dir = os.path.abspath(os.path.dirname(__file__))
                bl16_config = os.path.join(os.path.dirname(temp_dir), '..', 'CSNS_Alg', 'configure',
                                           'BL16_base_new.json')
            with open(bl16_config, 'r', encoding='utf-8') as json_file:
                bl16_configure = json.load(json_file)

            self.offset_config = resultcheck_mapping(run_filePaths, self.offset_config)

            self.run_button.setEnabled(False)
            self.run_button.setText('Checking')

            self.resultcheck_thread = resultcheck_thread(self.offset_config, bl16_configure)
            # 连接信号
            self.resultcheck_thread.update_progress.connect(self.progress_dialog.update_progress)
            self.resultcheck_thread.plotinfo_signal.connect(self.plot_result)
            self.resultcheck_thread.finished.connect(lambda: self.on_resultcheck_thread_finished(self.run_button))
            self.progress_dialog.update_progress(0)
            self.progress_dialog.canceled.connect(self.resultcheck_thread.stop)
            self.progress_dialog.show()  # 添加这一行来显示进度对话框
            self.resultcheck_thread.start()
        except Exception as e:
            print(f"An error occurred: {e}")
            traceback.print_exc()  # 打印异常的堆栈跟踪

    def on_resultcheck_thread_finished(self, run_button):
        try:
            run_button.setText('Result Check')
            run_button.setEnabled(True)
            self.progress_dialog.accept()

        except Exception as e:
            print(f"An error occurred: {e}")
            traceback.print_exc()  # 打印异常的堆栈跟踪

    def plot_result(self,plot_para,d_std):
        dialog = PlotWindow_2(plot_para,d_std, parent=self.window)
        dialog.exec_()

class PlotWindow_2(QtWidgets.QDialog):
    def __init__(self, plot_para,d_std, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Result Check')
        self.setGeometry(100, 100, 1200, 800)  # 设置窗口初始大小

        # 设置窗口标志，确保显示最小化、最大化和关闭按钮
        self.setWindowFlags(self.windowFlags() | Qt.WindowMinMaxButtonsHint | Qt.WindowCloseButtonHint)

        self.plotter = Offset_Plot()

        self.figure, self.ax = self.plotter.plot_result_data(plot_para,d_std)
        self.canvas = FigureCanvas(self.figure)
        self.toolbar = NavigationToolbar(self.canvas, self)

        splitter = QSplitter(Qt.Vertical)
        splitter.addWidget(self.canvas)
        splitter.addWidget(self.toolbar)

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(splitter)
        self.setLayout(layout)

        self.canvas.draw()



class resultcheck_thread(QThread):
    update_progress = pyqtSignal(int)
    plotinfo_signal = pyqtSignal(list,list)

    def __init__(self,  offset_config, base_config):
        super(resultcheck_thread, self).__init__()
        self.offset_config = offset_config
        self.base_config = base_config
        self.detector = self.offset_config['selected_detector']
        self._is_running = True  # 控制线程运行的标志

    def run(self):
        try:
            if self.detector[:5] == 'group':
                selected_detector = self.base_config['group_info'][self.detector].copy()
                selected_detector.append(self.detector)
            elif self.detector[:4] == 'bank':
                selected_detector = self.base_config['bank_info'][self.detector].copy()
                selected_detector.append(self.detector)
            elif self.detector[:6] == 'module':
                selected_detector = [self.detector].copy()
                pixel_range = self.offset_config['selected_pixels']
                x_list,y_list = [],[]
            j = 0
            j_sum = len(selected_detector)
            plot_para = []
            for detector in selected_detector:

                # 检查点：检查是否需要停止线程
                if not self._is_running:
                    break  # 如果停止标志被设置为 False，则退出

                task = CSNS_Offset(self.base_config, self.offset_config, detector, ui=True)

                for i,module in enumerate(task.moduleList):
                    dataset = load_histogram_data(task.conf["sample_fns"], f'{task.conf["param_path"]}/{module}.txt',
                                                  module, task.conf["first_flight_distance"],
                                                  x_offset=float(task.conf["T0_offset"]))
                    cal_fn = task.conf["save_path"] + "/" + module + "_offset.cal"
                    cal_dict = read_cal(cal_fn)
                    data_d = correct_tof_to_d(dataset, cal_dict)
                    data_d = mask_neutron_data(data_d, cal_dict["mask_list"])
                    if self.detector[:6] == 'module':
                        x = data_d["xvalue"].values[pixel_range[0]:pixel_range[1]]
                        y = data_d["histogram"].values[pixel_range[0]:pixel_range[1]]
                        mat = np.stack(y).astype(float)  # 变成 2D 浮点矩阵
                        row_max = mat.max(axis=1, keepdims=True)
                        np.divide(mat, row_max, out=mat, where=row_max > 0)  # 避免除 0
                        x_list.append(x)
                        y_list.append(mat)
                    data_d_focused = focus_neutron_data(data_d, None)
                    if i == 0:
                        data_sum = data_d_focused
                    else:
                        data_sum = calculate_neutron_data("add", data_sum, data_d_focused)
                x_sum, y_sum = data_sum["xvalue"].values[0], data_sum["histogram"].values[0]
                if y_sum.max() > 0:
                    y_sum/=y_sum.max()
                if self.detector[:6] == 'module':
                    plot_para.append([detector, x_sum, y_sum, x_list, y_list, pixel_range])
                else:
                    plot_para.append([detector,x_sum,y_sum])
                j = j + 1
                k = int(j / j_sum * 100)
                self.update_progress.emit(k)  # 发出进度更新信号
            d_std = task.conf["d_std"]
            self.plotinfo_signal.emit(plot_para,d_std)

        except:
            traceback.print_exc()

    def stop(self):
        self._is_running = False  # 设置标志以停止线程


