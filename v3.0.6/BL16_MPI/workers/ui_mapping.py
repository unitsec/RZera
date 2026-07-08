from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QLineEdit, QComboBox, QCheckBox, QRadioButton, QLabel
import traceback
import json
from PyQt5.QtWidgets import QFileDialog
import re
from utils.helper import extract_number
from pathlib import Path
import sys
import os
import glob
from collections import defaultdict
from BL16_MPI.workers.operate_slicepara import read_start_pulseID


def mapping(window,config):
    for name, obj in vars(window).items():
        if isinstance(obj, QCheckBox):
            config[name] = obj.isChecked()
        elif isinstance(obj, QComboBox):
            config[name] = obj.currentText()
        elif isinstance(obj, QLineEdit):
            config[name] = obj.text()
        elif isinstance(obj, QRadioButton):
            config[name] = obj.isChecked()
        elif isinstance(obj, QLabel):
            config[name] = obj.text()
    return config


def load_mapping(window, config):

    for name, value in config.items():
        if hasattr(window, name):
            obj = getattr(window, name)
            if isinstance(obj, QComboBox):
                index = obj.findText(value)
                if index >= 0:
                    obj.setCurrentIndex(index)
            elif isinstance(obj, QCheckBox):
                obj.setChecked(value)
            elif isinstance(obj, QRadioButton):
                obj.setChecked(value)
            elif isinstance(obj, QLabel):
                obj.setText(value)

    # 为QlineEdit单独开一个循环，确保后加载QLineEdit。
    # 因为，"nxs"和“dat"切换时，会清空对应的QLineEdit中的文本；如果加载配置时先加载了QLineEdit，会有被再次清空的危险。所以必须保证后加载QLineEdit。
    for name, value in config.items():
        if hasattr(window, name):
            obj = getattr(window, name)
            if isinstance(obj, QLineEdit):
                obj.setText(value)



