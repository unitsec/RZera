######################设计这个模块的原因是：给用户提供一个可以一键规约数据的选择#######################################
from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QLineEdit,QMessageBox,QLabel,QHeaderView,QApplication,QComboBox
from PyQt5.QtGui import QDoubleValidator, QIntValidator, QFont
from utils.browse import browse
from collections import defaultdict
import re,copy,os,time
from rongzai.utils import get_all_from_detector
from rongzai.dataSvc import load_histogram_data,load_event_data
from PyQt5.QtWidgets import QTableWidgetItem, QCheckBox, QWidget, QHBoxLayout, QVBoxLayout, QProgressBar, QDialog
from PyQt5.QtCore import Qt, QObject, QThread, pyqtSignal
from rongzai.algSvc.neutron import convert_unit_elastic
from rongzai.algSvc.instrument.timefocus_correction import correct_tof_to_d
from rongzai.dataSvc import read_mask,read_cal,read_instrument_info
from rongzai.algSvc.neutron import mask_neutron_data,crop_neutron_data,focus_neutron_data,rebin_neutron_data,correct_carpenter,calculate_neutron_data
from rongzai.algSvc.base import get_sample_properties
from rongzai.algSvc.instrument.timeslice import *
from rongzai.utils.histogram import Hist2D
import numpy as np
from utils.ui.BaseUI import CollapsibleWidget
from utils.helper import upgrade_positions_to_8cols
from rongzai.dataSvc import read_dataset,create_dataset
from utils.helper import load_dat_data,extract_info_from_datfn
import json

