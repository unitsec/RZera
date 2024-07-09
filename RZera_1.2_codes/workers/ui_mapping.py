from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QLineEdit, QComboBox, QCheckBox
import traceback
import json
from PyQt5.QtWidgets import QFileDialog
import re
from utils_ui.helper import extract_number
from pathlib import Path
import sys
import os


def mapping(window,config):
    for name, obj in vars(window).items():
        if isinstance(obj, QLineEdit):
            config[name] = obj.text()
        elif isinstance(obj, QComboBox):
            config[name] = obj.currentText()
        elif isinstance(obj, QCheckBox):
            config[name] = obj.isChecked()
    print(config)
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

    # 为QlineEdit单独开一个循环，确保后加载QLineEdit。
    # 因为，"nxs"和“dat"切换时，会清空对应的QLineEdit中的文本；如果加载配置时先加载了QLineEdit，会有被再次清空的危险。所以必须保证后加载QLineEdit。
    for name, value in config.items():
        if hasattr(window, name):
            obj = getattr(window, name)
            if isinstance(obj, QLineEdit):
                obj.setText(value)




def diff_mapping(window, diff_config, bl16_config):
    diff_config = mapping(window,diff_config)

    # diff_config['mode'] = mode.currentText()
    diff_config['param_path'] = diff_config['instru_path_text']
    diff_config['cal_path'] = diff_config['offset_file_text']
    diff_config['has_cal'] = diff_config['offset_correction_check']
    diff_config['is_batch'] = diff_config['batch_reduction_check']

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
    diff_config['v_run_mode'] = diff_config['van_run_mode']
    diff_config['v_fn'] = diff_config['v_fn'] if diff_config['v_run_mode'] == 'nxs' else diff_config['van_run_text']

    if diff_config['v_run_mode'] == 'nxs':
        diff_config['v_run'] = [re.findall(r'RUN\d+', path)[-1] for path in diff_config['v_fn']]
    else:
        matches = re.findall(r'RUN\d+', diff_config['van_run_text'])
        diff_config['v_run'] = matches[-1] if matches else ''

    diff_config['hold_fn'] = diff_config['hold_fn'] if diff_config['hold_run_mode'] == 'nxs' else diff_config[
        'hold_run_text']

    if diff_config['hold_run_mode'] == 'nxs':
        diff_config['hold_run'] = [re.findall(r'RUN\d+', path)[-1] for path in diff_config['hold_fn']]
    else:
        matches = re.findall(r'RUN\d+', diff_config['hold_run_text'])
        diff_config['hold_run'] = matches[-1] if matches else ''

    diff_config['wavemin'] = float(diff_config['wave_start_text']) if diff_config['wave_start_text'].strip() else None
    diff_config['wavemax'] = float(diff_config['wave_end_text']) if diff_config['wave_end_text'].strip() else None
    diff_config['useV'] = diff_config['v_check']
    diff_config['useHold'] = diff_config['hold_check']
    diff_config['normByPC'] = diff_config['norm_photon_charge_check']
    diff_config['scale_sam_hold'] = float(diff_config['sample_hold_text']) if diff_config[
        'sample_hold_text'].strip() else None
    diff_config['scale_v_hold'] = float(diff_config['v_hold_text']) if diff_config['v_hold_text'].strip() else None
    diff_config['T0offset'] = float(diff_config['T0_offset_text']) if diff_config['T0_offset_text'].strip() else None

    diff_config['diff_d_rebin'] = {"bank2": [], "bank3": [], "bank4": [], "bank5": [], "bank6": [], "bank7": []}
    if diff_config['diff_bankname'] != 'ALL':
        diff_config['diff_d_rebin'][diff_config['diff_bankname']] = \
            [float(diff_config['d_rebin_start']) if diff_config['d_rebin_start'].strip() else None,
             float(diff_config['d_rebin_end']) if diff_config['d_rebin_end'].strip() else None,
             int(diff_config['d_rebin_number']) if diff_config['d_rebin_number'].strip() else None]
    else:
        diff_config['diff_d_rebin'] = bl16_config['d_rebin']

    diff_config['bank_name'] = ["bank2", "bank3", "bank4", "bank5", "bank6", "bank7"] if diff_config['diff_bankname'] == 'ALL' else [diff_config['diff_bankname']]

    return diff_config