def diff_mapping(window, diff_config, base_config):
    diff_config = mapping(window,diff_config)

    # diff_config['mode'] = mode.currentText()
    # diff_config['param_path'] = diff_config['instru_path_text']
    # diff_config['cal_path'] = diff_config['offset_file_text']
    # diff_config['has_cal'] = diff_config['offset_correction_check']
    # diff_config['is_batch'] = diff_config['batch_reduction_check']

    # 检查列表中的所有文件名是否都符合格式，并提取数字
    all_have_number = all(extract_number(Path(path).name) is not None for path in diff_config['sam_fn'])
    if all_have_number and diff_config['is_batch'] == True:
        # 如果所有文件名都有数字，则按照数字大小排序
        sorted_paths = sorted(diff_config['sam_fn'], key=lambda p: extract_number(Path(p).name))
        diff_config['sam_fn'] = sorted_paths
        print("Sorted file paths:", diff_config['sam_fn'])
    else:
        all_have_number = False

    diff_config['time_slice'] = all_have_number
    diff_config['sam_run'] = [re.findall(r'RUN\d+', path)[-1] for path in diff_config['sam_fn']]
    diff_config['samBG_run_mode'] = diff_config['sambkg_mode']
    diff_config['v_run_mode'] = diff_config['van_run_mode']
    diff_config['v_fn'] = diff_config['v_fn'] if diff_config['v_run_mode'] == 'nxs' else [diff_config['van_run_text']]

    if diff_config['v_check'] is True:
        if diff_config['v_run_mode'] == 'nxs':
            diff_config['v_run'] = [re.findall(r'RUN\d+', path)[-1] for path in diff_config['v_fn']]
        else:
            matches = re.findall(r'RUN\d+', diff_config['van_run_text'])
            diff_config['v_run'] = [matches[-1]] if matches else []
    else:
        diff_config['v_run'] = []

    if diff_config['v'] is True:
        diff_config["vanadium_name"] = 'V'
    elif diff_config['vni'] is True:
        diff_config["vanadium_name"] = 'VNi'

    if window.num_dens.isEnabled():
        base_config['vanadium_correction']['density_num'] = float(diff_config['num_dens']) if diff_config['num_dens'].strip() else base_config['vanadium_correction']['density_num']
    if window.van_radius.isEnabled():
        base_config['vanadium_correction']['radius'] = float(diff_config['van_radius']) if diff_config[
            'van_radius'].strip() else base_config['vanadium_correction']['radius']

    diff_config['samBG_fn'] = diff_config['samBG_fn'] if diff_config['sambkg_mode'] == 'nxs' else [diff_config[
        'sambkg_text']]

    if diff_config['sambkg_check'] is True:
        if diff_config['sambkg_mode'] == 'nxs':
            diff_config['samBG_run'] = [re.findall(r'RUN\d+', path)[-1] for path in diff_config['samBG_fn']]
        else:
            matches = re.findall(r'RUN\d+', diff_config['sambkg_text'])
            diff_config['samBG_run'] = [matches[-1]] if matches else []
    else:
        diff_config['samBG_run'] = []

    diff_config['vBG_fn'] = diff_config['vBG_fn'] if diff_config['vanbkg_mode'] == 'nxs' else [diff_config[
        'vanbkg_text']]

    diff_config['vBG_run_mode'] = diff_config['vanbkg_mode']

    if diff_config['vbkg_check'] is True:
        if diff_config['vanbkg_mode'] == 'nxs':
            diff_config['vBG_run'] = [re.findall(r'RUN\d+', path)[-1] for path in diff_config['vBG_fn']]
        else:
            matches = re.findall(r'RUN\d+', diff_config['vanbkg_text'])
            diff_config['vBG_run'] = [matches[-1]] if matches else []
    else:
        diff_config['vBG_run'] = []

    diff_config['wave_min'] = float(diff_config['wave_start_text']) if diff_config['wave_start_text'].strip() else None
    diff_config['wave_max'] = float(diff_config['wave_end_text']) if diff_config['wave_end_text'].strip() else None
    diff_config['wavemin'] = float(diff_config['wave_start_text']) if diff_config['wave_start_text'].strip() else None
    diff_config['wavemax'] = float(diff_config['wave_end_text']) if diff_config['wave_end_text'].strip() else None
    diff_config['useSamBG'] = diff_config['sambkg_check']
    diff_config['useV'] = diff_config['v_check']
    diff_config['useVBG'] = diff_config['vbkg_check']
    # diff_config['normByPC'] = diff_config['norm_photon_charge_check']
    diff_config['scale_sam_bg'] = float(diff_config['sam_bkg_text']) if diff_config[
        'sam_bkg_text'].strip() else None
    diff_config['scale_v_bg'] = float(diff_config['van_bkg_text']) if diff_config['van_bkg_text'].strip() else None
    diff_config['T0_offset'] = 0.0
    
    base_config['d_rebin'] = {
        "group2": [float(diff_config['group2_start']) if diff_config['group2_start'].strip() else None,
                  float(diff_config['group2_end']) if diff_config['group2_end'].strip() else None,
                  int(diff_config['group2_number']) if diff_config['group2_number'].strip() else None],
        "group3": [float(diff_config['group3_start']) if diff_config['group3_start'].strip() else None,
                  float(diff_config['group3_end']) if diff_config['group3_end'].strip() else None,
                  int(diff_config['group3_number']) if diff_config['group3_number'].strip() else None],
        "group4": [float(diff_config['group4_start']) if diff_config['group4_start'].strip() else None,
                  float(diff_config['group4_end']) if diff_config['group4_end'].strip() else None,
                  int(diff_config['group4_number']) if diff_config['group4_number'].strip() else None],
        "group5": [float(diff_config['group5_start']) if diff_config['group5_start'].strip() else None,
                  float(diff_config['group5_end']) if diff_config['group5_end'].strip() else None,
                  int(diff_config['group5_number']) if diff_config['group5_number'].strip() else None],
        "group6": [float(diff_config['group6_start']) if diff_config['group6_start'].strip() else None,
                  float(diff_config['group6_end']) if diff_config['group6_end'].strip() else None,
                  int(diff_config['group6_number']) if diff_config['group6_number'].strip() else None],
        "group7": [float(diff_config['group7_start']) if diff_config['group7_start'].strip() else None,
                  float(diff_config['group7_end']) if diff_config['group7_end'].strip() else None,
                  int(diff_config['group7_number']) if diff_config['group7_number'].strip() else None]}

    diff_config['group_list'] = []
    for group in ['group2', 'group3', 'group4', 'group5', 'group6', 'group7']:
        if diff_config[group + '_check']:
            diff_config['group_list'].append(group)

    return diff_config, base_config