class reduction(CollapsibleWidget):
    # finished = pyqtSignal()
    def __init__(self, name, parent):
        super(reduction, self).__init__(name, "utils/ui/reduction.ui", parent)
        self.parent = parent

        self.validator = QDoubleValidator(0.0, float('inf'), 8, self)  # 创建一个浮点数验证器，限制输入范围在 [0.0, +∞)，且最多允许 8 位小数
        self.validator.setNotation(QDoubleValidator.StandardNotation)  # 强制使用标准十进制表示法（避免科学计数法）

        validator2 = QDoubleValidator(-float('inf'), float('inf'), 8, self)  # 创建一个浮点数验证器，限制输入范围在 [0.0, +∞)，且最多允许 8 位小数
        validator2.setNotation(QDoubleValidator.StandardNotation)  # 强制使用标准十进制表示法（避免科学计数法）

        self.sam_fn = []
        self.browse_run = browse()
        self.sample_button.clicked.connect(lambda: self.browse_run.select_nxsfiles(self.sample_text, self.sam_fn))
        
        self.samBG_fn = []
        self.samBG_button.clicked.connect(lambda:(self.samBG_datatypeCheck(),self.set_default_rebin))
        self.samBG_datatype.currentTextChanged.connect(lambda: (self.samBG_text.setText(''),self.samBG_fn.clear(),self.set_default_rebin()))
        
        self.v_fn = []
        self.v_button.clicked.connect(lambda:(self.v_datatypeCheck(),self.set_default_rebin))
        self.v_datatype.currentTextChanged.connect(lambda: (self.v_text.setText(''), self.v_fn.clear(), self.set_default_rebin()))

        self.vBG_fn = []
        self.vBG_button.clicked.connect(lambda:(self.vBG_datatypeCheck(),self.set_default_rebin))
        self.vBG_datatype.currentTextChanged.connect(lambda: (self.vBG_text.setText(''), self.vBG_fn.clear(),self.set_default_rebin()))


        ####################### 配置slice参数 #############################
        self.tof_step.setValidator(self.validator)
        self.tof_step.setText("8")
        self.operate_slicepara = operate_slicepara(self)
        self.add_slice.clicked.connect(lambda: self.operate_slicepara.add_row())
        self.remove_slice.clicked.connect(lambda: self.operate_slicepara.remove_row())
        self.load_evt_button.clicked.connect(
            lambda: (
                self.browse_run.select_folder(self.evt_text),
                self.check_evt_files() if self.evt_text.text().strip() else None
            )
        )
        #################################################################

        self.detector_button.clicked.connect(
            lambda: (self.browse_run.select_detectors(self.detector_text, self.parent.config['base']['group_info'], self.parent.config['base']['bank_info']),
                    self.set_default_rebin())
                    )

        self.instru_button.clicked.connect(lambda: self.browse_run.select_folder(self.instru_text))


        self.t0_text.setValidator(validator2) # 将 doubleValidator 设置到 QLineEdit 控件上 (只能输入浮点数)
        self.t0_text.setText('0.0')

        self.mask_button.clicked.connect(lambda: self.browse_run.select_folder(self.mask_text))

        self.wave_min.setValidator(self.validator)  # 将 doubleValidator 设置到 QLineEdit 控件上 (只能输入浮点数)
        self.wave_max.setValidator(self.validator)

        # 初始化carpenter correction
        self.mass.setValidator(self.validator)
        self.mass.setText("1.0")
        self.sam_height.setValidator(self.validator)
        self.sam_height.setText("3.0")
        self.radius_text.setValidator(self.validator)
        self.radius_text.setText("0.5")
        self.beam_height.setValidator(self.validator)
        self.beam_height.setText("3.0")
        self.num_density_text.setValidator(self.validator)
        self.num_density_text.setText("0.01")
        self.num_density_check.stateChanged.connect(lambda state: self.num_density_text.setEnabled(state == 2))
        self.num_density_check.setChecked(False)
        self.sample_name.textChanged.connect(self.update_num_density_label)
        self.mass.textChanged.connect(self.update_num_density_label)
        self.sam_height.textChanged.connect(self.update_num_density_label)
        self.radius_text.textChanged.connect(self.update_num_density_label)
        self.beam_height.textChanged.connect(self.update_num_density_label)

        self.offset_button.clicked.connect(lambda: self.browse_run.select_folder(self.offset_text))

        self.samBG_scale.setValidator(self.validator)
        self.samBG_scale.setText("1.0")
        self.vBG_scale.setValidator(self.validator)
        self.vBG_scale.setText("0.5")

        self.set_default_crop()

        self.load_button.clicked.connect(self.load)
        self.checkboxes = []  # 存储复选框引用
        self.delete_button.clicked.connect(lambda: self.delete_selected_rows())
        self.delete_all_button.clicked.connect(self.delete_all_rows)


    def samBG_datatypeCheck(self):
        if self.samBG_datatype.currentText() == 'nxs':
            self.browse_run.select_nxsfiles(self.samBG_text, self.samBG_fn, self)
        elif self.samBG_datatype.currentText() == 'nc':
            self.browse_run.select_ncfiles(self.samBG_fn,self)
            file_names = [os.path.basename(path) for path in self.samBG_fn]
            file_names_str = '; '.join(file_names)
            self.samBG_text.setText(file_names_str)
        else:
            self.browse_run.select_datfiles(self.samBG_fn, self)
            file_names = [os.path.basename(path) for path in self.samBG_fn]
            file_names_str = '; '.join(file_names)
            self.samBG_text.setText(file_names_str)
            
    def v_datatypeCheck(self):
        if self.v_datatype.currentText() == 'nxs':
            self.browse_run.select_nxsfiles(self.v_text, self.v_fn, self)
        elif self.v_datatype.currentText() == 'nc':
            self.browse_run.select_ncfiles(self.v_fn,self)
            file_names = [os.path.basename(path) for path in self.v_fn]
            file_names_str = '; '.join(file_names)
            self.v_text.setText(file_names_str)
        else:
            self.browse_run.select_datfiles(self.v_fn, self)
            file_names = [os.path.basename(path) for path in self.v_fn]
            file_names_str = '; '.join(file_names)
            self.v_text.setText(file_names_str)
            
    def vBG_datatypeCheck(self):
        if self.vBG_datatype.currentText() == 'nxs':
            self.browse_run.select_nxsfiles(self.vBG_text, self.vBG_fn, self)
        elif self.vBG_datatype.currentText() == 'nc':
            self.browse_run.select_ncfiles(self.vBG_fn,self)
            file_names = [os.path.basename(path) for path in self.vBG_fn]
            file_names_str = '; '.join(file_names)
            self.vBG_text.setText(file_names_str)
        else:
            self.browse_run.select_datfiles(self.vBG_fn, self)
            file_names = [os.path.basename(path) for path in self.vBG_fn]
            file_names_str = '; '.join(file_names)
            self.vBG_text.setText(file_names_str)

    def set_default_crop(self):
        try:
            wave_max = self.parent.config["base"]["wave_max"]
            wave_min = self.parent.config["base"]["wave_min"]
            self.wave_min.setText(str(wave_min))
            self.wave_max.setText(str(wave_max))
        except Exception as e:
            print(f'Reason: {e}')
            traceback.print_exc()  # 打印异常的堆栈跟踪

    def set_default_rebin(self):
        try:
            detectors_set = set()

            text = self.detector_text.text()
            sam_detectors_list = [s for s in text.split('; ') if s]
            detectors_set.update(sam_detectors_list)
            
            if self.samBG_datatype.currentText() == 'dat':
                for fn in self.samBG_fn:
                    samBG_detector = [extract_info_from_datfn(fn,"detector")]
                    detectors_set.update(samBG_detector)
            elif self.samBG_datatype.currentText() == 'nc':
                for fn in self.samBG_fn:
                    dataset = read_dataset(fn)
                    detectors_set.update([dataset.name])
                    
            if self.v_datatype.currentText() == 'dat':
                for fn in self.v_fn:
                    v_detector = [extract_info_from_datfn(fn,"detector")]
                    detectors_set.update(v_detector)
            elif self.v_datatype.currentText() == 'nc':
                for fn in self.v_fn:
                    dataset = read_dataset(fn)
                    detectors_set.update([dataset.name])

            if self.vBG_datatype.currentText() == 'dat':
                for fn in self.vBG_fn:
                    vBG_detector = [extract_info_from_datfn(fn,"detector")]
                    detectors_set.update(vBG_detector)
            elif self.vBG_datatype.currentText() == 'nc':
                for fn in self.vBG_fn:
                    dataset = read_dataset(fn)
                    detectors_set.update([dataset.name])

            detectors_list = list(detectors_set)
            self.delete_extra_rows(detectors_list)
            self.add_default_rows(detectors_list)
        except Exception as e:
            print(f'Reason: {e}')
            traceback.print_exc()  # 打印异常的堆栈跟踪

    def delete_extra_rows(self,selected_detectors):
        try:
            rows_to_remove = []
            for row in range(self.drebinWidget.rowCount()):
                existing_detector_item = self.drebinWidget.item(row, 0)
                detector_exists = False
                for detector in selected_detectors:
                    if existing_detector_item and existing_detector_item.text() == detector:
                        detector_exists = True
                        break
                if not detector_exists:
                    rows_to_remove.append(row)
            if rows_to_remove:
                # 按降序排序以避免删除行时影响其他待删除行的索引
                rows_to_remove.sort(reverse=True)
                # 删除表格行
                for row in rows_to_remove:
                    self.drebinWidget.removeRow(row)
        except Exception as e:
            print(f'Reason: {e}')
            import traceback
            traceback.print_exc()  # 打印异常的堆栈跟踪
                
    def add_default_rows(self, selected_files):
        for file in selected_files:
            # 检查文件是否已经存在于 tableWidget 中
            file_exists = False
            for row in range(self.drebinWidget.rowCount()):
                existing_file_item = self.drebinWidget.item(row, 0)
                if existing_file_item and existing_file_item.text() == file:
                    file_exists = True
                    break

            # 如果文件不存在，则添加新行
            if not file_exists:
                row_position = self.drebinWidget.rowCount()
                self.drebinWidget.insertRow(row_position)

                # 第1列: 文件名
                file_item = QTableWidgetItem(file)
                self.drebinWidget.setItem(row_position, 0, file_item)

                group, _ = get_all_from_detector(file, self.parent.config['base']['group_info'],
                                                       self.parent.config['base']['bank_info'])
                # 第2-4列: 可以输入浮点数的 QLineEdit
                for col in range(1, 4):
                    int_edit = QLineEdit()
                    int_edit.setValidator(self.validator)  # 仅允许输入浮点数
                    try:
                        int_edit.setText(str(self.parent.config["base"]["d_rebin"][file][col-1]))
                    except:
                        int_edit.setText(str(self.parent.config["base"]["d_rebin"][group][col - 1]))
                    self.drebinWidget.setCellWidget(row_position, col, int_edit)

                # 第5列: ComboBox
                combo_box = QComboBox()
                combo_box.addItems(["uniform", "log_10", "log_e", "deltaX_X"])
                try:
                    combo_box.setCurrentText(self.parent.config["base"]["d_rebin"]["mode"])  # 默认选择第一个选项
                except:
                    combo_box.setCurrentIndex(0)  # 默认选择第一个选项
                # 存储combo box的引用以便后续访问
                # self.combo_boxes.append((row_position, combo_box))
                self.drebinWidget.setCellWidget(row_position, 4, combo_box)

    def extract_drebin_from_table(self):
        drebin = {}
        combobox_choices = {}  # 新增的字典，用于存储ComboBox选择
        num_rows = self.drebinWidget.rowCount()

        for row in range(num_rows):
            # 获取第一列的文件名作为字典的 key
            detector_name = self.drebinWidget.item(row, 0).text()

            # 获取第2至第4列的数值
            for col in range(1, 4):
                edit = self.drebinWidget.cellWidget(row, col)
                if edit is not None:
                    try:
                        if col == 1:
                            dstart = float(edit.text())
                        elif col == 2:
                            dend = float(edit.text())
                        elif col == 3:
                            dnumber = float(edit.text())
                    except ValueError:
                        self.show_error_message(
                            f"Invalid input at row {row + 1}, column {col + 1}. Please enter a valid number.")
                        return None, None  # 返回两个None表示出错

            # 获取第5列的ComboBox选择（列索引4）
            combo_box = self.drebinWidget.cellWidget(row, 4)
            if combo_box is not None:
                combo_choice = combo_box.currentText()
            else:
                combo_choice = "uniform"  # 默认值

            # 将值添加到字典中
            if detector_name not in drebin:
                drebin[detector_name] = [dstart, dend, dnumber]
                combobox_choices[detector_name] = combo_choice

        return drebin, combobox_choices  # 返回两个字典

    def plot_data(self):
        if self.toggle_button.isChecked():
            plot_data = []
            for data in self.parent.data_list:
                if "detector_focused" in data:
                    plot_data.append({"name": f"{data['name']}_{data['detector']}",
                                      "data": [copy.deepcopy(data["detector_focused"]["xvalue"].values[0]),
                                               copy.deepcopy(data["detector_focused"]["histogram"].values[0]),
                                               copy.deepcopy(data["detector_focused"]["error"].values[0])],
                                      "x_label": "d (Å)",
                                      "y_label": "Intensity (a.u.)"})
            return plot_data
        else:
            return []

    def check_ui(self):
        if self.instru_text.text() == "":
            QMessageBox.warning(self, "warning", "The Instru Folder is blank, pleas check!")
            return False

        if self.samBG_datatype.currentText() != "nxs":
            for samBG_fn in self.samBG_fn:
                try:
                    if self.samBG_datatype.currentText() == "nc":
                        dataset = read_dataset(samBG_fn)
                    else:
                        dataset = load_dat_data(samBG_fn)
                except:
                    QMessageBox.warning(self, "warning", f"Can't load the samBG file from {samBG_fn}, please check!")
                    return False
        # v_detectors = []
        for v_fn in self.v_fn:
            try:
                if self.v_datatype.currentText() == "nc":
                    dataset = read_dataset(v_fn)
                else:
                    dataset = load_dat_data(v_fn)
            except:
                QMessageBox.warning(self, "warning", f"Can't load the v file from {v_fn}, please check!")
                return False
        #     v_detectors.append(dataset.name)
        # for detector in detectors_list:
        #     if detector not in v_detectors:
        #         QMessageBox.warning(self, "warning", f"The {detector} is not in the Van.")
        # vBG_detectors = []
        for vBG_fn in self.vBG_fn:
            try:
                if self.vBG_datatype.currentText() == "nc":
                    dataset = read_dataset(vBG_fn)
                else:
                    dataset = load_dat_data(vBG_fn)
            except:
                QMessageBox.warning(self, "warning", f"Can't load the vBG file from {vBG_fn}, please check!")
                return False
        #     vBG_detectors.append(dataset.name)
        # for detector in detectors_list:
        #     if detector not in vBG_detectors:
        #         QMessageBox.warning(self, "warning", f"The {detector} is not in the Van Bkg.")
        return True

    def load(self):
        try:
            if self.toggle_button.isChecked():
                self.load_button.setEnabled(False)
                if not self.check_ui():
                    self.operation_after_finish()
                    return
                if self.tabWidget.currentWidget().objectName() == "histogram":
                    if self.is_batch.isChecked():
                        mode = 'batch'
                    else:
                        mode = 'merge'
                    # 创建线程和 Worker 对象
                    self.thread = QThread()
                    self.worker = LoadThreadManager(mode, self)
                    self.worker.moveToThread(self.thread)

                    # 创建进度条弹出窗口
                    self.progress_dialog = ProgressDialog(self.thread, self)
                    self.progress_dialog.show()

                    # 连接信号和槽
                    self.thread.started.connect(self.worker.run)  # 线程启动时执行 Worker 的 run 方法
                    self.worker.finished.connect(self.thread.quit)  # 任务完成时退出线程
                    self.worker.finished.connect(self.worker.deleteLater)  # 任务完成后删除 Worker 对象
                    self.thread.finished.connect(self.thread.deleteLater)  # 线程退出后删除线程对象
                    self.worker.error.connect(self.handle_error)  # 处理任务中的错误
                    self.worker.data_ready.connect(self.on_data_ready)  # 处理数据信号
                    self.worker.progress.connect(self.progress_dialog.progress_bar.setValue)  # 更新进度条
                    self.worker.progress_text.connect(self.progress_dialog.update_info)  # 更新进度条
                    self.worker.finished.connect(lambda: (self.progress_dialog.close(),self.operation_after_finish()))  # 任务完成后关闭进度条窗口

                    # 启动线程
                    self.thread.start()
                elif self.tabWidget.currentWidget().objectName() == "event":
                    if not self.check_timeslice_param():
                        self.operation_after_finish()
                        return
                    # 创建线程和 Worker 对象
                    self.evt_thread = QThread()
                    self.worker = LoadThreadManager("batch", self)
                    self.worker.moveToThread(self.evt_thread)

                    # 创建进度条弹出窗口
                    self.evt_progress_dialog = ProgressDialog(self.evt_thread, self)
                    self.evt_progress_dialog.show()

                    # 连接信号和槽
                    self.evt_thread.started.connect(self.worker.run_slice)  # 线程启动时执行 Worker 的 run 方法
                    self.worker.finished.connect(self.evt_thread.quit)  # 任务完成时退出线程
                    self.worker.finished.connect(self.worker.deleteLater)  # 任务完成后删除 Worker 对象
                    self.evt_thread.finished.connect(self.evt_thread.deleteLater)  # 线程退出后删除线程对象
                    self.worker.error.connect(self.handle_error)  # 处理任务中的错误
                    self.worker.data_ready.connect(self.on_data_ready)  # 处理数据信号
                    self.worker.progress.connect(self.evt_progress_dialog.progress_bar.setValue)  # 更新进度条
                    self.worker.progress_text.connect(self.evt_progress_dialog.update_info)  # 更新进度条
                    self.worker.finished.connect(lambda: (self.evt_progress_dialog.close(),self.operation_after_finish()))  # 任务完成后关闭进度条窗口

                    # 启动线程
                    self.evt_thread.start()


        except Exception as e:
            print(f'Reason: {e}')
            traceback.print_exc()  # 打印异常的堆栈跟踪

    def check_event_param(self):
        slice_params = self.operate_slicepara.extract_slice_info()
        for i, param in enumerate(slice_params):
            try:
                start_time = float(param[0])
                end_time = float(param[1])
                num_splits = int(param[2])
            except (TypeError, ValueError):
                QMessageBox.warning(self, "error from slice parameter",
                                    f"The slice parameter in row {i + 1} is invalid, please check!")
                return False

            if start_time >= end_time:
                QMessageBox.warning(self, "error from slice parameter",
                                    f"The start time in row {i + 1} must be smaller than the end time, please check!")
                return False

            if num_splits <= 0:
                QMessageBox.warning(self, "error from slice parameter",
                                    f"The slice number in row {i + 1} must be a positive integer, please check!")
                return False
        return True

    def extract_detectors_from_lineedit(self, lineEdit):
        detector_list = lineEdit.text().split('; ')
        return detector_list

    def get_selected_event_modules(self):
        modules_list = set()
        detectors = self.extract_detectors_from_lineedit(self.detector_text)
        for detector in detectors:
            if not detector:
                continue
            _, modules = get_all_from_detector(detector,
                                               self.parent.config['base']['group_info'],
                                               self.parent.config['base']['bank_info'])
            modules_list.update(modules)

        monitor_name = self.parent.config['base'].get('normalization_monitor')
        if monitor_name:
            monitor_pattern = os.path.join(self.evt_text.text(), f"{monitor_name}_evt_*.nxs")
            if glob.glob(monitor_pattern):
                modules_list.add(monitor_name)
        return sorted(modules_list)

    def check_selected_evt_files(self):
        evt_dir = self.evt_text.text()
        missing_modules = []
        for module in self.get_selected_event_modules():
            module_pattern = os.path.join(evt_dir, f"{module}_evt_*.nxs")
            if not glob.glob(module_pattern):
                missing_modules.append(module)

        if missing_modules:
            QMessageBox.warning(
                self,
                "warning",
                "The evt files of these modules are missing:\n" + "\n".join(missing_modules)
            )
            return False
        return True

    def check_timeslice_param(self):
        if self.instru_text.text() == "":
            QMessageBox.warning(self, "warning", "The Instru Folder is blank, pleas check!")
            return False
        if self.evt_text.text() == "":
            QMessageBox.warning(self, "warning", "The Event Data Folder is blank, pleas check!")
            return False
        if self.detector_text.text() == "":
            QMessageBox.warning(self, "warning", "The Detector is blank, pleas check!")
            return False
        if not self.check_event_param():
            return False
        evt_num = self.check_evt_num()
        if evt_num == 0:
            QMessageBox.warning(self, "warning", "The number of each module's evt files is not same. Please Check!")
            return False
        if evt_num == -1:
            QMessageBox.warning(self, "warning", "The number of each module's evt files is 0! Please Check!")
            return False
        if not self.check_pc_file():
            QMessageBox.warning(self, "warning", "The pc_*.nxs is not exist in this folder. Please Check!")
            return False
        if not self.check_selected_evt_files():
            return False
        return True


   # 该方法需要在run方法的最后调用，目的是供上层在调用该模块时，检测任务是否完成。
    def operation_after_finish(self):
        # self.finished.emit()  # 定义一个信号
        # print(len(self.parent.data_list))
        self.load_button.setEnabled(True)
        return

    def update_num_density_label(self):
        try:
            info = self.get_correction_info()
            cal_info = get_sample_properties(info)
            cal_num_density = cal_info["density_num"]
            self.num_density_label.setText(f"Calculated Num Density:{cal_num_density:.6f} Å⁻³")
        except:
            self.num_density_label.setText(f"Calculated Num Density:0.000000 Å⁻³")

    def get_correction_info(self):
        """获取校正参数"""
        return {
            "sample_name": self.sample_name.text(),
            "mass": float(self.mass.text()),
            "volume": {
                "type": "cylinder",
                "height": float(self.sam_height.text()),
                "radius": float(self.radius_text.text()),
                "beam_height": float(self.beam_height.text()),
                "thickness": 0},
            "scale": 1
        }

    def on_data_ready(self, data_dict):
        try:
            # 在主线程中操作 UI 和共享数据
            self.parent.data_list.append(data_dict)
            self.append_data([data_dict])
        except Exception as e:
            print(f'Reason: {e}')
            traceback.print_exc()  # 打印异常的堆栈跟踪

    def handle_error(self, error_message):
        QMessageBox.warning(self,"error", error_message)

    def adjust_colWidth(self, col):
        # 动态调整列宽
        self.tableWidget.horizontalHeader().setSectionResizeMode(
            col, QHeaderView.ResizeToContents  # 设置目标列调整模式:ml-citation{ref="5" data="citationList"}
        )
        self.tableWidget.resizeColumnToContents(col)  # 立即触发调整:ml-citation{ref="1" data="citationList"}

    def insert_data(self, row, data):
        self.tableWidget.setItem(row, 0, QTableWidgetItem(data["name"])) # 第一列 - RunNo
        self.adjust_colWidth(0)

        self.tableWidget.setItem(row, 1, QTableWidgetItem(data["detector"])) # 第二列 - Detector
        self.adjust_colWidth(1)

        # 第三列 - 复选框
        chk_box_item = QWidget()
        layout = QHBoxLayout()
        layout.setAlignment(Qt.AlignCenter)
        checkbox = QCheckBox()
        layout.addWidget(checkbox)
        chk_box_item.setLayout(layout)
        self.tableWidget.setCellWidget(row, 2, chk_box_item)
        self.checkboxes.append((row, checkbox))  # 保存复选框的引用
        self.adjust_colWidth(2)

    def append_data(self, new_data_list):
        current_row_count = self.tableWidget.rowCount()
        new_row_count = current_row_count + len(new_data_list)
        self.tableWidget.setRowCount(new_row_count)

        for data in new_data_list:
            self.insert_data(current_row_count, data)
            current_row_count += 1

    def delete_selected_rows(self):
        try:
            rows_to_remove = []
            to_delete_set = set()  # 使用集合以避免重复记录

            # 第一次通过checkboxes记录要删除的数据的标志
            for row, checkbox in self.checkboxes:
                if checkbox.isChecked():
                    runno_item = self.tableWidget.item(row, 0)
                    detector_item = self.tableWidget.item(row, 1)
                    if runno_item and detector_item:
                        runno = runno_item.text()
                        detector = detector_item.text()
                        # 将将要删除的数据标记放入集合中
                        to_delete_set.add((runno, detector))
                        rows_to_remove.append(row)

            # 生成新的数据列表，通过不包含标记的项
            new_data_list = [data for data in self.parent.data_list
                             if (data["name"], data["detector"]) not in to_delete_set]

            # 替换为过滤后的数据列表
            self.parent.data_list = new_data_list

            # 按降序排序以避免删除行时影响其他待删除行的索引
            rows_to_remove.sort(reverse=True)

            # 删除表格行
            for row in rows_to_remove:
                self.tableWidget.removeRow(row)

            # 更新复选框引用，重建剩余复选框的列表
            new_checkboxes = []
            for row in range(self.tableWidget.rowCount()):
                checkbox = self.tableWidget.cellWidget(row, 2).layout().itemAt(0).widget()
                new_checkboxes.append((row, checkbox))
            self.checkboxes = new_checkboxes
        except Exception as e:
            print(f'Reason: {e}')
            traceback.print_exc()  # 打印异常的堆栈跟踪

    def delete_all_rows(self):
        try:
            rows_to_remove = []
            to_delete_set = set()  # 使用集合以避免重复记录

            # 第一次通过checkboxes记录要删除的数据的标志
            for row, checkbox in self.checkboxes:
                runno_item = self.tableWidget.item(row, 0)
                detector_item = self.tableWidget.item(row, 1)
                if runno_item and detector_item:
                    runno = runno_item.text()
                    detector = detector_item.text()
                    # 将要删除的数据标记放入集合中
                    to_delete_set.add((runno, detector))
                    rows_to_remove.append(row)

            # 生成新的数据列表，通过不包含标记的项
            new_data_list = [data for data in self.parent.data_list
                             if (data["name"], data["detector"]) not in to_delete_set]

            # 替换为过滤后的数据列表
            self.parent.data_list = new_data_list

            # 按降序排序以避免删除行时影响其他待删除行的索引
            rows_to_remove.sort(reverse=True)

            # 删除表格行
            for row in rows_to_remove:
                self.tableWidget.removeRow(row)

            # 更新复选框引用，重建剩余复选框的列表
            new_checkboxes = []
            for row in range(self.tableWidget.rowCount()):
                checkbox = self.tableWidget.cellWidget(row, 2).layout().itemAt(0).widget()
                new_checkboxes.append((row, checkbox))
            self.checkboxes = new_checkboxes
        except Exception as e:
            traceback.print_exc()  # 打印异常的堆栈跟踪


    def set_scrollArea(self, slice_parameters):
        # 首先清除现有的行
        while self.operate_slicepara.rows:
            self.operate_slicepara.remove_row()

        # 重新构建行
        for start, end, num in slice_parameters:
            self.operate_slicepara.add_row()
            last_row_index = len(self.operate_slicepara.rows) - 1
            row = self.operate_slicepara.rows[last_row_index]

            # 设置每一行的控件值
            row['start_value'].setText(str(start))
            row['end_value'].setText(str(end))
            row['num_splits'].setText(str(num))

    def save_rebintable(self):
        """保存表格数据到 JSON 文件"""
        table_data = []
        for row in range(self.drebinWidget.rowCount()):
            row_data = []
            for col in range(self.drebinWidget.columnCount()):
                if col == 0:  # 处理 QdrebinWidgetItem
                    item = self.drebinWidget.item(row, col)
                    if item is not None:
                        row_data.append({"type": "item", "value": item.text()})
                    else:
                        row_data.append({"type": "item", "value": ""})  # 空单元格
                elif col in (1, 2, 3):  # 处理 QLineEdit (第2-4列)
                    widget = self.drebinWidget.cellWidget(row, col)
                    if isinstance(widget, QtWidgets.QLineEdit):
                        row_data.append({"type": "line_edit", "value": widget.text()})
                    else:
                        row_data.append({"type": "line_edit", "value": ""})  # 默认值
                elif col == 4:  # 处理 QComboBox (第5列)
                    widget = self.drebinWidget.cellWidget(row, col)
                    if isinstance(widget, QtWidgets.QComboBox):
                        row_data.append({
                            "type": "combobox",
                            "value": widget.currentText(),
                            "options": [widget.itemText(i) for i in range(widget.count())]
                        })
                    else:
                        row_data.append({
                            "type": "combobox",
                            "value": "uniform",
                            "options": ["uniform", "log_10", "log_e", "deltaX_X"]
                        })  # 默认值
            table_data.append(row_data)
        return table_data
    
    def load_rebintable(self, table_data):
        """从 JSON 文件加载表格数据"""
        try:
            # 设置表格的行数和列数
            self.drebinWidget.setRowCount(len(table_data))
            if len(table_data) > 0:
                self.drebinWidget.setColumnCount(len(table_data[0]))
            # 填充数据
            for row, row_data in enumerate(table_data):
                for col, cell_data in enumerate(row_data):
                    if cell_data["type"] == "item":  # 处理 QdrebinWidgetItem
                        item = QtWidgets.QTableWidgetItem(cell_data["value"])
                        self.drebinWidget.setItem(row, col, item)
                    elif cell_data["type"] == "line_edit":  # 处理 QLineEdit
                        line_edit = QtWidgets.QLineEdit(cell_data["value"])
                        line_edit.setValidator(self.validator)  # 设置验证器
                        self.drebinWidget.setCellWidget(row, col, line_edit)
                    elif cell_data["type"] == "combobox":  # 处理 QComboBox
                        combo = QtWidgets.QComboBox()
                        combo.addItems(cell_data["options"])
                        # 设置当前选中的项
                        index = combo.findText(cell_data["value"])
                        if index >= 0:
                            combo.setCurrentIndex(index)
                        self.drebinWidget.setCellWidget(row, col, combo)
        except FileNotFoundError:
            print("Table data file not found!")
        except Exception as e:
            print(f"Error loading table data: {e}")
    
    def get_config(self):
        return {
            "detector_text": self.detector_text.text(),
            "sam_text": self.sample_text.text(),
            "is_batch": self.is_batch.isChecked(),
            "instru_text": self.instru_text.text(),
            "t0_text": self.t0_text.text(),
            "sam_fn": self.sam_fn,
            "samBG_text": self.samBG_text.text(),
            "samBG_datatype": self.samBG_datatype.currentText(),
            "samBG_fn": self.samBG_fn,
            "v_text": self.v_text.text(),
            "v_datatype": self.v_datatype.currentText(),
            "v_fn": self.v_fn,
            "vBG_text": self.vBG_text.text(),
            "vBG_datatype": self.vBG_datatype.currentText(),
            "vBG_fn": self.vBG_fn,
            "is_mask": self.is_mask.isChecked(),
            "mask_text": self.mask_text.text(),
            "is_crop": self.is_crop.isChecked(),
            "wave_min": self.wave_min.text(),
            "wave_max": self.wave_max.text(),
            "is_correction": self.is_correction.isChecked(),
            "sample_name": self.sample_name.text(),
            "mass": self.mass.text(),
            "radius": self.radius_text.text(),
            "sam_height": self.sam_height.text(),
            "beam_height": self.beam_height.text(),
            "num_density_check": self.num_density_check.isChecked(),
            "num_density_text": self.num_density_text.text(),
            "rebin_info": self.save_rebintable(),
            "is_offset": self.is_offset.isChecked(),
            "plot": self.plot.isChecked(),
            "offset_text": self.offset_text.text(),
            "evt_text": self.evt_text.text(),
            "exp_time": self.exp_time.text(),
            "tof_step": self.tof_step.text(),
            "slice_parameters": self.operate_slicepara.extract_slice_info(),
            "which_tab": self.tabWidget.currentIndex(),
            "pc_check": self.proton_nor.isChecked(),
            "monitor_check": self.monitor_nor.isChecked(),
            "samBG_scale": self.samBG_scale.text(),
            "vBG_scale": self.vBG_scale.text(),
            "is_use": self.toggle_button.isChecked()
        }

    def set_config(self,config):
        """根据配置更新模块状态"""
        self.detector_text.setText(config.get("detector_text", ""))
        self.sample_text.setText(config.get("sam_text", ""))
        self.is_batch.setChecked(config.get("is_batch",False))
        self.instru_text.setText(config.get("instru_text", ""))
        self.t0_text.setText(config.get("t0_text", ""))
        self.sam_fn = config.get("sam_fn",[])
        self.samBG_datatype.setCurrentText(config.get("samBG_datatype", "nc"))
        self.samBG_text.setText(config.get("samBG_text", ""))
        self.samBG_fn = config.get("samBG_fn", [])
        self.v_datatype.setCurrentText(config.get("v_datatype", "nc"))
        self.v_text.setText(config.get("v_text", ""))
        self.v_fn = config.get("v_fn", [])
        self.vBG_datatype.setCurrentText(config.get("vBG_datatype", "nc"))
        self.vBG_text.setText(config.get("vBG_text", ""))
        self.vBG_fn = config.get("vBG_fn", [])
        self.is_mask.setChecked(config.get("is_mask",False))
        self.mask_text.setText(config.get("mask_text", ""))
        self.is_crop.setChecked(config.get("is_crop", False))
        self.wave_min.setText(config.get("wave_min", ""))
        self.wave_max.setText(config.get("wave_max", ""))
        self.is_correction.setChecked(config.get("is_correction", False))
        self.sample_name.setText(config.get("sample_name", ""))
        self.mass.setText(config.get("mass", ""))
        self.radius_text.setText(config.get("radius", ""))
        self.sam_height.setText(config.get("sam_height", ""))
        self.beam_height.setText(config.get("beam_height", ""))
        self.num_density_check.setChecked(config.get("num_density_check",False))
        self.num_density_text.setText(config.get("num_density_text",""))
        self.load_rebintable(config.get("rebin_info", []))
        self.is_offset.setChecked(config.get("is_offset", False))
        self.offset_text.setText(config.get("offset_text", ""))
        self.plot.setChecked(config.get("plot", False))
        self.evt_text.setText(config.get("evt_text", ""))
        self.exp_time.setText(config.get("exp_time", ""))
        self.tof_step.setText(config.get("tof_step", ""))
        self.set_scrollArea(config.get("slice_parameters", []))
        self.tabWidget.setCurrentIndex(config.get("which_tab", 0))
        self.proton_nor.setChecked(config.get("pc_check", True))
        self.monitor_nor.setChecked(config.get("monitor_check", False))
        self.samBG_scale.setText(config.get("samBG_scale", "1"))
        self.vBG_scale.setText(config.get("vBG_scale", "0.5"))
        self.toggle_button.setChecked(config.get("is_use", False))

    def check_evt_files(self):
        try:
            evt_num = self.check_evt_num()
        except:
            QMessageBox.warning(self, "warning", "The path of event data folder is not correct. Please Check!")
            return
        if evt_num == 0:
            QMessageBox.warning(self, "warning", "The number of each module's evt files is not same. Please Check!")
            return
        if evt_num == -1:
            QMessageBox.warning(self, "warning", "The number of each module's evt files is 0! Please Check!")
            return
        exist = self.check_pc_file()
        # print(exist)
        if not exist:
            QMessageBox.warning(self, "warning", "The pc_*.nxs is not exist in this folder. Please Check!")
            return
        else:
            self.read_exptime(self)

    def check_evt_num(self):
        pattern = os.path.join(self.evt_text.text(), "module*_evt_*.nxs")
        files = glob.glob(pattern)  # 使用glob模块匹配符合条件的文件
        module_file_count = defaultdict(int)  # 使用defaultdict来统计每个module名的文件数量
        for file in files:
            filename = os.path.basename(file)  # 提取文件名
            module_name = filename.split('_evt_')[0]  # 提取module名
            module_file_count[module_name] += 1  # 统计module名相同的文件数量
        # 检查所有module名的文件数量是否一致
        file_counts = list(module_file_count.values())
        if len(file_counts) == 0:
            return -1
        if all(count == file_counts[0] for count in file_counts):
            return file_counts[0]  # 返回文件数量
        else:
            return 0  # 返回0表示数量不一致

    def check_pc_file(self):
        pattern = os.path.join(self.evt_text.text(), "pc*.nxs")
        files = glob.glob(pattern)
        # print(files)
        if len(files) != 0:
            return True
        else:
            return False

    def read_exptime(self,parent):
        sam_path = parent.evt_text.text()
        try:
            flist = glob.glob(sam_path + "/pc*.nxs")
            pc_fn = flist[0]
            with h5py.File(pc_fn, "r") as hf:
                try:
                    start_sec = hf["/csns/logs/proton_charge/utc_tai"][0]
                    end_sec = hf["/csns/logs/proton_charge/utc_tai"][-1]
                except:
                    start_sec = hf["/csns/logs/utc_tai"][0]
                    end_sec = hf["/csns/logs/utc_tai"][-1]
            exp_sec = int(end_sec) - int(start_sec)
            exp_minute = exp_sec / 60
            exp_minute_formatted = "{:.2f}".format(exp_minute)
            parent.exp_time.setText(exp_minute_formatted)
        except:
            parent.exp_time.setText('None')

