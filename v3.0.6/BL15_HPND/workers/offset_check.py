from PyQt5.QtWidgets import QMessageBox
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
    if offset_config['save_path_text'] == '':
        QMessageBox.warning(window, "Input Check", "Please provide the save path.")
        condition_met = False
        return condition_met
    if offset_config['select_Si'] is False and offset_config['select_other'] is False:
        QMessageBox.warning(window, "Input Check", "Please select or provide the d peaks' positions.")
        condition_met = False
        return condition_met
    if offset_config['select_other'] is True and offset_config['peaks_info_line'] == '':
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

    selected_bank = []
    for i in range(2,8):
        if offset_config[f'bank{i}_check'] is True:
            selected_bank.append(f'bank{i}')
    if len(selected_bank) == 0:
        QMessageBox.warning(window, "Input Check", "Please select one bank at least.")
        condition_met = False
        return condition_met
    for bank in selected_bank:
        if offset_config[f'smooth_points_{bank}'] == '' or offset_config[f'smooth_order_{bank}'] == '':
            QMessageBox.warning(window, "Input Check", f"please give the full smooth parameter of {bank}.")
            condition_met = False
            return condition_met

        if offset_config[f'peakfind_{bank}'] == '':
            QMessageBox.warning(window, "Input Check", f"please give the peak find parameter of {bank}.")
            condition_met = False
            return condition_met

        try:
            pattern = re.compile(r'\[(.*?)\]')  # 使用正则表达式匹配每个子列表
            matches = pattern.findall(offset_config[f'peakfind_{bank}'])
            high_width_para = []
            for match in matches:
                # 将每个子列表的字符串内容转换为浮点数
                sublist = [float(x) for x in match.split(',')]
                high_width_para.append(sublist)
        except:
            QMessageBox.warning(window, "Input Check", "The form of peak find parameter is incorrect.")
            condition_met = False
            return condition_met

        if len(high_width_para) > len(d_std_list):
            QMessageBox.warning(window, "Input Check", f"The number of peak find parameter groups in {bank} shouldn't more than the number of d peaks' positions.")
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
    if offset_config['save_path_text'] == '':
        QMessageBox.warning(window, "Input Check", "Please provide the save path.")
        condition_met = False
        return condition_met
    if offset_config['select_Si'] is False and offset_config['select_other'] is False:
        QMessageBox.warning(window, "Input Check", "Please select or provide the d peaks' positions.")
        condition_met = False
        return condition_met
    if offset_config['select_other'] is True and offset_config['peaks_info_line'] == '':
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

    module = f"1{offset_config['module_num_1']}{offset_config['module_num_2']}"
    bank = ''
    for bank_name, module_list in bank_group.items():
        if int(module) in module_list:
            bank = bank_name
    if bank == '':
        QMessageBox.warning(window, "Input Check", f"The module{module} doesn't exist.")
        condition_met = False
        return condition_met

    pixel = f"{offset_config['pixel_num_1']}{offset_config['pixel_num_2']}{offset_config['pixel_num_3']}"
    if int(pixel) not in range(1,801):
        QMessageBox.warning(window, "Input Check", f"The pixel 0{pixel} doesn't exist in module{module}.")
        condition_met = False
        return condition_met

    if offset_config[f'smooth_points_{bank}'] == '' or offset_config[f'smooth_order_{bank}'] == '':
        QMessageBox.warning(window, "Input Check", f"please give the full smooth parameter of {bank}.")
        condition_met = False
        return condition_met

    if offset_config[f'peakfind_{bank}'] == '':
        QMessageBox.warning(window, "Input Check", f"please give the peak find parameter of {bank}.")
        condition_met = False
        return condition_met

    try:
        pattern = re.compile(r'\[(.*?)\]')  # 使用正则表达式匹配每个子列表
        matches = pattern.findall(offset_config[f'peakfind_{bank}'])
        high_width_para = []
        for match in matches:
            # 将每个子列表的字符串内容转换为浮点数
            sublist = [float(x) for x in match.split(',')]
            high_width_para.append(sublist)
    except:
        QMessageBox.warning(window, "Input Check", "The form of peak find parameter is incorrect.")
        condition_met = False
        return condition_met

    if len(high_width_para) > len(d_std_list):
        QMessageBox.warning(window, "Input Check",
                            f"The number of peak find parameter groups in {bank} shouldn't more than the number of d peaks' positions.")
        condition_met = False
        return condition_met
    return condition_met