def pdf_mapping(window, pdf_config,base_config):
    pdf_config = mapping(window, pdf_config)

    # pdf_config['mode'] = mode.currentText()

    pdf_config['param_path'] = pdf_config['pdf_instrupath_text']
    # del pdf_config['pdf_instrupath_text']

    if getattr(sys, 'frozen', False):
        application_path = sys._MEIPASS
    else:
        application_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'utils')

    elementInfo_path = os.path.join(application_path, 'elementInfo.json')
    pdf_config['nist_fn'] = elementInfo_path

    if pdf_config['pdf_v'] is True:
        pdf_config["vanadium_name"] = 'V'
    elif pdf_config['pdf_vni'] is True:
        pdf_config["vanadium_name"] = 'VNi'

    base_config['vanadium_correction']['density_num'] = float(pdf_config['pdf_v_num_dens']) if pdf_config['pdf_v_num_dens'].strip() else base_config['vanadium_correction']['density_num']
    base_config['vanadium_correction']['radius'] = float(pdf_config['pdf_v_radius']) if pdf_config[
            'pdf_v_radius'].strip() else base_config['vanadium_correction']['radius']
    base_config['vanadium_correction']['beam_height'] = float(pdf_config['pdf_v_height']) if pdf_config[
            'pdf_v_height'].strip() else base_config['vanadium_correction']['beam_height']


    pdf_config['cal_path'] = pdf_config['pdf_offset_text']
    # del pdf_config['pdf_offset_text']

    pdf_config['has_cal'] = pdf_config['pdf_offset_check']
    # del pdf_config['pdf_offset_check']

    pdf_config.setdefault('sample_info', {})  # 如果 'sample_info' 不存在，则设置为一个空字典
    pdf_config['sample_info']['sample_name'] = pdf_config['pdf_chem_form']
    # del pdf_config['pdf_chem_form']

    pdf_config['sample_info']['mass'] = float(pdf_config['pdf_mass']) if pdf_config['pdf_mass'].strip() else None
    # del pdf_config['pdf_mass']

    pdf_config['sample_info']['shape'] = 'cylinder'

    pdf_config['sample_info']['height'] = float(pdf_config['pdf_height']) if pdf_config['pdf_height'].strip() else None
    # del pdf_config['pdf_height']

    pdf_config['sample_info']['radius'] = float(pdf_config['pdf_radius']) if pdf_config['pdf_radius'].strip() else None
    # del pdf_config['pdf_radius']

    pdf_config['sample_info']['beam_height'] = 3.0  # cm

    pdf_config['sam_run'] = [re.findall(r'RUN\d+', path)[-1] for path in pdf_config['sam_fn']]

    pdf_config['samBG_run_mode'] = pdf_config['sambkg_mode']
    pdf_config['samBG_fn'] = pdf_config['samBG_fn'] if pdf_config['sambkg_mode'] == 'nxs' else pdf_config[
        'sambkg_text']
    if pdf_config['samBG_run_mode'] == 'nxs':
        pdf_config['samBG_run'] = [re.findall(r'RUN\d+', path)[-1] for path in pdf_config['samBG_fn']]
    else:
        matches = re.findall(r'RUN\d+', pdf_config['sambkg_text'])
        pdf_config['samBG_run'] = [matches[-1] if matches else '']
    # del pdf_config['pdf_holdrun_text']

    pdf_config['scale_sam_bg'] = float(pdf_config['sam_bkg_text']) if pdf_config['sam_bkg_text'].strip() else None
    # del pdf_config['pdf_sam_hold']

    pdf_config['v_run_mode'] = pdf_config['van_run_mode']
    # del pdf_config['van_run_mode']
    pdf_config['v_fn'] = pdf_config['v_fn'] if pdf_config['v_run_mode'] == 'nxs' else pdf_config['pdf_vanrun_text']
    if pdf_config['v_run_mode'] == 'nxs':
        pdf_config['v_run'] = [re.findall(r'RUN\d+', path)[-1] for path in pdf_config['v_fn']]
    else:
        matches = re.findall(r'RUN\d+', pdf_config['pdf_vanrun_text'])
        pdf_config['v_run'] = [matches[-1] if matches else '']
    # del pdf_config['pdf_vanrun_text']

    pdf_config['vBG_run_mode'] = pdf_config['vanbkg_mode']
    pdf_config['vBG_fn'] = pdf_config['vBG_fn'] if pdf_config['vanbkg_mode'] == 'nxs' else pdf_config[
        'vanbkg_text']
    if pdf_config['vBG_run_mode'] == 'nxs':
        pdf_config['vBG_run'] = [re.findall(r'RUN\d+', path)[-1] for path in pdf_config['vBG_fn']]
    else:
        matches = re.findall(r'RUN\d+', pdf_config['vanbkg_text'])
        pdf_config['vBG_run'] = [matches[-1] if matches else '']

    pdf_config['scale_v_bg'] = float(pdf_config['van_bkg_text']) if pdf_config['van_bkg_text'].strip() else None
    # del pdf_config['pdf_sam_hold']

    pdf_config['wave_min'] = float(pdf_config['pdf_wavestart']) if pdf_config['pdf_wavestart'].strip() else None
    pdf_config['wavemin'] = pdf_config['wave_min']
    # del pdf_config['pdf_wavestart']

    pdf_config['wave_max'] = float(pdf_config['pdf_waveend']) if pdf_config['pdf_waveend'].strip() else None
    pdf_config['wavemax'] = pdf_config['wave_max']
    # del pdf_config['pdf_waveend']

    pdf_config['T0_offset'] = 0.0
    pdf_config['T0offset'] = 0.0
    # del pdf_config['pdf_T0_offset']

    pdf_config['q_rebin'] = [float(pdf_config['pdf_qrebin_start']) if pdf_config['pdf_qrebin_start'].strip() else None,
                             float(pdf_config['pdf_qrebin_end']) if pdf_config['pdf_qrebin_end'].strip() else None,
                             int(pdf_config['pdf_qrebin_number']) if pdf_config['pdf_qrebin_number'].strip() else None]
    # del pdf_config['pdf_qrebin_start'], pdf_config['pdf_qrebin_end'], pdf_config['pdf_qrebin_number']

    pdf_config['overlap'] = [tuple(map(float, pair.split('-'))) for pair in
                             re.split(r',\s*', pdf_config['pdf_stitch_overlaps']) if '-' in pair]

    pdf_config['r_rebin'] = [float(pdf_config['pdf_r_start']) if pdf_config['pdf_r_start'].strip() else None,
                             float(pdf_config['pdf_r_end']) if pdf_config['pdf_r_end'].strip() else None,
                             int(pdf_config['pdf_r_number']) if pdf_config['pdf_r_number'].strip() else None]

    return pdf_config, base_config