def pdf_mapping(window, pdf_config):
    pdf_config = mapping(window, pdf_config)

    # pdf_config['mode'] = mode.currentText()

    pdf_config['param_path'] = pdf_config['pdf_instrupath_text']
    # del pdf_config['pdf_instrupath_text']

    if getattr(sys, 'frozen', False):
        application_path = sys._MEIPASS
    else:
        application_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'utils_ui')

    elementInfo_path = os.path.join(application_path, 'elementInfo.json')
    pdf_config['nist_fn'] = elementInfo_path

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

    pdf_config['v_run_mode'] = pdf_config['van_run_mode']
    # del pdf_config['van_run_mode']

    pdf_config['v_fn'] = pdf_config['v_fn'] if pdf_config['v_run_mode'] == 'nxs' else pdf_config['pdf_vanrun_text']

    if pdf_config['v_run_mode'] == 'nxs':
        pdf_config['v_run'] = [re.findall(r'RUN\d+', path)[-1] for path in pdf_config['v_fn']]
    else:
        matches = re.findall(r'RUN\d+', pdf_config['pdf_vanrun_text'])
        pdf_config['v_run'] = matches[-1] if matches else ''
    # del pdf_config['pdf_vanrun_text']

    pdf_config['hold_fn'] = pdf_config['hold_fn'] if pdf_config['hold_run_mode'] == 'nxs' else pdf_config[
        'pdf_holdrun_text']

    if pdf_config['hold_run_mode'] == 'nxs':
        pdf_config['hold_run'] = [re.findall(r'RUN\d+', path)[-1] for path in pdf_config['hold_fn']]
    else:
        matches = re.findall(r'RUN\d+', pdf_config['pdf_holdrun_text'])
        pdf_config['hold_run'] = matches[-1] if matches else ''
    # del pdf_config['pdf_holdrun_text']

    pdf_config['wavemin'] = float(pdf_config['pdf_wavestart']) if pdf_config['pdf_wavestart'].strip() else None
    # del pdf_config['pdf_wavestart']

    pdf_config['wavemax'] = float(pdf_config['pdf_waveend']) if pdf_config['pdf_waveend'].strip() else None
    # del pdf_config['pdf_waveend']

    pdf_config['scale_sam_hold'] = float(pdf_config['pdf_sam_hold']) if pdf_config['pdf_sam_hold'].strip() else None
    # del pdf_config['pdf_sam_hold']

    pdf_config['scale_v_hold'] = float(pdf_config['pdf_van_hold']) if pdf_config['pdf_van_hold'].strip() else None
    # del pdf_config['pdf_van_hold']

    pdf_config['scale_sam_bg'] = float(pdf_config['pdf_sam_bkg']) if pdf_config['pdf_sam_bkg'].strip() else None
    # del pdf_config['pdf_sam_bkg']

    pdf_config['scale_v_bg'] = float(pdf_config['pdf_van_bkg']) if pdf_config['pdf_van_bkg'].strip() else None
    # del pdf_config['pdf_van_bkg']

    pdf_config['T0offset'] = float(pdf_config['pdf_T0_offset']) if pdf_config['pdf_T0_offset'].strip() else None
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

    return pdf_config


def save_diff_config(window, diff_config, bl16_config):
    try:
        diff_config = diff_mapping(window, diff_config, bl16_config)

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


def save_pdf_config(window, pdf_config):
    pdf_config = pdf_mapping(window, pdf_config)

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
            window.diff_config['hold_fn'] = diff_configure['hold_fn'] if diff_configure['hold_run_mode'] == 'nxs' else []

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
            window.pdf_config['hold_fn'] = pdf_config['hold_fn'] if pdf_config['hold_run_mode'] == 'nxs' else []

        except Exception as e:
            QtWidgets.QMessageBox.information(window, 'Error',
                                              'uncorrected json file')
            print(f'Failed to plot. Reason: {e}')
            traceback.print_exc()  # 打印异常的堆栈跟踪