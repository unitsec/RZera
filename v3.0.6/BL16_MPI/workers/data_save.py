from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QFileDialog, QMessageBox
from rongzai.dataSvc.write_format import write_ascii
from CSNS_Alg.data_save import diffraction_format
from CSNS_Alg.CSNS_PDF import CSNS_PDF
# from drneutron.python.algSvc.base import (interpolate,cal_PDF,merge_all_curves,rebin,
                        # generate_x,strip_peaks,smooth)
from BL16_MPI.workers.ui_mapping import pdf_mapping,diff_mapping
import json
import os
import sys
import traceback
import numpy as np

def force_positive(x, warn_tag):
    for i, value in enumerate(x):
        if value < 0 or np.isnan(value) or (value == 0 and np.signbit(value)):
            x[i] = 0
            warn_tag = False
    return x, warn_tag


def save_diff(window, diff_config, sam_list, other_list, plot_list_dict):
    options = QFileDialog.Options()
    # 获取用户选择的目录
    directory = QFileDialog.getExistingDirectory(window, "Select Directory", options=options)
    try:
        if directory:

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
            configure = {**diff_config, **bl16_configure}
            # suffix = '_d'
            # if configure["normByPC"]:
            #     suffix = "_pc"+suffix
            for index in range(1, sam_list.count()):  # 从 1 开始，跳过 "ALL" 条目
                item = sam_list.item(index)
                warn_tag = True
                if item.checkState() == Qt.Checked:
                    [x, y, e, tof, runno, bank] = plot_list_dict['sam_list'][item.text()]
                    # 判断输出结果中是否有负数，告知用户
                    y, warn_tag = force_positive(y, warn_tag)
                    e, warn_tag = force_positive(e, warn_tag)
                    if not warn_tag:
                        QMessageBox.warning(window, "Output Check", f"Intensity of {item.text()} is negative, please check whether the back is too large.\n The result is still save, but the negative count set zero.")
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

def save_sq(window, sam_list, other_list, plot_list_dict):
    options = QFileDialog.Options()
    # 获取用户选择的目录
    directory = QFileDialog.getExistingDirectory(window, "Select Directory", options=options)
    try:
        if directory:
            for index in range(1, sam_list.count()):  # 从 1 开始，跳过 "ALL" 条目
                item = sam_list.item(index)
                if item.checkState() == Qt.Checked:
                    x, y, e, runno = plot_list_dict['sam_list'][item.text()]
                    # 创建文件名，假设 item.text() 是有效的文件名
                    filename = f"{item.text()}.txt"
                    if isinstance(runno, str):
                        sam_directory = directory + '/' + runno
                    else:
                        sam_directory = directory
                    os.makedirs(sam_directory, exist_ok=True)  # exist_ok=True 表示如果目录已存在则忽略创建，否则会抛出异常
                    # 完整的文件路径
                    full_filename = os.path.join(sam_directory, filename)
                    write_ascii(full_filename, x, y, e)

            for index in range(1, other_list.count()):  # 从 1 开始，跳过 "ALL" 条目
                item = other_list.item(index)
                if item.checkState() == Qt.Checked:
                    x, y, e, runno = plot_list_dict['other_list'][item.text()]
                    other_directory = directory + '/' + runno
                    os.makedirs(other_directory, exist_ok=True)  # exist_ok=True 表示如果目录已存在则忽略创建，否则会抛出异常
                    # 创建文件名，假设 item.text() 是有效的文件名
                    filename = f"{item.text()}.dat"
                    # 完整的文件路径
                    full_filename = os.path.join(other_directory, filename)
                    write_ascii(full_filename,x, y, e)

    except Exception as e:
        print(f"An error occurred: {e}")
        traceback.print_exc()  # 打印异常的堆栈跟踪


def save_pdf(window, pdf_config, plot_list, plot_list_dict):
    options = QFileDialog.Options()
    # 获取用户选择的目录
    directory = QFileDialog.getExistingDirectory(window, "Select Directory", options=options)

    if directory:
        try:
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

            pdf_config, bl16_config = pdf_mapping(window, pdf_config, bl16_configure)
            CSNS_PDF_instance = CSNS_PDF(bl16_config, pdf_config, auto_save=False)
            for index in range(1, plot_list.count()):  # 从 1 开始，跳过 "ALL" 条目
                item = plot_list.item(index)
                if item.checkState() == Qt.Checked:
                    [q, sq, sq_e, _] = plot_list_dict[item.text()]
                    r, data = CSNS_PDF_instance.PDF(q, sq, sq_e)
                    # newX = generate_x(pdf_config["q_rebin"][0],
                    #                   pdf_config["q_rebin"][1],
                    #                   pdf_config["q_rebin"][2], "uniform")
                    # newY, newE = interpolate(q, sq, sq_e, newX)
                    # r = generate_x(pdf_config["r_rebin"][0],
                    #                pdf_config["r_rebin"][1],
                    #                pdf_config["r_rebin"][2],
                    #                "uniform")
                    # 创建文件名，假设 item.text() 是有效的文件名
                    filename = f"{item.text()[:-3]}_{CSNS_PDF_instance.conf['PDF_type']}.dat"
                    # 完整的文件路径
                    full_filename = os.path.join(directory, filename)
                    write_ascii(full_filename, r, data,format="%.5f")
        except Exception as e:
            print(f"An error occurred: {e}")
            traceback.print_exc()  # 打印异常的堆栈跟踪