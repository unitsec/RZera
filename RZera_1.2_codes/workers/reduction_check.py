from PyQt5.QtWidgets import QMessageBox

def diff_reduction_check(window, diff_config):
    condition_met = True
    if diff_config['sample_run_text'] == '':
        QMessageBox.warning(window, "Input Check", "Please provide sample run file.")
        condition_met = False
        return condition_met
    if diff_config['instru_path_text'] == '':
        QMessageBox.warning(window, "Input Check", "Please provide instrument file path.")
        condition_met = False
        return condition_met
    if diff_config['offset_file_text'] == '':
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
    if diff_config['T0_offset_text'] == '':
        QMessageBox.warning(window, "Input Check", "Please provide T0 offset value.")
        condition_met = False
        return condition_met
    if diff_config['v_check'] and diff_config['van_run_text'] =='':
        QMessageBox.warning(window, "Input Check", "Please provide V run file.")
        condition_met = False
        return condition_met
    if diff_config['hold_check'] and diff_config['hold_run_text'] =='':
        QMessageBox.warning(window, "Input Check", "Please provide hold run file.")
        condition_met = False
        return condition_met
    if diff_config['hold_check'] and diff_config['sample_hold_text'] == '':
        QMessageBox.warning(window, "Input Check", "Please provide sample-hold value.")
        condition_met = False
        return condition_met
    if diff_config['hold_check'] and diff_config['v_check'] and diff_config['v_hold_text'] == '':
        QMessageBox.warning(window, "Input Check", "Please provide van-hold value.")
        condition_met = False
        return condition_met
    if diff_config['diff_bankname'] != 'ALL' and diff_config['diff_d_rebin'][diff_config['diff_bankname']][0] == None:
        QMessageBox.warning(window, "Input Check", "Please provide d rebin start value.")
        condition_met = False
        return condition_met
    if diff_config['diff_bankname'] != 'ALL' and diff_config['diff_d_rebin'][diff_config['diff_bankname']][1] == None:
        QMessageBox.warning(window, "Input Check", "Please provide d rebin end value.")
        condition_met = False
        return condition_met
    if diff_config['diff_bankname'] != 'ALL' and diff_config['diff_d_rebin'][diff_config['diff_bankname']][2] == None:
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
    if pdf_config['pdf_holdrun_text'] == '':
        QMessageBox.warning(window, "Input Check", "Please provide hold run file.")
        condition_met = False
        return condition_met
    if pdf_config['pdf_bkg_check'] and pdf_config['pdf_bkgrun_text'] == '':
        QMessageBox.warning(window, "Input Check", "Please provide bkg run file.")
        condition_met = False
        return condition_met
    if pdf_config['pdf_sam_hold'] == '':
        QMessageBox.warning(window, "Input Check", "Please provide sample-hold value.")
        condition_met = False
        return condition_met
    if pdf_config['pdf_van_hold'] == '':
        QMessageBox.warning(window, "Input Check", "Please provide van-hold value.")
        condition_met = False
        return condition_met
    if pdf_config['pdf_offset_text'] == '':
        QMessageBox.warning(window, "Input Check", "Please provide offset file directory.")
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
    if pdf_config['pdf_T0_offset'] == '':
        QMessageBox.warning(window, "Input Check", "Please provide T0 offset value.")
        condition_met = False
        return condition_met
    return condition_met