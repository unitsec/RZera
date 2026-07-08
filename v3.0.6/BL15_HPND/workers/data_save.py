from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QFileDialog
from rongzai.dataSvc.write_format import write_ascii
from CSNS_Alg.data_save import diffraction_format
# from rongzai.algSvc.instrument.CSNS_PDF import CSNS_PDF
# from drneutron.python.algSvc.base import (interpolate,cal_PDF,merge_all_curves,rebin,
                        # generate_x,strip_peaks,smooth)
import json
import os
import sys
import traceback
import numpy as np


def save_diff_small(window, diff_config, sam_list, other_list, plot_list_dict):
    options = QFileDialog.Options()
    # 获取用户选择的目录
    directory = QFileDialog.getExistingDirectory(window, "Select Directory", options=options)
    try:
        if directory:

            # 如果是 PyInstaller 打包后的临时目录中运行
            if getattr(sys, 'frozen', False):
                # 获取 PyInstaller 打包后的临时目录路径
                temp_dir = getattr(sys, '_MEIPASS', os.path.abspath(os.path.dirname(sys.executable)))
                bl16_config = os.path.join(temp_dir, 'BL15_small_base.json')
            else:
                # 如果是在源码中运行
                temp_dir = os.path.abspath(os.path.dirname(__file__))
                bl16_config = os.path.join(temp_dir, '..', '..', 'CSNS_Alg', 'configure', 'BL15_small_base.json')

            with open(bl16_config, 'r', encoding='utf-8') as json_file:
                bl16_configure = json.load(json_file)
            configure = {**diff_config, **bl16_configure}
            # suffix = '_d'
            # if configure["normByPC"]:
            #     suffix = "_pc"+suffix
            for index in range(1, sam_list.count()):  # 从 1 开始，跳过 "ALL" 条目
                item = sam_list.item(index)
                if item.checkState() == Qt.Checked:
                    [x, y, e, tof, runno, bank] = plot_list_dict['sam_list'][item.text()]
                    filename = item.text()[:-4] + item.text()[-2:]
                    configure['current_runno'] = runno
                    configure['current_bank'] = bank
                    sam_directory = directory + "/" + runno
                    os.makedirs(sam_directory, exist_ok=True)  # exist_ok=True 表示如果目录已存在则忽略创建，否则会抛出异常
                    configure['save_path'] = sam_directory
                    output = diffraction_format(configure)
                    output.writeGSAS(tof, y, e,sam_directory,filename)
                    output.writeZR(tof, y, e,sam_directory,filename)
                    output.writeFP(tof, y, e,sam_directory,filename)
                    path = sam_directory + '/' + item.text() + '.dat'
                    write_ascii(path, x, y, e)
                    path = sam_directory + '/' + item.text()[:-4] + '_q' + item.text()[-2:] + '.dat'
                    q = 2 * np.pi / x
                    data = np.array([q, y, e])  # 将 q, y, e 组合成一个二维的 NumPy 数组，每一行是一个观测值
                    sorted_indices = np.argsort(q)  # 对数据按照 q 的值进行排序，这里 argsort() 会返回排序后的索引
                    sorted_data = data[:, sorted_indices]  # 使用排序后的索引来重新排列原数据数组
                    # 分别提取排序后的 q, y, e
                    q_sorted = sorted_data[0]
                    y_sorted = sorted_data[1]
                    e_sorted = sorted_data[2]
                    write_ascii(path, q_sorted, y_sorted, e_sorted)

            for index in range(1, other_list.count()):  # 从 1 开始，跳过 "ALL" 条目
                item = other_list.item(index)
                if item.checkState() == Qt.Checked:
                    [x, y, e, _, runno, _] = plot_list_dict['other_list'][item.text()]
                    other_directory = directory + "/" + runno
                    os.makedirs(other_directory, exist_ok=True)
                    path = other_directory + '/' + item.text() + '.dat'
                    write_ascii(path, x, y, e)

    except Exception as e:
        print(f"An error occurred: {e}")
        traceback.print_exc()  # 打印异常的堆栈跟踪

def save_diff_big(window, diff_config, sam_list, other_list, plot_list_dict):
    options = QFileDialog.Options()
    # 获取用户选择的目录
    directory = QFileDialog.getExistingDirectory(window, "Select Directory", options=options)
    try:
        if directory:

            # 如果是 PyInstaller 打包后的临时目录中运行
            if getattr(sys, 'frozen', False):
                # 获取 PyInstaller 打包后的临时目录路径
                temp_dir = getattr(sys, '_MEIPASS', os.path.abspath(os.path.dirname(sys.executable)))
                bl16_config = os.path.join(temp_dir, 'BL15_big_base.json')
            else:
                # 如果是在源码中运行
                temp_dir = os.path.abspath(os.path.dirname(__file__))
                bl16_config = os.path.join(temp_dir, '..', '..', 'CSNS_Alg', 'configure', 'BL15_big_base.json')

            with open(bl16_config, 'r', encoding='utf-8') as json_file:
                bl16_configure = json.load(json_file)
            configure = {**diff_config, **bl16_configure}
            # suffix = '_d'
            # if configure["normByPC"]:
            #     suffix = "_pc"+suffix
            for index in range(1, sam_list.count()):  # 从 1 开始，跳过 "ALL" 条目
                item = sam_list.item(index)
                if item.checkState() == Qt.Checked:
                    [x, y, e, tof, runno, bank] = plot_list_dict['sam_list'][item.text()]
                    filename = item.text()[:-4] + item.text()[-2:]
                    configure['current_runno'] = runno
                    configure['current_bank'] = bank
                    sam_directory = directory + "/" + runno
                    os.makedirs(sam_directory, exist_ok=True)  # exist_ok=True 表示如果目录已存在则忽略创建，否则会抛出异常
                    configure['save_path'] = sam_directory
                    output = diffraction_format(configure)
                    output.writeGSAS(tof, y, e,sam_directory,filename)
                    output.writeZR(tof, y, e,sam_directory,filename)
                    output.writeFP(tof, y, e,sam_directory,filename)
                    path = sam_directory + '/' + item.text() + '.dat'
                    write_ascii(path, x, y, e)
                    path = sam_directory + '/' + item.text()[:-4] + '_q' + item.text()[-2:] + '.dat'
                    q = 2 * np.pi / x
                    data = np.array([q, y, e])  # 将 q, y, e 组合成一个二维的 NumPy 数组，每一行是一个观测值
                    sorted_indices = np.argsort(q)  # 对数据按照 q 的值进行排序，这里 argsort() 会返回排序后的索引
                    sorted_data = data[:, sorted_indices]  # 使用排序后的索引来重新排列原数据数组
                    # 分别提取排序后的 q, y, e
                    q_sorted = sorted_data[0]
                    y_sorted = sorted_data[1]
                    e_sorted = sorted_data[2]
                    write_ascii(path, q_sorted, y_sorted, e_sorted)

            for index in range(1, other_list.count()):  # 从 1 开始，跳过 "ALL" 条目
                item = other_list.item(index)
                if item.checkState() == Qt.Checked:
                    [x, y, e, _, runno, _] = plot_list_dict['other_list'][item.text()]
                    other_directory = directory + "/" + runno
                    os.makedirs(other_directory, exist_ok=True)
                    path = other_directory + '/' + item.text() + '.dat'
                    write_ascii(path, x, y, e)

    except Exception as e:
        print(f"An error occurred: {e}")
        traceback.print_exc()  # 打印异常的堆栈跟踪