class LoadThreadManager(QObject):
    finished = pyqtSignal()  # 任务完成信号
    error = pyqtSignal(str)  # 任务错误信号
    data_ready = pyqtSignal(dict)  # 数据准备好信号
    progress = pyqtSignal(int)  # 进度信号
    progress_text = pyqtSignal(str)

    def __init__(self, mode, parent_widget):
        super().__init__()
        self.mode = mode
        self.parent_widget = parent_widget
        self.current_time = time.strftime("%Y-%m-%d-%H:%M:%S")
        self.is_running = True  # 标志位，控制线程是否继续运行

    def run(self):
        try:
            if self.mode == 'merge':
                sam_list = self.mergeLoad_and_focus("sample")
            else:
                sam_list = self.batchLoad_and_focus()

            if self.parent_widget.samBG_datatype.currentText() == "nc":
                samBG_list = self.load_focused_data(self.parent_widget.samBG_fn)
            elif self.parent_widget.samBG_datatype.currentText() == "dat":
                samBG_list = self.load_dat_data(self.parent_widget.samBG_fn)
            else:
                samBG_list = self.mergeLoad_and_focus("samBG")

            if self.parent_widget.v_datatype.currentText() == "nc":
                v_list = self.load_focused_data(self.parent_widget.v_fn)
            else:
                v_list = self.load_dat_data(self.parent_widget.v_fn)

            if self.parent_widget.vBG_datatype.currentText() == "nc":
                vBG_list = self.load_focused_data(self.parent_widget.vBG_fn)
            else:
                vBG_list = self.load_dat_data(self.parent_widget.vBG_fn)

            if sam_list:
                self.d_rebin(sam_list)
                self.normalization(sam_list)
                if samBG_list:
                    self.d_rebin(samBG_list)
                    if self.parent_widget.samBG_datatype.currentText() != "dat":
                        self.normalization(samBG_list)
                    self.subtraction(sam_list, samBG_list, "samBG")

                if v_list:
                    self.d_rebin(v_list)
                    if self.parent_widget.v_datatype.currentText() != "dat":
                        self.normalization(v_list)
                    if vBG_list:
                        self.d_rebin(vBG_list)
                        if self.parent_widget.vBG_datatype.currentText() != "dat":
                            self.normalization(vBG_list)
                        self.subtraction(v_list, vBG_list, "vBG")
                    self.calibration(sam_list, v_list)

            self.finished.emit()  # 任务完成，发送信号
        except Exception as e:
            traceback.print_exc()  # 打印异常的堆栈跟踪
            self.error.emit(str(e))  # 任务出错，发送信号
            self.finished.emit()  # 任务完成，发送信号

    def calibration(self, sam_list,van_list):
        for sam in sam_list:
            for van in van_list:
                if van["detector"] == sam["detector"]:
                    sam["detector_focused"] = calculate_neutron_data('divide',sam["detector_focused"],van["detector_focused"])
                    sam["record"]["division"] = van['name']
                    if "subtraction_self" in van['record']:
                        sam["record"]["subtraction_v"] = van['record']["subtraction_self"]
                        sam["record"]["subtraction_v_scale"] = van['record']["subtraction_scale"]
                    if "correction_info" in van.keys():
                        sam["v_correction"] = van["correction_info"]

    def subtraction(self, sam_list, bkg_list, bkgtype):
        if sam_list and bkg_list:
            for sam in sam_list:
                for bkg in bkg_list:
                    if bkg["detector"] == sam["detector"]:
                        backup = copy.deepcopy(bkg["detector_focused"])
                        if bkgtype == "samBG":
                            scale = float(self.parent_widget.samBG_scale.text())
                        else:
                            scale = float(self.parent_widget.vBG_scale.text())
                        bkg["detector_focused"]["histogram"].values *= scale
                        bkg["detector_focused"]["error"].values *= scale
                        sam["detector_focused"] = calculate_neutron_data(
                            'subtract',
                            sam["detector_focused"],
                            bkg["detector_focused"]
                        )
                        bkg["detector_focused"] = backup
                        sam["record"]["subtraction_self"] = bkg['name']
                        sam["record"]["subtraction_scale"] = scale

    def normalization(self, data_list):
        if self.parent_widget.proton_nor.isChecked():
            for data in data_list:
                proton_charge = data['detector_focused']["proton_charge"].values
                proton_charge /= self.parent_widget.parent.config['base']['pc_factor']
                data['detector_focused']["histogram"].values /= proton_charge
                data['detector_focused']["error"].values /= proton_charge
                data["record"]["normalization"] = "protonCharge"
        elif self.parent_widget.monitor_nor.isChecked():
            for data in data_list:
                monitor_counts = data['detector_focused']["monitor_counts"].values
                data['detector_focused']["histogram"].values /= monitor_counts
                data['detector_focused']["error"].values /= monitor_counts
                data["record"]["normalization"] = "monitorCounts"


    def d_rebin(self, data_list):
        drebin, rebin_mode = self.parent_widget.extract_drebin_from_table()
        for data in data_list:
            if rebin_mode[data['detector']] == "deltaX_X":
                dvalue = generate_x(float(drebin[data['detector']][0]), float(drebin[data['detector']][1]),
                                    float(drebin[data['detector']][2]), rebin_mode[data['detector']])
            else:
                dvalue = generate_x(float(drebin[data['detector']][0]), float(drebin[data['detector']][1]),
                                    int(drebin[data['detector']][2]), rebin_mode[data['detector']])
            data['detector_focused'] = rebin_neutron_data(data['detector_focused'], dvalue)
            data["record"]["d_rebin"] = drebin[data['detector']]

    def load_focused_data(self, nc_fn):
        try:
            datalist = []
            for fn in nc_fn:
                name,_ = os.path.splitext(os.path.basename(fn))
                data_dict = {'name': name}
                dataset = read_dataset(fn)
                dataset = upgrade_positions_to_8cols(dataset)  # 如果是老版本数据，positions只有3列，扩展成8列以和新版本rongzai兼容
                data_dict['runno'] = dataset.runno
                data_dict['detector'] = dataset.name
                data_dict['detector_focused'] = dataset

                record_info = json.loads(dataset.attrs["record"])
                data_dict["record"] = record_info

                if "carpenterCorrection" in data_dict["record"].keys():
                    data_dict["correction_info"] = data_dict["record"]["carpenterCorrection"]

                if "time_slice" in dataset.attrs:
                    data_dict["time_slice"] = dataset.attrs["time_slice"]
                self.data_ready.emit(data_dict)
                datalist.append(data_dict)
            return datalist
        except Exception as e:
            print(f'Reason: {e}')
            traceback.print_exc()  # 打印异常的堆栈跟踪

    def load_dat_data(self, dat_fn):
        try:
            datalist = []
            for fn in dat_fn:
                name,_ = os.path.splitext(os.path.basename(fn))
                data_dict = {'name': name}
                data_dict['runno'] = self.extract_info_from_datfn(fn,"runno")
                data_dict['detector'] = self.extract_info_from_datfn(fn,"detector")
                x, y, e = np.loadtxt(fn, unpack=True)
                dataset = create_dataset(y, e, x, np.array([1]), np.array([0, 0, 0, 0, 0, 0, 0, 0]), 0.0, 0.0, data_dict['detector'],
                                         unit="dspacing")
                data_dict['detector_focused'] = dataset

                record_info = {}
                data_dict["record"] = record_info

                if "carpenterCorrection" in data_dict["record"].keys():
                    data_dict["correction_info"] = data_dict["record"]["carpenterCorrection"]

                if "time_slice" in dataset.attrs:
                    data_dict["time_slice"] = dataset.attrs["time_slice"]
                self.data_ready.emit(data_dict)
                datalist.append(data_dict)
            return datalist
        except Exception as e:
            print(f'Reason: {e}')
            traceback.print_exc()  # 打印异常的堆栈跟踪

    def process_detector(self, run_fn, runno, detector, index, total_tasks):
        data_dict = {}
        data_dict["runno"] = runno
        data_dict['detector'] = detector
        data_dict['record'] = {}
        group, modules = get_all_from_detector(detector, self.parent_widget.parent.config['base']['group_info'],
                                               self.parent_widget.parent.config['base']['bank_info'])
        dvalue = generate_x(self.parent_widget.parent.config['base']['d_rebin'][group][0],
                            self.parent_widget.parent.config['base']['d_rebin'][group][1],
                            self.parent_widget.parent.config['base']['d_rebin'][group][2], self.parent_widget.parent.config['base']['d_rebin']['mode'])
        for i, module in enumerate(modules):
            if not self.is_running:  # 检查标志位
                return False
            self.progress_text.emit(f"Start Loading and focusing {detector}, {module}")
            pidInfo_fn = os.path.join(self.parent_widget.instru_text.text(), module + ".txt")
            if not os.path.exists(pidInfo_fn):
                self.error.emit(f"Please check the instru file of {module}!")
                return False
            try:
                neutron_data = load_histogram_data(run_fn, pidInfo_fn, module,
                                                 self.parent_widget.parent.config['base']["first_flight_distance"],
                                                 float(self.parent_widget.t0_text.text()))
            except:
                self.error.emit(f"The sample data failed loading, please check the loaded sample file!")
                return False
            if self.parent_widget.is_mask.isChecked():
                mask_file = self.parent_widget.mask_text.text() + "/" + module + "_mask.txt"
                cal_dict = read_mask(mask_file)
                neutron_data = mask_neutron_data(neutron_data, cal_dict["mask_list"])
                data_dict["record"]["mask"] = self.parent_widget.instru_text.text()
            if self.parent_widget.is_crop.isChecked():
                neutron_data = convert_unit_elastic(neutron_data, "wavelength")
                neutron_data = crop_neutron_data(neutron_data, float(self.parent_widget.wave_min.text()),
                                                 float(self.parent_widget.wave_max.text()))
                neutron_data = convert_unit_elastic(neutron_data, "tof")
                data_dict["record"][
                    "crop"] = f"{self.parent_widget.wave_min.text()}_{self.parent_widget.wave_max.text()}"
            if self.parent_widget.is_correction.isChecked():
                correction_info = self.parent_widget.get_correction_info()
                if self.parent_widget.num_density_check.isChecked():
                    correction_info["density_num"] = float(self.parent_widget.num_density_text.text())
                    cal_info = get_sample_properties(correction_info)
                else:
                    cal_info = get_sample_properties(correction_info)
                    correction_info["density_num"] = cal_info["density_num"]
                neutron_data = convert_unit_elastic(neutron_data,"wavelength")
                neutron_data = correct_carpenter(neutron_data, cal_info)
                neutron_data = convert_unit_elastic(neutron_data, "tof")
                data_dict["record"]["carpenterCorrection"] = correction_info
                data_dict["correction_info"] = data_dict["record"]["carpenterCorrection"]
            if self.parent_widget.is_offset.isChecked():
                cal_fn = self.parent_widget.offset_text.text() + "/" + module + "_offset.cal"
                try:
                    cal_dict = read_cal(cal_fn)
                except:
                    self.error.emit(f"Please check the offset file of {module}!")
                    return False
                data_d = correct_tof_to_d(neutron_data, cal_dict)
                data_d = mask_neutron_data(data_d, cal_dict["mask_list"])
                data_d_focused = focus_neutron_data(data_d,dvalue)
                data_dict["record"]["offset"] = self.parent_widget.offset_text.text()
            else:
                neutron_data = convert_unit_elastic(neutron_data, "dspacing")
                data_d_focused = focus_neutron_data(neutron_data,dvalue)
            if i == 0:
                data_dict['detector_focused'] = data_d_focused
            else:
                data_dict["detector_focused"] = calculate_neutron_data("add", data_dict["detector_focused"],
                                                                       data_d_focused)
        try:
            self.progress_text.emit(
                f"Start Loading and focusing {detector}, {self.parent_widget.parent.config['base']['normalization_monitor']}")
            pidInfo_fn = self.parent_widget.instru_text.text() + "/" + self.parent_widget.parent.config['base'][
                "normalization_monitor"] + ".txt"
            monitor_data = load_histogram_data(run_fn, pidInfo_fn,
                                             self.parent_widget.parent.config['base']["normalization_monitor"],
                                             self.parent_widget.parent.config['base']["first_flight_distance"],
                                             float(self.parent_widget.t0_text.text()))
            if self.parent_widget.is_crop.isChecked():
                monitor_data = convert_unit_elastic(monitor_data, "wavelength")
                monitor_data = crop_neutron_data(monitor_data, float(self.parent_widget.wave_min.text()),
                                                 float(self.parent_widget.wave_max.text()))
                monitor_data = focus_neutron_data(monitor_data,None)
            data_dict["monitor"] = monitor_data.copy()
            mc = monitor_data["histogram"].values.sum()
            data_dict["monitor_counts"] = mc
        except:
            pass
        self.get_name_of_data_dict(data_dict)
        self.data_ready.emit(data_dict)
        # self.parent.data_list.append(data_dict)
        # self.append_data([data_dict])
        # 计算并发射进度
        progress = int(((index + 1) / total_tasks) * 100)
        self.progress.emit(progress)
        return data_dict

    def mergeLoad_and_focus(self, datatype):
        detectors_list = self.extract_detectors_from_lineedit(self.parent_widget.detector_text)
        total_tasks = len(detectors_list)
        task_index = 0
        datalist = []

        if datatype == "sample":
            runno = self.extract_runs_from_lineedit(self.parent_widget.sample_text, mode=self.mode)
        else:
            runno = self.extract_runs_from_lineedit(self.parent_widget.samBG_text, mode=self.mode)

        for detector in detectors_list:
            if not self.is_running:  # 检查标志位
                return False

            if datatype == "sample":
                data_dict = self.process_detector(self.parent_widget.sam_fn, runno, detector, task_index, total_tasks)
            else:
                data_dict = self.process_detector(self.parent_widget.samBG_fn, runno, detector, task_index, total_tasks)

            if not data_dict:
                return False
            datalist.append(data_dict)
            task_index += 1
        return datalist


    # 下面这个方法只针对样品
    def batchLoad_and_focus(self):
        runno_list = self.extract_runs_from_lineedit(self.parent_widget.sample_text, mode=self.mode)
        detectors_list = self.extract_detectors_from_lineedit(self.parent_widget.detector_text)
        total_tasks = len(runno_list) * len(detectors_list)
        task_index = 0
        datalist = []
        for runno in runno_list:
            extracted_runfn = self.extract_runfn_from_runno(self.parent_widget.sam_fn, runno)
            for detector in detectors_list:
                if not self.is_running:  # 检查标志位
                    return False
                data_dict = self.process_detector(extracted_runfn, runno, detector, task_index, total_tasks)
                if not data_dict:
                    return False
                datalist.append(data_dict)
                task_index += 1
        return datalist

    def get_unrepeated_modules_from_dectectors(self, detectors_list):
        modulesList = set()
        for detector in detectors_list:
            group, modules = get_all_from_detector(detector,
                                                   self.parent_widget.parent.config['base']['group_info'],
                                                   self.parent_widget.parent.config['base']['bank_info'])
            modulesList.update(modules)
        return list(modulesList)

    def get_name_of_data_dict(self, data_dict):
        name = data_dict["runno"]
        if "time_slice" in data_dict.keys():
            name = f"{name}_slicedTime({data_dict['time_slice']})"
        name = f"{name}_{data_dict['detector']}"
        for key in data_dict["record"].keys():
            name = f"{name}_{key}"
        name = f"{name}_time({self.current_time})"
        data_dict["name"] = name

    def focus_sliced_data(self):
        try:
            detectors_list = self.extract_detectors_from_lineedit(self.parent_widget.detector_text)
            modules_list = self.get_unrepeated_modules_from_dectectors(detectors_list)
            self.slice_worker = TimeSlice(modules_list,self)
            self.slice_worker.setup_timeslice()
            time_list = self.slice_worker.generate_slice_time_list()
            total_tasks = len(self.slice_worker.moduleList) + len(detectors_list) * len(time_list)
            task_index = 0
            datalist = []
            for module in self.slice_worker.moduleList:
                if not self.is_running:  # 检查标志位
                    return False
                self.progress_text.emit(f"Start loading and slicing {module}")
                print(f"start slice {module}")
                self.slice_worker.get_slice_module(module)
                # 计算并发射进度
                task_index += 1
                progress = int(task_index / total_tasks * 100)
                self.progress.emit(progress)
            sliced_pc = self.slice_worker.get_slice_pc()

            for i, data in enumerate(self.slice_worker.focused_data.values()):
                if not self.is_running:  # 检查标志位
                    return False
                self.progress_text.emit(f"Start calculating the sliced data {i+1}")
                for detector in detectors_list:
                    if not self.is_running:  # 检查标志位
                        return False
                    data_dict = {}
                    data_dict["runno"] = self.slice_worker.conf['sample_run'][-1]
                    data_dict["time_slice"] = f"{round(time_list[i][0],2)}-{round(time_list[i][1],2)}"
                    data_dict["detector"] = detector
                    data_dict["record"] = {}
                    data_dict["record"].update(self.slice_worker.record)
                    self.get_name_of_data_dict(data_dict)
                    group, modules = get_all_from_detector(detector,
                                                           self.parent_widget.parent.config['base']['group_info'],
                                                           self.parent_widget.parent.config['base']['bank_info'])
                    dvalue = generate_x(self.parent_widget.parent.config['base']['d_rebin'][group][0],
                                        self.parent_widget.parent.config['base']['d_rebin'][group][1],
                                        self.parent_widget.parent.config['base']['d_rebin'][group][2], 'uniform')
                    for j, module in enumerate(modules):
                        data_d_focused = rebin_neutron_data(data[module], dvalue)
                        if j == 0:
                            data_dict['detector_focused'] = data_d_focused
                        else:
                            data_dict["detector_focused"] = calculate_neutron_data("add", data_dict["detector_focused"],
                                                                                   data_d_focused)
                    data_dict["detector_focused"]["proton_charge"] = sliced_pc[i]
                    try:
                        data_dict["monitor_counts"] = data[self.parent_widget.parent.config['base']['normalization_monitor']]
                    except:
                        pass
                    self.data_ready.emit(data_dict)
                    datalist.append(data_dict)
                    # 计算并发射进度
                    task_index += 1
                    progress = int(task_index / total_tasks * 100)
                    self.progress.emit(progress)
            return datalist


        except Exception as e:
            import traceback
            traceback.print_exc()  # 打印异常的堆栈跟踪
            self.error.emit(str(e))  # 任务出错，发送信号


    def run_slice(self):
        try:
            sam_list = self.focus_sliced_data()

            if self.parent_widget.samBG_datatype.currentText() == "nc":
                samBG_list = self.load_focused_data(self.parent_widget.samBG_fn)
            elif self.parent_widget.samBG_datatype.currentText() == "dat":
                samBG_list = self.load_dat_data(self.parent_widget.samBG_fn)
            else:
                samBG_list = self.mergeLoad_and_focus("samBG")

            if self.parent_widget.v_datatype.currentText() == "nc":
                v_list = self.load_focused_data(self.parent_widget.v_fn)
            else:
                v_list = self.load_dat_data(self.parent_widget.v_fn)

            if self.parent_widget.vBG_datatype.currentText() == "nc":
                vBG_list = self.load_focused_data(self.parent_widget.vBG_fn)
            else:
                vBG_list = self.load_dat_data(self.parent_widget.vBG_fn)

            if sam_list:
                self.d_rebin(sam_list)
                self.normalization(sam_list)
                if samBG_list:
                    self.d_rebin(samBG_list)
                    if self.parent_widget.samBG_datatype.currentText() != "dat":
                        self.normalization(samBG_list)
                    self.subtraction(sam_list, samBG_list, "samBG")

                if v_list:
                    self.d_rebin(v_list)
                    if self.parent_widget.v_datatype.currentText() != "dat":
                        self.normalization(v_list)
                    if vBG_list:
                        self.d_rebin(vBG_list)
                        if self.parent_widget.vBG_datatype.currentText() != "dat":
                            self.normalization(vBG_list)
                        self.subtraction(v_list, vBG_list, "vBG")
                    self.calibration(sam_list, v_list)

            self.finished.emit()  # 任务完成，发送信号
        except Exception as e:
            traceback.print_exc()  # 打印异常的堆栈跟踪
            self.error.emit(str(e))  # 任务出错，发送信号
            self.finished.emit()  # 任务完成，发送信号

    def extract_runs_from_lineedit(self,lineEdit,mode='merge'):
        # 从 lineEdit 中提取 selected_files
        selected_files = lineEdit.text().split('; ')

        # 提取 RUN*******
        run_pattern = re.compile(r'RUN\d+')  # 匹配 RUN 后跟数字的部分
        run_list = [run_pattern.search(file).group() for file in selected_files if run_pattern.search(file)]
        if mode == 'merge':
            # 用 _ 间隔组成字符串
            run_string = '_'.join(run_list)
            return run_string
        else:
            return run_list

    def extract_info_from_datfn(self,datfn,info):
        if info == "runno":
            # 提取 RUN*******
            run_pattern = re.compile(r'RUN\d+')  # 匹配 RUN 后跟数字的部分
            runs = run_pattern.findall(datfn) # 返回列表，如 ['RUN12', 'RUN34']
            # 用 _ 间隔组成字符串
            run_string = '_'.join(runs)
            return run_string
        if info == "detector":
            group_pattern = re.compile(r'(?<![A-Za-z])group[A-Za-z]+(?![A-Za-z])', re.IGNORECASE)
            bank_pattern = re.compile(r'(?<=)bank[A-Za-z0-9]+(?=)', re.IGNORECASE)
            module_pattern = re.compile(r'(?<=)module[A-Za-z0-9]+(?=)', re.IGNORECASE)
            groups = group_pattern.findall(datfn)
            banks = bank_pattern.findall(datfn)
            modules = module_pattern.findall(datfn)
            if groups:
                group_string = '_'.join(groups)
                return group_string
            if banks:
                bank_string = '_'.join(banks)
                return bank_string
            if modules:
                module_string = '_'.join(modules)
                return module_string
        return ""



    def extract_runs_from_datfn(self,datfn):
        # 提取 RUN*******
        run_pattern = re.compile(r'RUN\d+')  # 匹配 RUN 后跟数字的部分
        runs = run_pattern.findall(datfn) # 返回列表，如 ['RUN12', 'RUN34']
        # 用 _ 间隔组成字符串
        run_string = '_'.join(runs)
        return run_string

    def extract_detectors_from_lineedit(self,lineEdit):
        detector_list = lineEdit.text().split('; ')
        return detector_list

    def is_data_exist(self,data_list,runno,detector):
        for data in data_list:
            if runno == data["runno"] and detector == data["detector"]:
                return True
        return False

    def extract_runfn_from_runno(self, run_fn, runno):
        # 使用列表推导式从 run_fn 中提取包含 runno 的元素
        filtered_list = [fn for fn in run_fn if runno in fn]
        return filtered_list

    def stop(self):
        """停止线程"""
        self.is_running = False
        # self.progress_text.emit("Start stopping,please wait")
        # self.finished.emit()  # 任务完成，发送信号

