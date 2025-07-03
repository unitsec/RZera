from BL09_TREND.workers.browse_file import browse_file
import traceback


def mode_check(text, sample_run_button, sample_run_text, batch_reduction_check=None):
    # 根据下拉选框的选择来启用或禁用控件
    if text == 'online':
        sample_run_button.setEnabled(False)
        sample_run_text.setEnabled(False)
        if batch_reduction_check is not None:
            batch_reduction_check.setEnabled(False)
    elif text == 'offline':
        sample_run_button.setEnabled(True)
        sample_run_text.setEnabled(True)
        if batch_reduction_check is not None:
            batch_reduction_check.setEnabled(True)


def browse_mode_check(combobox, run_filePaths, run_text, parent=None):
    try:
        browse_file_instance = browse_file()
        if combobox.currentText() == 'nxs':
            browse_file_instance.select_nxsfiles(run_text,run_filePaths,parent)
        else:
            browse_file_instance.select_folder(run_text, parent)
    except Exception as e:
        print(f"An error occurred: {e}")
        traceback.print_exc()  # 打印异常的堆栈跟踪


def change_rebin_mode(bank_name, rebin_start, rebin_end, rebin_number, BL09_config):
    # 根据下拉选框的选择来启用或禁用控件
    if bank_name == 'ALL':
        rebin_start.setText('')
        rebin_end.setText('')
        rebin_number.setText('')
        rebin_start.setEnabled(False)
        rebin_end.setEnabled(False)
        rebin_number.setEnabled(False)
    else:
        rebin_start.setEnabled(True)
        rebin_end.setEnabled(True)
        rebin_number.setEnabled(True)
        if bank_name == 'bank2':
            rebin_start.setText(str(BL09_config['d_rebin']['bank2'][0]))
            rebin_end.setText(str(BL09_config['d_rebin']['bank2'][1]))
            rebin_number.setText(str(BL09_config['d_rebin']['bank2'][2]))
        elif bank_name == 'bank3':
            rebin_start.setText(str(BL09_config['d_rebin']['bank3'][0]))
            rebin_end.setText(str(BL09_config['d_rebin']['bank3'][1]))
            rebin_number.setText(str(BL09_config['d_rebin']['bank3'][2]))
        elif bank_name == 'bank4':
            rebin_start.setText(str(BL09_config['d_rebin']['bank4'][0]))
            rebin_end.setText(str(BL09_config['d_rebin']['bank4'][1]))
            rebin_number.setText(str(BL09_config['d_rebin']['bank4'][2]))
        elif bank_name == 'bank5':
            rebin_start.setText(str(BL09_config['d_rebin']['bank5'][0]))
            rebin_end.setText(str(BL09_config['d_rebin']['bank5'][1]))
            rebin_number.setText(str(BL09_config['d_rebin']['bank5'][2]))
        elif bank_name == 'bank6':
            rebin_start.setText(str(BL09_config['d_rebin']['bank6'][0]))
            rebin_end.setText(str(BL09_config['d_rebin']['bank6'][1]))
            rebin_number.setText(str(BL09_config['d_rebin']['bank6'][2]))
        elif bank_name == 'bank7':
            rebin_start.setText(str(BL09_config['d_rebin']['bank7'][0]))
            rebin_end.setText(str(BL09_config['d_rebin']['bank7'][1]))
            rebin_number.setText(str(BL09_config['d_rebin']['bank7'][2]))