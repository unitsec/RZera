from PyQt5.QtWidgets import QMessageBox
from rongzai.dataSvc.read_format import read_cal
import pathlib
import re

def offset_run_check(window, offset_config):
    condition_met = True
    if offset_config['select_run_text'] == '':
        QMessageBox.warning(window, "Input Check", "Please provide sample run file.")
        condition_met = False
        return condition_met
    if offset_config['select_pid_text'] == '':
        QMessageBox.warning(window, "Input Check", "Please provide the instrument file path.")
        condition_met = False
        return condition_met
    if offset_config['select_path_text'] == '':
        QMessageBox.warning(window, "Input Check", "Please provide the save path.")
        condition_met = False
        return condition_met
    if offset_config['select_path_text'] == '':
        QMessageBox.warning(window, "Input Check", "Please provide the save path.")
        condition_met = False
        return condition_met

    if offset_config['group_along_tof'] == '' or offset_config[('group_cross_tof')] == '' or offset_config['group_along_d'] == '' or offset_config['group_cross_d'] == '':
        QMessageBox.warning(window, "Input Check", "Please provide complete the group information.")
        condition_met = False
        return condition_met

    if offset_config['peaks_info_line'] == '':
        QMessageBox.warning(window, "Input Check", "Please provide the d peaks' positions.")
        condition_met = False
        return condition_met
    try:
        d_std_list = [float(x) for x in offset_config['peaks_info_line'].split(',')]
    except:
        QMessageBox.warning(window, "Input Check", "The information of d peaks' position is incorrect.")
        condition_met = False
        return condition_met
    if len(d_std_list) == 1:
        QMessageBox.warning(window, "Input Check", "The number of d peaks' position must be more than 1.")
        condition_met = False
        return condition_met

    selected_group = []
    if offset_config[f'groupBS_check'] is True:
        selected_group.append(f'groupBS')
    if offset_config[f'groupHA_check'] is True:
        selected_group.append(f'groupHA')
    if offset_config[f'groupSE_check'] is True:
        selected_group.append(f'groupSE')
    if offset_config[f'groupMA_check'] is True:
        selected_group.append(f'groupMA')
    if offset_config[f'groupLA_check'] is True:
        selected_group.append(f'groupLA')
    if len(selected_group) == 0:
        QMessageBox.warning(window, "Input Check", "Please select one group at least.")
        condition_met = False
        return condition_met

    for group in selected_group:
        if  offset_config['smooth_check'] is True:
            if offset_config[f'smooth_points_{group}'] == '' or offset_config[f'smooth_order_{group}'] == '':
                QMessageBox.warning(window, "Input Check", f"please give the full smooth parameter of {group}.")
                condition_met = False
                return condition_met

        if offset_config[f'peakfind_{group}'] == '':
            QMessageBox.warning(window, "Input Check", f"please give the peak find parameter of {group}.")
            condition_met = False
            return condition_met

        try:
            pattern = re.compile(r'\[(.*?)\]')  # 使用正则表达式匹配每个子列表
            print(offset_config[f'peakfind_{group}'])
            matches = pattern.findall(offset_config[f'peakfind_{group}'])
            print(matches)
            high_width_para = []
            for match in matches:
                # 将每个子列表的字符串内容转换为浮点数
                sublist = [float(x) for x in match.split(',')]
                high_width_para.append(sublist)
        except:
            QMessageBox.warning(window, "Input Check", "The form of peak find parameter is incorrect.")
            condition_met = False
            return condition_met

        if len(high_width_para) < len(d_std_list):
            QMessageBox.warning(window, "Input Check", f"The number of peak find parameter in {group} shouldn't less than the number of d peaks' positions.")
            condition_met = False
            return condition_met
    return condition_met