class TimeSlice:
    def __init__(self, modules, parent):
        self.parent = parent
        self.conf = self.parent.parent_widget.parent.config["base"]
        self.conf["data_path"] = os.path.dirname(self.parent.parent_widget.evt_text.text())
        self.conf["sample_run"] = self.parent.extract_runs_from_lineedit(self.parent.parent_widget.evt_text,mode="batch")
        self.conf["slice_part"] = {"evt_file_num": self.parent.parent_widget.check_evt_num(),
                                    "tof_step": float(self.parent.parent_widget.tof_step.text()),
                                    "start_pulseID":0,
                                    "slice_info":self.convert_to_num(self.parent.parent_widget.operate_slicepara.extract_slice_info())}
        self.conf["param_path"] = self.parent.parent_widget.instru_text.text()
        module_list = set()
        module_list.update(modules)
        # 使用 glob 检查是否存在匹配的文件
        pattern = os.path.join(self.conf["data_path"], f"{self.conf['normalization_monitor']}_evt_*.nxs")
        if glob.glob(pattern):
            module_list.add(self.conf['normalization_monitor'])
        self.moduleList = list(module_list)

        self.save_histogram = False
        self.instrument = {}
        self.focused_data = {}
        self.record = {}
        self.sliced_proton_charge = []

    def setup_timeslice(self):
        self.data_path = os.path.join(self.conf["data_path"], self.conf["sample_run"][0])
        self.pulse_time_ranges = generate_slice_pulseID_list(self.conf)
        self.tot_num = len(self.pulse_time_ranges)
        self.slice_data = {}
        check_dir(os.path.join(self.data_path, "tmp"))

    def get_slice_module(self, module):
        get_slice_module(module, self.conf, self.pulse_time_ranges, self.save_chunk)

    def get_slice_pc(self):
        return get_slice_pc(self.conf,self.pulse_time_ranges)

    def convert_to_num(self,slice_info):
        new_slice_info = []
        for data in slice_info:
            new_data = [float(data[0]),float(data[1]),int(data[2])]
            new_slice_info.append(new_data)
        return new_slice_info

    def organize_pixel_id(self, moduleName):
        xpixels = self.conf["pixel_info"][moduleName]["xpixels"]
        ypixels = self.conf["pixel_info"][moduleName]["ypixels"]
        stepbyrow = self.conf["pixel_info"][moduleName]["stepbyrow"]
        start_id = self.conf["pixel_info"][moduleName]["start"]

        # 生成二维列表
        if stepbyrow == "y":
            pixelsid = np.arange(start_id, start_id + xpixels * ypixels).reshape(xpixels, ypixels)
        elif stepbyrow == "x":
            pixelsid = np.arange(start_id, start_id + xpixels * ypixels).reshape(ypixels, xpixels).T

        return pixelsid.tolist()

    def evt2histogram(self, pids, tofs, tof_step, txt_file_path):
        pixel_ids, _ = read_instrument_info(txt_file_path)
        pid_nums = pixel_ids.size
        tof_min = 0
        tof_max = 40000
        tof_nums = int((tof_max - tof_min) / tof_step)
        histogram = Hist2D(pid_nums, tof_nums, [[-0.5 + pixel_ids[0], pixel_ids[-1] + 0.5],
                                                [tof_min, tof_max]])
        histogram.fill(pids, tofs)
        return histogram

    def generate_slice_time_list(self):
        result = []
        t0 = self.conf["slice_part"]['start_pulseID']
        if t0 == 0:
            t0 = self.get_start_pulseID_from_pc()
            print(f"find t0 from pc: {t0}")
        slice_info = self.conf["slice_part"]["slice_info"]
        for start_left, end_right, num in slice_info:
            step = (end_right - start_left) / num
            start = start_left
            for _ in range(num):
                end = start + step
                result.append([start, end])
                start = end
        return result

    def get_start_pulseID_from_pc(self):
        flist = glob.glob(self.data_path + "/pc*.nxs")
        # print(flist)
        pc_fn = flist[0]
        with h5py.File(pc_fn, "r") as hf:
            try:
                return hf["/csns/logs/proton_charge/pulse_time"][0]
            except:
                return hf["/csns/logs/pulse_time"][0]

    def save_chunk(self, buffer, chunk_counter, moduleName, config):
        if self.save_histogram is True:
            txt_fn = self.conf["param_path"] + "/" + moduleName + ".txt"
            histogram = self.evt2histogram(buffer['event_pixel_id'],buffer["event_time_of_flight"],self.conf["slice_part"]["tof_step"], txt_fn)
            if str(chunk_counter) not in self.instrument:
                self.instrument[str(chunk_counter)] = {}
            self.instrument[str(chunk_counter)][moduleName] = {}
            self.instrument[str(chunk_counter)][moduleName]["histogram_data"] = histogram.hist
            self.instrument[str(chunk_counter)][moduleName]["pixel_id"] = self.organize_pixel_id(moduleName)
            self.instrument[str(chunk_counter)][moduleName]["time_of_flight"] = histogram.yedge
        else:
            if str(chunk_counter) not in self.focused_data:
                self.focused_data[str(chunk_counter)] = {}
            if moduleName[:7] == "monitor":
                txt_fn = os.path.join(self.conf["param_path"], self.conf['base']["normalization_monitor"] + ".txt")
                if not os.path.exists(txt_fn):
                    self.parent.error.emit(f"Please check the instru file of {self.conf['base']['normalization_monitor']}!")
                    self.parent.finished.emit()  # 任务完成，发送信号
                txt_fn = self.conf["param_path"] + "/" + self.conf['base']["normalization_monitor"] + ".txt"
                monitor_data = load_event_data(buffer['event_pixel_id'], buffer["event_time_of_flight"],
                                                 self.conf["slice_part"]["tof_step"], 1, txt_fn, moduleName,
                                                 self.conf["first_flight_distance"], x_offset=0)
                if self.parent.parent_widget.is_crop.isChecked():
                    monitor_data = convert_unit_elastic(monitor_data, "wavelength")
                    monitor_data = crop_neutron_data(monitor_data,
                                                     float(self.parent.parent_widget.wave_min.text()),
                                                     float(self.parent.parent_widget.wave_max.text()))
                    monitor_data = focus_neutron_data(monitor_data)
                mc = monitor_data["histogram"].values.sum()
                self.focused_data[str(chunk_counter)][moduleName] = mc
            else:
                txt_fn = os.path.join(self.conf["param_path"], moduleName + ".txt")
                if not os.path.exists(txt_fn):
                    self.parent.error.emit(
                        f"Please check the instru file of {moduleName}!")
                    self.parent.finished.emit()  # 任务完成，发送信号
                neutron_data = load_event_data(buffer['event_pixel_id'], buffer["event_time_of_flight"],
                                                     self.conf["slice_part"]["tof_step"], 1, txt_fn, moduleName,
                                                     self.conf["first_flight_distance"], x_offset=0)
                if self.parent.parent_widget.is_mask.isChecked():
                    mask_file = self.parent.parent_widget.mask_text.text() + "/" + moduleName + "_mask.txt"
                    cal_dict = read_mask(mask_file)
                    neutron_data = mask_neutron_data(neutron_data, cal_dict["mask_list"])
                    self.record["mask"] = self.parent.parent_widget.mask_text.text()
                if self.parent.parent_widget.is_crop.isChecked():
                    neutron_data = convert_unit_elastic(neutron_data, "wavelength")
                    neutron_data = crop_neutron_data(neutron_data, float(self.parent.parent_widget.wave_min.text()),
                                                     float(self.parent.parent_widget.wave_max.text()))
                    neutron_data = convert_unit_elastic(neutron_data, "tof")
                    self.record["crop"] = f"{self.parent.parent_widget.wave_min.text()}_{self.parent.parent_widget.wave_max.text()}"
                if self.parent.parent_widget.is_correction.isChecked():
                    correction_info = self.parent.parent_widget.get_correction_info()
                    # 下面这一步这么写，是为了确保correction_info里面必须有"density_num"这一项，这用于后面pdf的pho0的计算
                    if self.parent.parent_widget.num_density_check.isChecked():
                        correction_info["density_num"] = float(self.parent.parent_widget.num_density_text.text())
                        cal_info = get_sample_properties(correction_info)
                    else:
                        cal_info = get_sample_properties(correction_info)
                        correction_info["density_num"] = cal_info["density_num"]
                    neutron_data = convert_unit_elastic(neutron_data, "wavelength")
                    neutron_data = correct_carpenter(neutron_data, cal_info)
                    neutron_data = convert_unit_elastic(neutron_data, "tof")
                    self.record["carpenterCorrection"] = correction_info
                if self.parent.parent_widget.is_offset.isChecked():
                    cal_fn = self.parent.parent_widget.offset_text.text() + "/" + moduleName + "_offset.cal"
                    try:
                        cal_dict = read_cal(cal_fn)
                    except:
                        self.parent.error.emit(f"Please check the offset file of {moduleName}!")
                        self.parent.finished.emit()  # 任务完成，发送信号
                    data_d = correct_tof_to_d(neutron_data, cal_dict)
                    data_d = mask_neutron_data(data_d, cal_dict["mask_list"])
                    data_d_focused = focus_neutron_data(data_d,None)
                    self.record["offset"] = self.parent.parent_widget.offset_text.text()
                else:
                    neutron_data = convert_unit_elastic(neutron_data, "dspacing")
                    data_d_focused = focus_neutron_data(neutron_data,None)

                if str(chunk_counter) not in self.focused_data:
                    self.focused_data[str(chunk_counter)] = {}
                self.focused_data[str(chunk_counter)][moduleName]=data_d_focused

    def save_histogram_nxs(self):
        for key, modules_data in self.instrument.items():
            file_path = f"{self.conf['save_path']}/detector_{key}.nxs"  # 完整路径
            os.makedirs(self.conf['save_path'], exist_ok=True)
            with h5py.File(file_path, "w") as f:
                csns = f.create_group("csns")  # 创建路径 csns
                csns.create_dataset("beamline", data=self.conf["beamline"])
                csns.create_dataset("end_time_tai", data=self.sliced_proton_charge[int(key)][1][-1])
                # csns.create_dataset("end_time_utc", data=)
                # event_data = f.create_group("csns/event_data")
                # histogram_data = f.create_group("csns/histogram_data")
                instrument = csns.create_group("instrument")
                for moduleName, data in modules_data.items():
                    # print(moduleName)
                    module_data = instrument.create_group(moduleName)
                    module_data.create_dataset("histogram_data",data=data["histogram_data"])
                    module_data.create_dataset("pixel_id", data=data["pixel_id"])
                    module_data.create_dataset("time_of_flight", data=data["time_of_flight"])

                logs = csns.create_group("logs")
                logs.create_group("chopper")
                proton_charge = logs.create_group("proton_charge")
                proton_charge.create_dataset("pulse_time", data=self.sliced_proton_charge[int(key)][0])
                proton_charge.create_dataset("utc_tai", data=self.sliced_proton_charge[int(key)][1])
                proton_charge.create_dataset("value", data=self.sliced_proton_charge[int(key)][2])
                csns.create_group("process")
                csns.create_dataset("proton_charge",data=sum(self.sliced_proton_charge[int(key)][2]))
                csns.create_dataset("runno", data=self.conf["sample_run"][0])
                csns.create_dataset("start_time_tai", data=self.sliced_proton_charge[int(key)][1][0])
                # csns.create_dataset("start_time_utc", data=)
                csns.create_group("user")

    def slice_proton_charge(self):
        pulse_time, utc_tai, value = self.get_proton_charge()
        # 遍历每一行的范围
        for start, end in self.pulse_time_ranges:
            # 使用布尔索引筛选符合条件的 utc_tai
            mask = (pulse_time >= start) & (pulse_time < end)

            # 根据 mask 切割 pulse_time, utc_tai, value
            sliced_pulse_time = pulse_time[mask]
            sliced_utc_tai = utc_tai[mask]
            sliced_value = value[mask]

            # 将结果添加到 sliced_data
            self.sliced_proton_charge.append((sliced_pulse_time, sliced_utc_tai, sliced_value))

    def get_proton_charge(self):
        flist = glob.glob(self.data_path + "/pc*.nxs")
        pc_fn = flist[0]
        with h5py.File(pc_fn, "r") as hf:
            try:
                return hf["/csns/logs/proton_charge/pulse_time"][:], hf["/csns/logs/proton_charge/utc_tai"][:], hf["/csns/logs/proton_charge/value"][:]
            except:
                return hf["/csns/logs/pulse_time"][:],hf["/csns/logs/utc_tai"][:],hf["/csns/logs/value"][:]