def offset_mapping(run_filePaths,offset_config,mode='cal',bank_group=None):
    offset_config['save_path'] = offset_config['select_path_text']
    offset_config['param_path'] = offset_config['select_pid_text']
    offset_config['data_path'] = os.path.dirname(os.path.dirname(run_filePaths[0]))
    offset_config['sam_fn'] = run_filePaths
    offset_config['sample_fns'] = run_filePaths #添加这行是为了适应rongzai-3.0版本，其中把sam_fn改为了sample_fns
    offset_config['sam_run'] = [os.path.basename(os.path.dirname(run_filePaths[0]))]
    selected_group = []
    if mode == 'check':
        selected_module = []
        module = f"1{offset_config['paracheck_module_num_1']}{offset_config['paracheck_module_num_2']}"
        for group_name, module_list in bank_group.items():
            if int(module) in module_list:
                selected_group.append(group_name)
                selected_module.append('module'+module)
        offset_config['selected_module'] = selected_module
    else:
        for i in range(2, 8):
            if offset_config[f'group{i}_check'] is True:
                selected_group.append(f'group{i}')
    offset_config['selected_group'] = selected_group
    offset_config['smooth_para'] = {}
    offset_config['d_std'] = {}
    offset_config['high_width_para'] = {}
    offset_config['fit_para'] = {}
    offset_config['group_para_tof'] = {}
    offset_config['group_para_d'] = {}
    for group in offset_config['selected_group']:
        offset_config['smooth_para'][group]={}
        offset_config['smooth_para'][group]['is_smooth'] = offset_config['smooth_check']
        offset_config['smooth_para'][group]['smooth_para'] = [int(offset_config[f'smooth_points_{group}']),int(offset_config[f'smooth_order_{group}'])]
        offset_config['d_std'][group] = [float(x) for x in offset_config['peaks_info_line'].split(',')]

        # 使用正则表达式匹配每个子列表
        pattern = re.compile(r'\[(.*?)\]')
        matches = pattern.findall(offset_config[f'peakfind_{group}'])
        # 将匹配结果转换为浮点数列表
        offset_config['high_width_para'][group] = []
        for match in matches:
            # 将每个子列表的字符串内容转换为浮点数
            sublist = [float(x) for x in match.split(',')]
            offset_config['high_width_para'][group].append(sublist)
        offset_config['high_width_para'][group] = offset_config['high_width_para'][group][:len(offset_config['d_std'][group])]

        offset_config['fit_para'][group] = {}
        offset_config['fit_para'][group]['least_peaks_num'] = float(offset_config[f'least_number_{group}'])
        if offset_config['asygaussian_check'] is True:
            offset_config['fit_para'][group]['fit_function'] = 'asymmetric_gaussian'
        else:
            offset_config['fit_para'][group]['fit_function'] = 'gaussian'
        offset_config['fit_para'][group]['order'] = offset_config[f'{group}_order']
        offset_config['fit_para'][group]['goodness_bottom'] = float(offset_config[f'goodness_{group}'])
        offset_config['fit_para'][group]['sub_background'] = True

        offset_config['group_para_tof'][group] = {}
        offset_config['group_para_tof'][group]['group_along_tube'] = float(offset_config['group_along_tof'])
        offset_config['group_para_tof'][group]['group_cross_tube'] = float(offset_config['group_cross_tof'])
        offset_config['group_para_tof'][group]['group_along_tube'] = int(offset_config['group_along_tof'])
        offset_config['group_para_tof'][group]['group_cross_tube'] = int(offset_config['group_cross_tof'])

        offset_config['group_para_d'][group] = {}
        offset_config['group_para_d'][group]['group_along_tube'] = float(offset_config['group_along_d'])
        offset_config['group_para_d'][group]['group_cross_tube'] = float(offset_config['group_cross_d'])
        offset_config['group_para_d'][group]['group_along_tube'] = int(offset_config['group_along_d'])
        offset_config['group_para_d'][group]['group_cross_tube'] = int(offset_config['group_cross_d'])
    if mode == 'check':
        offset_config['mode'] = 'check'
        pixel = f"{offset_config['paracheck_pixel_num_1']}{offset_config['paracheck_pixel_num_2']}{offset_config['paracheck_pixel_num_3']}"
        offset_config['check_point'] = int(pixel) - 1
    else:
        offset_config['mode'] = 'cal'
        offset_config['check_point'] = 1
    offset_config['anchor_point'] = None
    offset_config['group_list'] = ['group2','group3','group4','group5','group6','group7']
    offset_config['rebin_mode'] = 'uniform'
    return offset_config