def offset_check_check(window, offset_config, bank_group):
    condition_met = True
    if offset_config['select_run_text'] == '':
        QMessageBox.warning(window, "Input Check", "Please provide sample run file.")
        condition_met = False
        return condition_met
    if offset_config['select_pid_text'] == '':
        QMessageBox.warning(window, "Input Check", "Please provide the instrument file path.")
        condition_met = False
        return condition_met
    if offset_config['select_path_text'] == '':
        QMessageBox.warning(window, "Input Check", "Please provide the save path.")
        condition_met = False
        return condition_met

    if offset_config['group_along_tof'] == '' or offset_config['group_cross_tof'] == '' or offset_config[
        'group_along_d'] == '' or offset_config['group_cross_d'] == '':
        QMessageBox.warning(window, "Input Check", "Please provide complete the group information.")
        condition_met = False
        return condition_met

    if offset_config['peaks_info_line'] == '':
        QMessageBox.warning(window, "Input Check", "Please provide the d peaks' positions.")
        condition_met = False
        return condition_met
    try:
        d_std_list = [float(x) for x in offset_config['peaks_info_line'].split(',')]
    except:
        QMessageBox.warning(window, "Input Check", "The information of d peaks' position is incorrect.")
        condition_met = False
        return condition_met
    if len(d_std_list) == 1:
        QMessageBox.warning(window, "Input Check", "The number of d peaks' position must be more than 1.")
        condition_met = False
        return condition_met

    module = f"1{offset_config['paracheck_module_num_1']}{offset_config['paracheck_module_num_2']}"
    group = ''
    for group_name, module_list in bank_group.items():
        if int(module) in module_list:
            group = group_name
    if group == '':
        QMessageBox.warning(window, "Input Check", f"The module{module} doesn't exist.")
        condition_met = False
        return condition_met

    if group == 'groupBS':
        max_pixel = 800 / (int(offset_config['group_along_tof']) * int(offset_config['group_cross_tof'])) / (
                    int(offset_config['group_along_d']) * int(offset_config['group_cross_d']))
    else:
        max_pixel = 2400 / (int(offset_config['group_along_tof']) * int(offset_config['group_cross_tof'])) / (
                int(offset_config['group_along_d']) * int(offset_config['group_cross_d']))
    if max_pixel - int(max_pixel) != 0:
        QMessageBox.warning(window, "Input Check", f"The group method can't separate the pixels correctly.")
        condition_met = False
        return condition_met

    pixel = f"{offset_config['paracheck_pixel_num_1']}{offset_config['paracheck_pixel_num_2']}{offset_config['paracheck_pixel_num_3']}"

    if int(pixel) not in range(1, int(max_pixel +1)):
        QMessageBox.warning(window, "Input Check", f"The pixel 0{pixel} doesn't exist in module{module}.")
        condition_met = False
        return condition_met

    if offset_config['smooth_check'] is True:
        if offset_config[f'smooth_points_{group}'] == '' or offset_config[f'smooth_order_{group}'] == '':
            QMessageBox.warning(window, "Input Check", f"please give the full smooth parameter of {group}.")
            condition_met = False
            return condition_met

    if offset_config[f'peakfind_{group}'] == '':
        QMessageBox.warning(window, "Input Check", f"please give the peak find parameter of {group}.")
        condition_met = False
        return condition_met

    if offset_config["LA_offset"] and offset_config['select_run_text_2'] == '':
        QMessageBox.warning(window, "Input Check", f"please give another run file.")
        condition_met = False
        return condition_met

    if offset_config["LA_offset"] and offset_config['peaks_info_line_LA'] == '':
        QMessageBox.warning(window, "Input Check", f"please give another d peaks' positions.")
        condition_met = False
        return condition_met

    if offset_config["LA_offset"] and offset_config['peaks_info_line_LA'] == '':
        QMessageBox.warning(window, "Input Check", f"please give another d peaks' positions.")
        condition_met = False
        return condition_met

    if offset_config["LA_offset"]:
        try:
            d_std_list_LA = [float(x) for x in offset_config['peaks_info_line_LA'].split(',')]
        except:
            QMessageBox.warning(window, "Input Check", "The information of d peaks' position is incorrect.")
            condition_met = False
            return condition_met
        try:
            pattern = re.compile(r'\[(.*?)\]')  # 使用正则表达式匹配每个子列表
            matches = pattern.findall(offset_config[f'peakfind_{group}_LA'])
            high_width_para_LA = []
            for match in matches:
                # 将每个子列表的字符串内容转换为浮点数
                sublist = [float(x) for x in match.split(',')]
                high_width_para_LA.append(sublist)
        except:
            QMessageBox.warning(window, "Input Check", "The form of peak find parameter is incorrect.")
            condition_met = False
            return condition_met

        if len(high_width_para_LA) != len(d_std_list_LA):
            QMessageBox.warning(window, "Input Check",
                                f"The number of peak find parameter groups in {group} didn't match the number of d peaks' positions.")
            condition_met = False
            return condition_met
        return condition_met

    try:
        pattern = re.compile(r'\[(.*?)\]')  # 使用正则表达式匹配每个子列表
        matches = pattern.findall(offset_config[f'peakfind_{group}'])
        high_width_para = []
        for match in matches:
            # 将每个子列表的字符串内容转换为浮点数
            sublist = [float(x) for x in match.split(',')]
            high_width_para.append(sublist)
    except:
        QMessageBox.warning(window, "Input Check", "The form of peak find parameter is incorrect.")
        condition_met = False
        return condition_met

    if len(high_width_para) != len(d_std_list):
        QMessageBox.warning(window, "Input Check",
                            f"The number of peak find parameter groups in {group} didn't match the number of d peaks' positions.")
        condition_met = False
        return condition_met
    return condition_met

def offset_result_check(window, offset_config):
    condition_met = True
    if offset_config['select_run_text'] == '':
        QMessageBox.warning(window, "Input Check", "Please provide sample run file.")
        condition_met = False
        return condition_met
    if offset_config['select_pid_text'] == '':
        QMessageBox.warning(window, "Input Check", "Please provide the instrument file path.")
        condition_met = False
        return condition_met
    if offset_config['select_path_text'] == '':
        QMessageBox.warning(window, "Input Check", "Please provide the save path.")
        condition_met = False
        return condition_met
    if offset_config['group_check'] is False and offset_config['bank_check'] is False and offset_config['module_check'] is False:
        QMessageBox.warning(window, "Input Check", "Please select a result check strategy.")
        condition_met = False
        return condition_met
    return condition_met