class ProgressDialog(QDialog):
    def __init__(self, thread, parent_widget, parent=None):
        super().__init__(parent)
        self.thread = thread
        self.parent_widget = parent_widget

        # 设置窗口标题
        self.setWindowTitle("Data Loading")
        self.resize(250, 100)  # Width 300, Height 100 # 设置窗口初始大小

        # 创建布局
        layout = QVBoxLayout()

        # 添加信息标签
        self.info_label = QLabel("progress info:starting...", self)
        self.info_label.setFont(self.customized_font())
        layout.addWidget(self.info_label)
        layout.addWidget(self.info_label)

        # 添加进度条
        self.progress_bar = QProgressBar(self)
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        layout.addWidget(self.progress_bar)

        # 设置布局
        self.setLayout(layout)

    def customized_font(self):
        font = QFont()
        if QFont("Times New Roman").exactMatch():
            font.setFamily("Times New Roman")
        else:
            font.setFamily(font.defaultFamily())  # 使用默认字体
        font.setPointSize(14)
        return font


    def update_info(self, info):
        """更新信息标签的文本"""
        self.info_label.setText(f"progress info:{info}")

    def closeEvent(self, event):
        """重写关闭事件，确保线程停止"""
        # 更新信息标签
        self.update_info("Start stopping, please wait...")

        # 将进度条的状态设置为不确定
        self.progress_bar.setRange(0, 0)  # 设置为不确定，显示一个动画条

        self.parent_widget.worker.stop()  # 请求停止线程

        if self.thread.isRunning():
            self.thread.quit()  # 请求线程退出
            # 可能需要在等待期间处理事件，以防止界面卡住
            while self.thread.isRunning():
                QApplication.processEvents()  # 处理事件循环，防止界面无响应
                self.thread.wait(100)  # 短暂等待，避免长时间阻塞

        self.progress_bar.setRange(0, 100)  # 复位进度条，使其不再显示动画
        event.accept()