def resultcheck_mapping(run_filePaths,offset_config):
    offset_config['save_path'] = offset_config['select_path_text']
    offset_config['param_path'] = offset_config['select_pid_text']
    offset_config['data_path'] = os.path.dirname(os.path.dirname(run_filePaths[0]))
    offset_config['sam_fn'] = run_filePaths
    offset_config['sample_fns'] = run_filePaths  # 添加这行是为了适应rongzai-3.0版本，其中把sam_fn改为了sample_fns
    offset_config['sam_run'] = [os.path.basename(os.path.dirname(run_filePaths[0]))]
    offset_config['d_std'] = [float(x) for x in offset_config['peaks_info_line'].split(',')]
    if offset_config['group_check'] is True:
        offset_config['selected_detector'] = offset_config['group_select']
    elif offset_config['bank_check'] is True:
        offset_config['selected_detector'] = offset_config['bank_select']
    elif offset_config['module_check'] is True:
        module = f"1{offset_config['resultcheck_module_num_1']}{offset_config['resultcheck_module_num_2']}"
        offset_config['selected_detector'] = 'module'+module
        start_pixel = f"{offset_config['resultcheck_pixel_num_1']}{offset_config['resultcheck_pixel_num_2']}{offset_config['resultcheck_pixel_num_3']}"
        end_pixel = f"{offset_config['resultcheck_pixel_num_4']}{offset_config['resultcheck_pixel_num_5']}{offset_config['resultcheck_pixel_num_6']}"
        offset_config['selected_pixels'] = [int(start_pixel)-1,int(end_pixel)]
    offset_config['group_list'] = ['group2','group3','group4','group5','group6','group7']
    offset_config['rebin_mode'] = 'uniform'
    return offset_config


