from PyQt5.QtWidgets import QMessageBox
from rongzai.dataSvc.read_format import read_cal
import pathlib

def diff_reduction_check(window, diff_config, base_config):
    condition_met = True
    if diff_config['sample_run_text'] == '':
        QMessageBox.warning(window, "Input Check", "Please provide sample run file.")
        condition_met = False
        return condition_met
    if diff_config['param_path'] == '':
        QMessageBox.warning(window, "Input Check", "Please provide instrument file path.")
        condition_met = False
        return condition_met
    if diff_config['cal_path'] == '' and diff_config['has_cal'] is True:
        QMessageBox.warning(window, "Input Check", "Please provide offset file directory.")
        condition_met = False
        return condition_met
    if diff_config['wave_start_text'] == '':
        QMessageBox.warning(window, "Input Check", "Please provide wave start value.")
        condition_met = False
        return condition_met
    if diff_config['wave_end_text'] == '':
        QMessageBox.warning(window, "Input Check", "Please provide wave end value.")
        condition_met = False
        return condition_met
    # if diff_config['T0_offset_text'] == '':
    #     QMessageBox.warning(window, "Input Check", "Please provide T0 offset value.")
    #     condition_met = False
    #     return condition_met
    if diff_config['sambkg_check'] and diff_config['sambkg_text'] =='':
        QMessageBox.warning(window, "Input Check", "Please provide sample background file.")
        condition_met = False
        return condition_met
    if diff_config['sambkg_check'] and diff_config['sam_bkg_text'] =='':
        QMessageBox.warning(window, "Input Check", "Please provide sample-background scale value.")
        condition_met = False
        return condition_met

    if diff_config['v_check'] and diff_config['van_run_text'] =='':
        QMessageBox.warning(window, "Input Check", "Please provide V run file.")
        condition_met = False
        return condition_met

    if diff_config['vbkg_check'] and diff_config['vanbkg_text'] =='':
        QMessageBox.warning(window, "Input Check", "Please provide van background file.")
        condition_met = False
        return condition_met
    if diff_config['vbkg_check'] and diff_config['van_bkg_text'] =='':
        QMessageBox.warning(window, "Input Check", "Please provide van-background scale value.")
        condition_met = False
        return condition_met

    for group in diff_config['group_list']:
        if base_config['d_rebin'][group][0] is None:
            QMessageBox.warning(window, "Input Check", "Please provide d rebin start value.")
            condition_met = False
            return condition_met
        if base_config['d_rebin'][group][1] is None:
            QMessageBox.warning(window, "Input Check", "Please provide d rebin end value.")
            condition_met = False
            return condition_met
        if base_config['d_rebin'][group][2] is None:
            QMessageBox.warning(window, "Input Check", "Please provide d rebin number value.")
            condition_met = False
            return condition_met
    return condition_met

def sq_reduction_check(window, pdf_config):
    condition_met = True
    if pdf_config['pdf_samrun_text'] == '':
        QMessageBox.warning(window, "Input Check", "Please provide sample run file.")
        condition_met = False
        return condition_met
    if pdf_config['pdf_vanrun_text'] == '':
        QMessageBox.warning(window, "Input Check", "Please provide V run file.")
        condition_met = False
        return condition_met
    if pdf_config['pdf_chem_form'] =='':
        QMessageBox.warning(window, "Input Check", "Please provide sample chemical formular.")
        condition_met = False
        return condition_met
    if pdf_config['pdf_mass'] =='':
        QMessageBox.warning(window, "Input Check", "Please provide sample mass.")
        condition_met = False
        return condition_met
    if pdf_config['pdf_radius'] =='':
        QMessageBox.warning(window, "Input Check", "Please provide radius.")
        condition_met = False
        return condition_met
    if pdf_config['pdf_height'] =='':
        QMessageBox.warning(window, "Input Check", "Please provide height.")
        condition_met = False
        return condition_met
    if pdf_config['pdf_instrupath_text'] == '':
        QMessageBox.warning(window, "Input Check", "Please provide instrument file path.")
        condition_met = False
        return condition_met
    if pdf_config['sambkg_text'] == '':
        QMessageBox.warning(window, "Input Check", "Please provide sample background file.")
        condition_met = False
        return condition_met
    if pdf_config['vanbkg_text'] == '':
        QMessageBox.warning(window, "Input Check", "Please provide van background file.")
        condition_met = False
        return condition_met
    if pdf_config['sam_bkg_text'] == '':
        QMessageBox.warning(window, "Input Check", "Please provide sample-bkg value.")
        condition_met = False
        return condition_met
    if pdf_config['van_bkg_text'] == '':
        QMessageBox.warning(window, "Input Check", "Please provide van-bkg value.")
        condition_met = False
        return condition_met
    if pdf_config['pdf_offset_text'] == '':
        QMessageBox.warning(window, "Input Check", "Please provide offset file directory.")
        condition_met = False
        return condition_met
    else:
        try:
            cal_dir = pathlib.Path(pdf_config['pdf_offset_text'])
            cal_fn = list(cal_dir.glob(f'*_offset.cal'))
            _ = read_cal(cal_fn[0])
        except Exception as e:
            print(f"An error occurred: {e}")
            QMessageBox.warning(window, "Input Check", "Uncorrect offset file.")
            condition_met = False
            return condition_met
    if pdf_config['pdf_wavestart'] == '':
        QMessageBox.warning(window, "Input Check", "Please provide wave start value.")
        condition_met = False
        return condition_met
    if pdf_config['pdf_waveend'] == '':
        QMessageBox.warning(window, "Input Check", "Please provide wave end value.")
        condition_met = False
        return condition_met
    # if pdf_config['pdf_T0_offset'] == '':
    #     QMessageBox.warning(window, "Input Check", "Please provide T0 offset value.")
    #     condition_met = False
    #     return condition_met
    return condition_met