class operate_slicepara():
    def __init__(self, parent):
        self.parent = parent
        self.rows = []  # 用于存储行控件的引用
        # 确保 scrollAreaWidgetContents 有一个 QVBoxLayout
        if not self.parent.scrollAreaWidgetContents.layout():
            self.parent.scrollAreaWidgetContents.setLayout(QVBoxLayout())

        # 添加拉伸项，以确保控件靠近顶部
        self.parent.scrollAreaWidgetContents.layout().addStretch()

        self.add_row() # 初始化时添加一行

    def add_row(self):
        # 创建一个新的行布局
        row_layout = QHBoxLayout()

        # 起始值输入框
        start_value = QLineEdit()
        start_value.setPlaceholderText("Start Time (min)")
        start_value.setValidator(QDoubleValidator())  # 只允许输入浮点数

        # 结束值输入框
        end_value = QLineEdit()
        end_value.setPlaceholderText("End Time (min)")
        start_value.setValidator(QDoubleValidator())  # 只允许输入浮点数

        # 切割数量输入框
        num_splits = QLineEdit()
        num_splits.setPlaceholderText("Slice Number")
        num_splits.setValidator(QIntValidator())  # 只允许输入整数

        # 为每个控件设置唯一的名字
        row_index = len(self.rows)
        start_value.setObjectName(f"slice_start_{row_index}")
        end_value.setObjectName(f"slice_end_{row_index}")
        num_splits.setObjectName(f"slice_number_{row_index}")

        # 将输入框添加到行布局中
        row_layout.addWidget(start_value)
        row_layout.addWidget(end_value)
        row_layout.addWidget(num_splits)

        # 获取布局，并在拉伸项之前插入新行
        layout = self.parent.scrollAreaWidgetContents.layout()
        layout.insertLayout(layout.count() - 1, row_layout)  # 插入到倒数第二个位置

        # 将控件引用存储在列表中
        self.rows.append({
            'start_value': start_value,
            'end_value': end_value,
            'num_splits': num_splits,
            'layout': row_layout
        })

    def remove_row(self):
        # 移除参数设置区域中的最后一行
        layout = self.parent.scrollAreaWidgetContents.layout()
        if layout.count() > 1:  # 至少保留拉伸项
            last_row = layout.takeAt(layout.count() - 2)  # 移除倒数第二个项
            if last_row:
                # 删除行布局中的所有子控件
                while last_row.count():
                    item = last_row.takeAt(0)
                    widget = item.widget()
                    if widget:
                        widget.deleteLater()
                last_row.deleteLater()
            # 从 self.rows 列表中删除最后一个元素
            if self.rows:
                self.rows.pop()

    def extract_slice_info(self):
        # 保存动态控件的信息
        dynamic_rows = []
        for row in self.rows:
            dynamic_rows.append([row['start_value'].text(),row['end_value'].text(),row['num_splits'].text()])
        return dynamic_rows