def timeslice_mapping(window, diff_config, base_config):
    diff_config = mapping(window, diff_config)

    # 保存动态控件的信息
    if hasattr(window, 'operate_slicepara'):
        diff_config['dynamic_rows'] = []
        for row in window.operate_slicepara.rows:
            row_info = {
                'start_value': row['start_value'].text(),
                'end_value': row['end_value'].text(),
                'num_splits': row['num_splits'].text()
            }
            diff_config['dynamic_rows'].append(row_info)

    diff_config['sam_path'] = diff_config['sample_run_text']
    print(diff_config['sam_path'])
    diff_config['sam_run'] = [re.findall(r'RUN\d+', diff_config['sam_path'])[-1]]
    diff_config['samBG_run_mode'] = diff_config['sambkg_mode']
    diff_config['v_run_mode'] = diff_config['van_run_mode']
    diff_config['v_fn'] = diff_config['v_fn'] if diff_config['v_run_mode'] == 'nxs' else [diff_config['van_run_text']]

    if diff_config['v_check'] is True:
        if diff_config['v_run_mode'] == 'nxs':
            diff_config['v_run'] = [re.findall(r'RUN\d+', path)[-1] for path in diff_config['v_fn']]
        else:
            matches = re.findall(r'RUN\d+', diff_config['van_run_text'])
            diff_config['v_run'] = [matches[-1]] if matches else []
    else:
        diff_config['v_run'] = []

    if diff_config['v'] is True:
        diff_config["vanadium_name"] = 'V'
    elif diff_config['vni'] is True:
        diff_config["vanadium_name"] = 'VNi'

    if window.num_dens.isEnabled():
        base_config['vanadium_correction']['density_num'] = float(diff_config['num_dens']) if diff_config[
            'num_dens'].strip() else base_config['vanadium_correction']['density_num']
    if window.van_radius.isEnabled():
        base_config['vanadium_correction']['radius'] = float(diff_config['van_radius']) if diff_config[
            'van_radius'].strip() else base_config['vanadium_correction']['radius']
    if window.beam_height.isEnabled():
        base_config['vanadium_correction']['beam_height'] = float(diff_config['beam_height']) if diff_config[
            'beam_height'].strip() else base_config['vanadium_correction']['beam_height']

    diff_config['samBG_fn'] = diff_config['samBG_fn'] if diff_config['sambkg_mode'] == 'nxs' else [diff_config[
                                                                                                       'sambkg_text']]

    if diff_config['sambkg_check'] is True:
        if diff_config['sambkg_mode'] == 'nxs':
            diff_config['samBG_run'] = [re.findall(r'RUN\d+', path)[-1] for path in diff_config['samBG_fn']]
        else:
            matches = re.findall(r'RUN\d+', diff_config['sambkg_text'])
            diff_config['samBG_run'] = [matches[-1]] if matches else []
    else:
        diff_config['samBG_run'] = []

    diff_config['vBG_fn'] = diff_config['vBG_fn'] if diff_config['vanbkg_mode'] == 'nxs' else [diff_config[
                                                                                                   'vanbkg_text']]
    if diff_config['vbkg_check'] is True:
        diff_config['vBG_run_mode'] = diff_config['vanbkg_mode']
        if diff_config['vanbkg_mode'] == 'nxs':
            diff_config['vBG_run'] = [re.findall(r'RUN\d+', path)[-1] for path in diff_config['vBG_fn']]
        else:
            matches = re.findall(r'RUN\d+', diff_config['vanbkg_text'])
            diff_config['vBG_run'] = [matches[-1]] if matches else []
    else:
        diff_config['vBG_run'] = []

    diff_config['wave_min'] = float(diff_config['wave_start_text']) if diff_config['wave_start_text'].strip() else None
    diff_config['wave_max'] = float(diff_config['wave_end_text']) if diff_config['wave_end_text'].strip() else None
    diff_config['wavemin'] = float(diff_config['wave_start_text']) if diff_config['wave_start_text'].strip() else None
    diff_config['wavemax'] = float(diff_config['wave_end_text']) if diff_config['wave_end_text'].strip() else None
    diff_config['useSamBG'] = diff_config['sambkg_check']
    diff_config['useV'] = diff_config['v_check']
    diff_config['useVBG'] = diff_config['vbkg_check']
    # diff_config['normByPC'] = diff_config['norm_photon_charge_check']
    diff_config['scale_sam_bg'] = float(diff_config['sam_bkg_text']) if diff_config[
        'sam_bkg_text'].strip() else None
    diff_config['scale_v_bg'] = float(diff_config['van_bkg_text']) if diff_config['van_bkg_text'].strip() else None
    diff_config['T0_offset'] = 0.0

    base_config['d_rebin'] = {
        "group2": [float(diff_config['group2_start']) if diff_config['group2_start'].strip() else None,
                   float(diff_config['group2_end']) if diff_config['group2_end'].strip() else None,
                   int(diff_config['group2_number']) if diff_config['group2_number'].strip() else None],
        "group3": [float(diff_config['group3_start']) if diff_config['group3_start'].strip() else None,
                   float(diff_config['group3_end']) if diff_config['group3_end'].strip() else None,
                   int(diff_config['group3_number']) if diff_config['group3_number'].strip() else None],
        "group4": [float(diff_config['group4_start']) if diff_config['group4_start'].strip() else None,
                   float(diff_config['group4_end']) if diff_config['group4_end'].strip() else None,
                   int(diff_config['group4_number']) if diff_config['group4_number'].strip() else None],
        "group5": [float(diff_config['group5_start']) if diff_config['group5_start'].strip() else None,
                   float(diff_config['group5_end']) if diff_config['group5_end'].strip() else None,
                   int(diff_config['group5_number']) if diff_config['group5_number'].strip() else None],
        "group6": [float(diff_config['group6_start']) if diff_config['group6_start'].strip() else None,
                   float(diff_config['group6_end']) if diff_config['group6_end'].strip() else None,
                   int(diff_config['group6_number']) if diff_config['group6_number'].strip() else None],
        "group7": [float(diff_config['group7_start']) if diff_config['group7_start'].strip() else None,
                   float(diff_config['group7_end']) if diff_config['group7_end'].strip() else None,
                   int(diff_config['group7_number']) if diff_config['group7_number'].strip() else None]}

    diff_config['group_list'] = []
    for group in ['group2', 'group3', 'group4', 'group5', 'group6', 'group7']:
        if diff_config[group + '_check']:
            diff_config['group_list'].append(group)

    diff_config['slice_part'] = {}

    pattern = os.path.join(diff_config['sam_path'], "module*_evt_*.nxs")
    files = glob.glob(pattern) # 使用glob模块匹配符合条件的文件
    module_file_count = defaultdict(int) # 使用defaultdict来统计每个module名的文件数量
    for file in files:
        filename = os.path.basename(file) # 提取文件名
        module_name = filename.split('_evt_')[0] # 提取module名
        module_file_count[module_name] += 1 # 统计module名相同的文件数量
    # 检查所有module名的文件数量是否一致
    file_counts = list(module_file_count.values())
    if all(count == file_counts[0] for count in file_counts):
        diff_config['slice_part']["evt_file_num"] = file_counts[0]  # 返回文件数量
    else:
        diff_config['slice_part']["evt_file_num"] = 0  # 返回0表示数量不一致

    diff_config['slice_part']['slice_info'] = []
    for i, row in enumerate(window.operate_slicepara.rows):
        start_value = row['start_value'].text().strip()
        end_value = row['end_value'].text().strip()
        num_splits = row['num_splits'].text().strip()

        # 只有在字符串不为空时才进行转换
        start_value = float(start_value) if start_value else None
        end_value = float(end_value) if end_value else None
        num_splits = int(num_splits) if num_splits else None

        diff_config['slice_part']['slice_info'].append([start_value, end_value, num_splits])
        diff_config['slice_part']['start_pulseID'] = read_start_pulseID(window)
        diff_config['slice_part']['tof_step'] = float(diff_config['tof_step']) if diff_config['tof_step'].strip() else None


    # diff_config['rows'] = window.operate_slicepara.rows #将window.operate_slicepara.rows的信息存储下来，目的是下次加载的时候复原它
    return diff_config, base_config



def save_diff_config(window, diff_config, bl16_config):
    try:
        diff_config, _ = diff_mapping(window, diff_config, bl16_config)

        # if diff_config['mode'] == 'offline':
            # 弹出保存文件对话框
        options = QFileDialog.Options()
        filename, _ = QFileDialog.getSaveFileName(window, "Save Config", "", "JSON Files (*.json);;All Files (*)",
                                                  options=options)

        if filename:
            # 确保文件名以 .json 结尾
            if not filename.lower().endswith('.json'):
                filename += '.json'

            # 将配置保存到选择的文件中
            with open(filename, 'w') as config_file:
                json.dump(diff_config, config_file, indent=4)  # 使用 indent 参数格式化 JSON 输出

                # 可选：弹出消息框通知用户配置已保存
                # QMessageBox.information(window, "Config Saved", f"Configuration saved successfully to: {filename}")
        # else:
        #     # 将字典序列化为 JSON 字符串
        #     config_json_str = json.dumps(diff_config)
        #
        #     # 存储 JSON 字符串到 Redis
        #     Path = '/mpi/rzera/diff_reduction'
        #     try:
        #         rds.write(Path, config_json_str)  # 使用已经创建的 Redis 客户端实例 self.rds
        #         # 可选：给用户一个反馈，告知他们文件已保存
        #         QtWidgets.QMessageBox.information(window, 'Success',
        #                                           'The config file has been saved to redis of ' + Path)
        #     except:
        #         QtWidgets.QMessageBox.information(window, 'Failure',
        #                                           'Redis connection failure')
    except Exception as e:
        print(f"An error occurred: {e}")
        traceback.print_exc()  # 打印异常的堆栈跟踪


def save_pdf_config(window, pdf_config, base_config):
    pdf_config,_ = pdf_mapping(window, pdf_config, base_config)

    # if pdf_config['mode'] == 'offline':
        # 弹出保存文件对话框
    options = QFileDialog.Options()
    filename, _ = QFileDialog.getSaveFileName(window, "Save Config", "", "JSON Files (*.json);;All Files (*)",
                                              options=options)

    if filename:
        # 确保文件名以 .json 结尾
        if not filename.lower().endswith('.json'):
            filename += '.json'

        # 将配置保存到选择的文件中
        with open(filename, 'w') as config_file:
            json.dump(pdf_config, config_file, indent=4)  # 使用 indent 参数格式化 JSON 输出

            # 可选：弹出消息框通知用户配置已保存
            # QMessageBox.information(window, "Config Saved", f"Configuration saved successfully to: {filename}")

    # else:
    #     # 将字典序列化为 JSON 字符串
    #     config_json_str = json.dumps(pdf_config)
    #
    #     # 存储 JSON 字符串到 Redis
    #     Path = '/mpi/rzera/sqcal'
    #     try:
    #         rds.write(Path, config_json_str)  # 使用已经创建的 Redis 客户端实例 self.rds
    #         # 可选：给用户一个反馈，告知他们文件已保存
    #         QtWidgets.QMessageBox.information(window, 'Success',
    #                                           'The config file has been saved to redis of ' + Path)
    #     except:
    #         QtWidgets.QMessageBox.information(window, 'Failure',
    #                                           'Redis connection failure')

    # print(pdf_config)

def save_offset_config(window, run_filePaths):
    try:
        offset_config = {}
        offset_config = mapping(window, offset_config)
        offset_config['sam_fn'] = run_filePaths
        options = QFileDialog.Options()
        filename, _ = QFileDialog.getSaveFileName(window, "Save Config", "", "JSON Files (*.json);;All Files (*)",
                                                  options=options)

        if filename:
            # 确保文件名以 .json 结尾
            if not filename.lower().endswith('.json'):
                filename += '.json'

            # 将配置保存到选择的文件中
            with open(filename, 'w') as config_file:
                json.dump(offset_config, config_file, indent=4)  # 使用 indent 参数格式化 JSON 输出
    except Exception as e:
        print(f"An error occurred: {e}")
        traceback.print_exc()  # 打印异常的堆栈跟踪

def save_timeslice_config(window, diff_config, bl16_config):
    try:
        diff_config, _ = timeslice_mapping(window, diff_config, bl16_config)

        options = QFileDialog.Options()
        filename, _ = QFileDialog.getSaveFileName(window, "Save Config", "", "JSON Files (*.json);;All Files (*)",
                                                  options=options)

        if filename:
            # 确保文件名以 .json 结尾
            if not filename.lower().endswith('.json'):
                filename += '.json'

            # 将配置保存到选择的文件中
            with open(filename, 'w') as config_file:
                json.dump(diff_config, config_file, indent=4)  # 使用 indent 参数格式化 JSON 输出

    except Exception as e:
        print(f"An error occurred: {e}")
        traceback.print_exc()  # 打印异常的堆栈跟踪


def load_diff_config(window):
    # 打开文件选择对话框
    options = QtWidgets.QFileDialog.Options()
    config_file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
        window, "Select Config File", "", "JSON Files (*.json)", options=options)

    try:
        if config_file_path:
            # 读取并加载配置文件
            with open(config_file_path, 'r', encoding='utf-8') as json_file:
                diff_configure = json.load(json_file)

            load_mapping(window, diff_configure)
            # index = mode.findText(diff_configure['mode'])
            # mode.setCurrentIndex(index)
            window.diff_config['sam_fn'] = diff_configure['sam_fn']
            window.diff_config['v_fn'] = diff_configure['v_fn'] if diff_configure['v_run_mode'] == 'nxs' else []
            window.diff_config['samBG_fn'] = diff_configure['samBG_fn'] if diff_configure['sambkg_mode'] == 'nxs' else []
            window.diff_config['vBG_fn'] = diff_configure['vBG_fn'] if diff_configure[
                                                                               'vBG_run_mode'] == 'nxs' else []

    except Exception as e:
        QtWidgets.QMessageBox.information(window, 'Error',
                                          'uncorrected json file')
        print(f'Failed to plot. Reason: {e}')
        traceback.print_exc()  # 打印异常的堆栈跟踪


def load_pdf_config(window):
    # 打开文件选择对话框
    options = QtWidgets.QFileDialog.Options()
    config_file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
        window, "Select Config File", "", "JSON Files (*.json)", options=options)

    if config_file_path:
        # 读取并加载配置文件
        with open(config_file_path, 'r', encoding='utf-8') as json_file:
            pdf_config = json.load(json_file)

        try:
            load_mapping(window, pdf_config)

            # index = mode.findText(pdf_config['mode'])
            # mode.setCurrentIndex(index)

            window.pdf_config['sam_fn'] = pdf_config['sam_fn']
            window.pdf_config['v_fn'] = pdf_config['v_fn'] if pdf_config['v_run_mode'] == 'nxs' else []
            window.pdf_config['samBG_fn'] = pdf_config['samBG_fn'] if pdf_config[
                                                                               'sambkg_mode'] == 'nxs' else []
            window.pdf_config['vBG_fn'] = pdf_config['vBG_fn'] if pdf_config[
                                                                           'vBG_run_mode'] == 'nxs' else []

        except Exception as e:
            QtWidgets.QMessageBox.information(window, 'Error',
                                              'uncorrected json file')
            print(f'Failed to plot. Reason: {e}')
            traceback.print_exc()  # 打印异常的堆栈跟踪

def load_offset_config(window):
    # 打开文件选择对话框
    options = QtWidgets.QFileDialog.Options()
    config_file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
        window, "Select Config File", "", "JSON Files (*.json)", options=options)

    try:
        if config_file_path:
            # 读取并加载配置文件
            with open(config_file_path, 'r', encoding='utf-8') as json_file:
                offset_configure = json.load(json_file)

            load_mapping(window, offset_configure)
            # index = mode.findText(diff_configure['mode'])
            # mode.setCurrentIndex(index)
            window.run_filePaths = offset_configure['sam_fn']

    except Exception as e:
        QtWidgets.QMessageBox.information(window, 'Error',
                                          'uncorrected json file')
        print(f'Failed to plot. Reason: {e}')
        traceback.print_exc()  # 打印异常的堆栈跟踪

def load_timeslice_config(window):
    # 打开文件选择对话框
    options = QtWidgets.QFileDialog.Options()
    config_file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
        window, "Select Config File", "", "JSON Files (*.json)", options=options)

    try:
        if config_file_path:
            # 读取并加载配置文件
            with open(config_file_path, 'r', encoding='utf-8') as json_file:
                diff_configure = json.load(json_file)

            while len(window.operate_slicepara.rows) > 0:
                window.operate_slicepara.remove_row()

            # 加载动态控件的信息
            if 'dynamic_rows' in diff_configure:
                for row_info in diff_configure['dynamic_rows']:
                    window.operate_slicepara.add_row()
                    last_row = window.operate_slicepara.rows[-1]
                    last_row['start_value'].setText(row_info['start_value'])
                    last_row['end_value'].setText(row_info['end_value'])
                    last_row['num_splits'].setText(row_info['num_splits'])


            load_mapping(window, diff_configure)



            window.diff_config['sam_path'] = diff_configure['sam_path']
            window.diff_config['v_fn'] = diff_configure['v_fn'] if diff_configure['v_run_mode'] == 'nxs' else []
            window.diff_config['samBG_fn'] = diff_configure['samBG_fn'] if diff_configure['sambkg_mode'] == 'nxs' else []
            window.diff_config['vBG_fn'] = diff_configure['vBG_fn'] if diff_configure[
                                                                               'vBG_run_mode'] == 'nxs' else []

    except Exception as e:
        QtWidgets.QMessageBox.information(window, 'Error',
                                          'uncorrected json file')
        print(f'Failed to plot. Reason: {e}')
        traceback.print_exc()  # 打印异常的堆栈跟踪