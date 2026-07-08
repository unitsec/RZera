######################设计这个模块的原因是：某些谱仪模块以及模块下像素数量太多，全部加载极易撑爆内存，因此只能逐个加载并释放#######################################
from PyQt5.QtWidgets import QLineEdit,QMessageBox,QLabel,QHeaderView,QApplication
from PyQt5.QtGui import QDoubleValidator, QIntValidator, QFont
from utils.browse import browse
from utils.helper import float_or_nan
from utils.scale_nd import scale_bkg
from collections import defaultdict
import traceback,re,glob,h5py,os,time
from rongzai.utils import get_all_from_detector
from rongzai.dataSvc import load_histogram_data,load_event_data
from rongzai.dataSvc.data_loader import get_time_from_hdf
from PyQt5.QtWidgets import QTableWidgetItem, QCheckBox, QWidget, QHBoxLayout, QVBoxLayout, QProgressBar, QDialog
from PyQt5.QtCore import Qt, QObject, QThread, pyqtSignal
from rongzai.algSvc.neutron import convert_unit_elastic
from rongzai.algSvc.neutron import correct_carpenter
from rongzai.algSvc.instrument.timefocus_correction import correct_tof_to_d
from rongzai.dataSvc import read_mask,read_cal,read_instrument_info
from rongzai.algSvc.neutron import mask_neutron_data,crop_neutron_data,focus_neutron_data,rebin_neutron_data,calculate_neutron_data
from rongzai.algSvc.neutron.abs_ms_nd import correct_bkg_abs_psd
from rongzai.algSvc.base import get_sample_properties
from rongzai.utils import generate_x
from rongzai.algSvc.instrument.timeslice import *
from rongzai.utils.histogram import Hist2D
import numpy as np
from utils.ui.BaseUI import CollapsibleWidget
import copy
from datetime import datetime, timezone
import dateutil.parser


def _normalize_hdf_time_value(value):
    if isinstance(value, bytes):
        return value.decode("utf-8").strip()

    if isinstance(value, str):
        return value.strip()

    if isinstance(value, np.ndarray):
        if value.ndim == 0:
            return _normalize_hdf_time_value(value.item())
        if value.size == 0:
            raise ValueError("empty time dataset")
        return _normalize_hdf_time_value(value.reshape(-1)[0])

    if isinstance(value, (list, tuple)):
        if not value:
            raise ValueError("empty time dataset")
        return _normalize_hdf_time_value(value[0])

    return str(value).strip()


def get_time_from_hdf_safe(fn):
    with h5py.File(fn, "r") as hf:
        start = hf["/csns/start_time_utc"][()]
        end = hf["/csns/end_time_utc"][()]
        start_time = _normalize_hdf_time_value(start)
        end_time = _normalize_hdf_time_value(end)
        return start_time, end_time


def mask_neutron_data_tof(neutron_data, mask_tof_list):
    if not mask_tof_list:
        return neutron_data

    tof_ranges = np.asarray(mask_tof_list, dtype=float)
    if tof_ranges.ndim != 2 or tof_ranges.shape[1] != 2:
        raise ValueError("mask_tof_list should be [[tof_start, tof_end], ...].")

    tof_ranges = np.sort(tof_ranges, axis=1)
    range_start = tof_ranges[:, 0]
    range_end = tof_ranges[:, 1]

    xvalue = np.asarray(neutron_data["xvalue"].values)
    histogram = neutron_data["histogram"].values
    error = neutron_data["error"].values if "error" in neutron_data else None

    if xvalue.ndim == 1:
        tof_mask = ((xvalue[:, None] >= range_start) & (xvalue[:, None] <= range_end)).any(axis=1)
        histogram[..., tof_mask] = 0
        if error is not None:
            error[..., tof_mask] = 0
        return neutron_data

    if xvalue.shape == histogram.shape:
        tof_mask = ((xvalue[..., None] >= range_start) & (xvalue[..., None] <= range_end)).any(axis=-1)
        histogram[tof_mask] = 0
        if error is not None:
            error[tof_mask] = 0
        return neutron_data

    tof_axis = xvalue[0]
    tof_mask = ((tof_axis[:, None] >= range_start) & (tof_axis[:, None] <= range_end)).any(axis=1)
    histogram[..., tof_mask] = 0
    if error is not None:
        error[..., tof_mask] = 0
    return neutron_data

class load_and_focus(CollapsibleWidget):
    # finished = pyqtSignal()
    def __init__(self, name, parent):
        super(load_and_focus, self).__init__(name, "utils/ui/load_and_focus.ui", parent)
        self.parent = parent

        validator = QDoubleValidator(0.0, float('inf'), 8, self)  # 创建一个浮点数验证器，限制输入范围在 [0.0, +∞)，且最多允许 8 位小数
        validator.setNotation(QDoubleValidator.StandardNotation)  # 强制使用标准十进制表示法（避免科学计数法）

        validator2 = QDoubleValidator(-float('inf'), float('inf'), 8, self)
        validator2.setNotation(QDoubleValidator.StandardNotation)

        self.run_fn = []
        self.browse_run = browse()
        self.run_button.clicked.connect(lambda: (self.browse_run.select_nxsfiles(self.run_text, self.run_fn), print(self.run_fn)))

        ####################### 配置slice参数 #############################
        self.tof_step.setValidator(validator)
        self.tof_step.setText("8")
        self.operate_slicepara = operate_slicepara(self)
        self.add_slice.clicked.connect(lambda: self.operate_slicepara.add_row())
        self.remove_slice.clicked.connect(lambda: self.operate_slicepara.remove_row())
        self.rebuild.clicked.connect(self.rebuild_histogram_nxs)
        self.load_evt_button.clicked.connect(
            lambda: (
                self.browse_run.select_folder(self.evt_text),
                self.check_evt_files() if self.evt_text.text().strip() else None
            )
        )

        # 悬停提示：说明批处理与合并模式的区别
        try:
            self.is_batch.setToolTip("check it for batch processing; unchecked for merged loading.")
        except Exception:
            pass

        self.detector_button.clicked.connect(
            lambda: self.browse_run.select_detectors(self.detector_text, self.parent.config['base']['group_info'], self.parent.config['base']['bank_info']))

        self.instru_button.clicked.connect(lambda: self.browse_run.select_folder(self.instru_text))


        self.t0_text.setValidator(validator2) # 将 doubleValidator 设置到 QLineEdit 控件上 (只能输入浮点数)
        self.t0_text.setText('0.0')

        self.mask_button.clicked.connect(lambda: self.browse_run.select_folder(self.mask_text))

        self.wave_min.setValidator(validator)  # 将 doubleValidator 设置到 QLineEdit 控件上 (只能输入浮点数)
        self.wave_max.setValidator(validator)

        # 初始化carpenter correction
        self.mass.setValidator(validator)
        self.mass.setText("1.0")
        self.sam_height.setValidator(validator)
        self.sam_height.setText("3.0")
        self.radius_text.setValidator(validator)
        self.radius_text.setText("0.5")
        self.cell_radius_text.setValidator(validator)
        self.cell_radius_text.setText("0.5")
        self.beam_height.setValidator(validator)
        self.beam_height.setText("3.0")
        self.num_density_text.setValidator(validator)
        self.num_density_text.setText("0.01")
        self.num_density_check.stateChanged.connect(lambda state: self.num_density_text.setEnabled(state == 2))
        self.num_density_check.setChecked(False)
        self.sample_name.textChanged.connect(self.update_num_density_label)
        self.mass.textChanged.connect(self.update_num_density_label)
        self.sam_height.textChanged.connect(self.update_num_density_label)
        self.radius_text.textChanged.connect(self.update_num_density_label)
        self.beam_height.textChanged.connect(self.update_num_density_label)

        # 初始化holder absorption
        self.holder_thickness.setValidator(validator)
        self.holder_densityNum.setValidator(validator)
        self.holder_attenXs.setValidator(validator)
        self.holder_incXs.setValidator(validator)

        self.offset_button.clicked.connect(lambda: self.browse_run.select_folder(self.offset_text))

        self.load_button.clicked.connect(self.load)

        self.checkboxes = [] # 存储复选框引用
        self.delete_button.clicked.connect(lambda:self.delete_selected_rows())
        self.delete_all_button.clicked.connect(self.delete_all_rows)

        self.set_default_crop()

    def set_default_crop(self):
        try:
            wave_max = self.parent.config["base"]["wave_max"]
            wave_min = self.parent.config["base"]["wave_min"]
            self.wave_min.setText(str(wave_min))
            self.wave_max.setText(str(wave_max))
        except Exception as e:
            print(f'Reason: {e}')
            traceback.print_exc()  # 打印异常的堆栈跟踪

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
        if self.tableWidget.rowCount() != 0:
            # 显示一个确认对话框
            reply = QMessageBox.question(self, "Confirm", "Table is not empty. Do you want to delete all rows?",
                                         QMessageBox.Yes | QMessageBox.No, QMessageBox.No)

            # 如果用户选择了 "Yes"，则执行删除操作
            if reply == QMessageBox.Yes:
                self.delete_all_rows()
                return True
            else:
                return False
        return True

    def collect_params(self, mode):
        base = copy.deepcopy(self.parent.config['base'])
        return dict(
            mode=mode,
            run_fn=self.run_fn,
            batch_sources=self.build_histogram_batch_sources(self.run_fn),
            evt_text = self.evt_text.text(),
            runno=self.extract_runs_from_lineedit(self.run_text, mode=mode),
            evt_runno = self.extract_runs_from_lineedit(self.evt_text, mode='batch'),
            evt_num = self.check_evt_num(),
            tof_step = self.tof_step.text(),
            slice_info = self.operate_slicepara.extract_slice_info(),
            detectors=self.extract_detectors_from_lineedit(self.detector_text),
            instru_text=self.instru_text.text(),
            mask_text=self.mask_text.text(),
            offset_text=self.offset_text.text(),
            t0_text=float(self.t0_text.text()),
            is_maskTOF=self.is_maskTOF.isChecked(),
            maskTOFList = self.extractTOFList(self.maskTOFText.text()),
            is_mask=self.is_mask.isChecked(),
            is_crop=self.is_crop.isChecked(),
            is_correction=self.is_correction.isChecked(),
            is_bkg_scale=self.is_bkg_scale.isChecked(),
            is_numdensity=self.num_density_check.isChecked(),
            num_density_text = self.num_density_text.text(),
            is_bkgAbs=self.is_bkgAbs.isChecked(),
            is_offset=self.is_offset.isChecked(),
            wave_min=float(self.wave_min.text()),
            wave_max=float(self.wave_max.text()),
            correction_info=self.get_correction_info() if self.is_correction.isChecked() or self.is_bkg_scale.isChecked() else {},  # 在主线程调用
            holder_info=self.get_holder_info() if self.is_bkgAbs.isChecked() else {},  # 在主线程调用
            base=base
        )


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
                    params = self.collect_params(mode)
                    # 创建线程和 Worker 对象
                    self.thread = QThread()
                    self.worker = LoadThreadManager(params, self)
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
                    params = self.collect_params("batch")
                    self.evt_thread = QThread()
                    self.worker = LoadThreadManager(params, self)
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

    def check_rebuild_param(self):
        return self.check_timeslice_param()

    def rebuild_histogram_nxs(self):
        try:
            if not self.check_timeslice_param():
                return

            self.rebuild.setEnabled(False)
            params = self.collect_params("batch")
            self.rebuild_thread = QThread()
            self.worker = LoadThreadManager(params, self)
            self.worker.moveToThread(self.rebuild_thread)

            self.rebuild_progress_dialog = ProgressDialog(self.rebuild_thread, self)
            self.rebuild_progress_dialog.show()

            self.rebuild_thread.started.connect(self.worker.run_rebuild_histogram)
            self.worker.finished.connect(self.rebuild_thread.quit)
            self.worker.finished.connect(self.worker.deleteLater)
            self.rebuild_thread.finished.connect(self.rebuild_thread.deleteLater)
            self.worker.error.connect(self.handle_error)
            self.worker.progress.connect(self.rebuild_progress_dialog.progress_bar.setValue)
            self.worker.progress_text.connect(self.rebuild_progress_dialog.update_info)
            self.worker.finished.connect(lambda: (self.rebuild_progress_dialog.close(), self.rebuild.setEnabled(True)))

            self.rebuild_thread.start()
        except Exception as e:
            self.rebuild.setEnabled(True)
            print(f'Reason: {e}')
            traceback.print_exc()  # 打印异常的堆栈跟踪

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
            "mass": float(self.mass.text()) if self.mass.text() else 0.0,
            "cell_radius": float(self.cell_radius_text.text()) if self.cell_radius_text.text() else 0.0,
            "volume": {
                "type": "cylinder",
                "height": float(self.sam_height.text() if self.sam_height.text() else 0.0),
                "radius": float(self.radius_text.text() if self.radius_text.text() else 0.0),
                "beam_height": float(self.beam_height.text() if self.beam_height.text() else 0.0),
                "thickness": 0},
            "scale": 1
        }

    def get_holder_info(self):
        return {
            "holder_thickness": float(self.holder_thickness.text()) if self.holder_thickness.text() else 0.0,
            "holder_densityNum": float(self.holder_densityNum.text()) if self.holder_densityNum.text() else 0.0,
            "holder_attenXs": float(self.holder_attenXs.text()) if self.holder_attenXs.text() else 0.0,
            "holder_incXs": float(self.holder_incXs.text()) if self.holder_incXs.text() else 0.0
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

    def get_config(self):
        return {
            "detector_text": self.detector_text.text(),
            "run_text": self.run_text.text(),
            "instru_text": self.instru_text.text(),
            "t0_text": self.t0_text.text(),
            "run_fn": self.run_fn,
            "is_mask": self.is_mask.isChecked(),
            "mask_text": self.mask_text.text(),
            "is_maskTOF": self.is_maskTOF.isChecked(),
            "maskTOFtext": self.maskTOFText.text(),
            "is_crop": self.is_crop.isChecked(),
            "wave_min": self.wave_min.text(),
            "wave_max": self.wave_max.text(),
            "is_correction": self.is_correction.isChecked(),
            "is_bkg_scale": self.is_bkg_scale.isChecked(),
            "sample_name": self.sample_name.text(),
            "mass": self.mass.text(),
            "radius": self.radius_text.text(),
            "cell_radius": self.cell_radius_text.text(),
            "sam_height": self.sam_height.text(),
            "beam_height": self.beam_height.text(),
            "num_density_check": self.num_density_check.isChecked(),
            "num_density_text": self.num_density_text.text(),
            "is_bkgAbs": self.is_bkgAbs.isChecked(),
            "holder_thickness": self.holder_thickness.text(),
            "holder_densityNum": self.holder_densityNum.text(),
            "holder_attenXs": self.holder_attenXs.text(),
            "holder_incXs": self.holder_incXs.text(),
            "is_offset": self.is_offset.isChecked(),
            "plot": self.plot.isChecked(),
            "offset_text": self.offset_text.text(),
            "evt_text": self.evt_text.text(),
            "exp_time": self.exp_time.text(),
            "tof_step": self.tof_step.text(),
            "slice_parameters": self.operate_slicepara.extract_slice_info(),
            "which_tab": self.tabWidget.currentIndex(),
            "is_use": self.toggle_button.isChecked()
        }

    def set_config(self,config):
        """根据配置更新模块状态"""
        self.detector_text.setText(config.get("detector_text", ""))
        self.run_text.setText(config.get("run_text", ""))
        self.instru_text.setText(config.get("instru_text", ""))
        self.t0_text.setText(config.get("t0_text", ""))
        self.run_fn = config.get("run_fn",[])
        self.is_mask.setChecked(config.get("is_mask",False))
        self.mask_text.setText(config.get("mask_text", ""))
        self.is_maskTOF.setChecked(config.get("is_maskTOF", False))
        self.maskTOFText.setText(config.get("maskTOFtext", ""))
        self.is_crop.setChecked(config.get("is_crop", False))
        self.wave_min.setText(config.get("wave_min", ""))
        self.wave_max.setText(config.get("wave_max", ""))
        self.is_correction.setChecked(config.get("is_correction", False))
        self.is_bkg_scale.setChecked(config.get("is_bkg_scale", False))
        self.sample_name.setText(config.get("sample_name", ""))
        self.mass.setText(config.get("mass", ""))
        self.radius_text.setText(config.get("radius", ""))
        self.cell_radius_text.setText(config.get("cell_radius", ""))
        self.sam_height.setText(config.get("sam_height", ""))
        self.beam_height.setText(config.get("beam_height", ""))
        self.num_density_check.setChecked(config.get("num_density_check",False))
        self.num_density_text.setText(config.get("num_density_text",""))
        self.is_bkgAbs.setChecked(config.get("is_bkgAbs", False))
        self.holder_thickness.setText(config.get("holder_thickness", ""))
        self.holder_densityNum.setText(config.get("holder_densityNum", ""))
        self.holder_attenXs.setText(config.get("holder_attenXs", ""))
        self.holder_incXs.setText(config.get("holder_incXs", ""))
        self.is_offset.setChecked(config.get("is_offset", False))
        self.offset_text.setText(config.get("offset_text", ""))
        self.plot.setChecked(config.get("plot", False))
        self.evt_text.setText(config.get("evt_text", ""))
        self.exp_time.setText(config.get("exp_time", ""))
        self.tof_step.setText(config.get("tof_step", ""))
        self.set_scrollArea(config.get("slice_parameters", []))
        self.tabWidget.setCurrentIndex(config.get("which_tab", 0))
        self.toggle_button.setChecked(config.get("is_use", False))


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

    def build_histogram_batch_sources(self, selected_files):
        run_pattern = re.compile(r'RUN\d+')
        batch_sources = []
        default_labels = []

        for file_path in selected_files:
            file_name = os.path.basename(file_path)
            base_name = os.path.splitext(file_name)[0]
            match = run_pattern.search(file_path)
            default_labels.append(match.group() if match else base_name)

        duplicated_labels = {label for label in default_labels if default_labels.count(label) > 1}

        for index, file_path in enumerate(selected_files):
            file_name = os.path.basename(file_path)
            base_name = os.path.splitext(file_name)[0]
            label = default_labels[index]
            if label in duplicated_labels:
                label = base_name
            batch_sources.append({
                "label": label,
                "files": [file_path]
            })

        return batch_sources

    def extract_detectors_from_lineedit(self,lineEdit):
        detector_list = lineEdit.text().split('; ')
        return detector_list
    
    def extractTOFList(self,text):
        if not text or not text.strip():
            return []

        mask_range_text = text.replace('，', ',').replace(';', ',').replace('\n', ',')
        mask_range_list = [item.strip() for item in mask_range_text.split(',') if item.strip()]
        formatted_mask_ranges = []

        for mask_range in mask_range_list:
            range_parts = [part.strip() for part in mask_range.split('-')]
            if len(range_parts) != 2 or not range_parts[0] or not range_parts[1]:
                QMessageBox.warning(
                    self,
                    "warning",
                    f"Invalid TOF range: {mask_range}. Please use a format like 40000-40040,50010-50020"
                )
                return []

            try:
                start_tof = float(range_parts[0])
                end_tof = float(range_parts[1])
            except ValueError:
                QMessageBox.warning(
                    self,
                    "warning",
                    f"Invalid TOF range: {mask_range}. Please use a format like 40000-40040,50010-50020"
                )
                return []

            if start_tof > end_tof:
                start_tof, end_tof = end_tof, start_tof

            formatted_mask_ranges.append([start_tof, end_tof])

        return formatted_mask_ranges
        


    def check_evt_files(self):
        evt_num = self.check_evt_num()
        if evt_num == 0:
            QMessageBox.warning(self, "warning", "The number of each module's evt files is not same. Please Check!")
            return
        if evt_num == -1:
            QMessageBox.warning(self, "warning", "The number of each module's evt files is 0! Please Check!")
            return
        exist = self.check_pc_file()
        print(exist)
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
        if all(count == file_counts[0] for count in file_counts):
            if len(file_counts) == 0:
                return -1 # 返回-1表示没有文件
            else:
                return file_counts[0]  # 返回文件数量
        else:
            return 0  # 返回0表示数量不一致

    def check_pc_file(self):
        pattern = os.path.join(self.evt_text.text(), "pc*.nxs")
        files = glob.glob(pattern)
        print(files)
        if len(files) != 0:
            return True
        else:
            return False

    def read_exptime(self,parent):
        sam_path = parent.evt_text.text()
        flist = glob.glob(sam_path + "/pc*.nxs")
        pc_fn = flist[0]
        try:
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
            QMessageBox.warning(self, "warning", f"The data in {os.path.basename(pc_fn)} has some problems!")
            parent.exp_time.setText('None')

    def find_earliest_and_latest_times(self, run_fns, get_time_from_hdf):
        """
        run_fns: 可迭代，包含 HDF 文件路径
        get_time_from_hdf: 函数(fn) -> (start_time_str, end_time_str)
        返回: (earliest_start_dt, latest_end_dt) (datetime with tz if parsed)
        """
        earliest = None
        latest = None
        for fn in run_fns:
            try:
                start_str, end_str = get_time_from_hdf(fn)
            except Exception as e:
                print(f"warning: failed to read times from {fn}: {e}")
                continue

            try:
                # dateutil.parser 能解析多种 ISO/常见格式，保留时区信息（若存在）
                start_dt = dateutil.parser.isoparse(start_str) if hasattr(dateutil.parser, "isoparse") else dateutil.parser.parse(start_str)
            except Exception:
                # 兜底：尝试 parse（dateutil.parse 通常能处理更多格式）
                try:
                    start_dt = dateutil.parser.parse(start_str)
                except Exception as e:
                    print(f"warning: cannot parse start time from {fn}: '{start_str}' -> {e}")
                    continue

            try:
                end_dt = dateutil.parser.isoparse(end_str) if hasattr(dateutil.parser, "isoparse") else dateutil.parser.parse(end_str)
            except Exception:
                try:
                    end_dt = dateutil.parser.parse(end_str)
                except Exception as e:
                    print(f"warning: cannot parse end time from {fn}: '{end_str}' -> {e}")
                    continue

            # 如果没有时区信息，假设为 UTC（可按需改）
            if start_dt.tzinfo is None:
                start_dt = start_dt.replace(tzinfo=timezone.utc)
            if end_dt.tzinfo is None:
                end_dt = end_dt.replace(tzinfo=timezone.utc)

            if earliest is None or start_dt < earliest:
                earliest = start_dt
            if latest is None or end_dt > latest:
                latest = end_dt

        # 返回格式化字符串：YYYY-MM-DD HH:MM:SS
        if earliest is None or latest is None:
            return None, None

        # 将时间转换为本函数期望的字符串形式（去掉时区信息，保留 UTC 时间）
        earliest_str = earliest.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        latest_str = latest.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        return earliest_str, latest_str

class LoadThreadManager(QObject):
    finished = pyqtSignal()  # 任务完成信号
    error = pyqtSignal(str)  # 任务错误信号
    data_ready = pyqtSignal(dict)  # 数据准备好信号
    progress = pyqtSignal(int)  # 进度信号
    progress_text = pyqtSignal(str)

    def __init__(self, params, parent_widget):
        super().__init__()
        self.params = params
        self.parent_widget = parent_widget
        self.current_time = time.strftime("%Y-%m-%d-%H:%M:%S")
        self.is_running = True  # 标志位，控制线程是否继续运行

    def run(self):
        try:
            if self.params['mode'] == 'merge':
                self.mergeLoad_and_focus()
            else:
                self.batchLoad_and_focus()
            self.finished.emit()  # 任务完成，发送信号
        except Exception as e:
            traceback.print_exc()  # 打印异常的堆栈跟踪
            self.error.emit(str(e))  # 任务出错，发送信号
            self.finished.emit()  # 任务完成，发送信号

    def mergeLoad_and_focus(self):
        p = self.params
        runno = p['runno']
        detectors_list = p['detectors']
        total_tasks = len(detectors_list)
        for index, detector in enumerate(detectors_list):
            if not self.is_running:  # 检查标志位
                return
            data_dict = {}
            data_dict["runno"] = runno
            data_dict['detector'] = detector
            data_dict['record'] = {}
            group, modules = get_all_from_detector(detector, p['base']['group_info'],
                                                   p['base']['bank_info'])
            dvalue = generate_x(p['base']['d_rebin'][group][0],
                                p['base']['d_rebin'][group][1],
                                p['base']['d_rebin'][group][2],
                                p['base']['d_rebin']['mode'])
            
            earliest_dt, latest_dt = self.parent_widget.find_earliest_and_latest_times(p['run_fn'], get_time_from_hdf_safe)
            if earliest_dt and latest_dt:
                # find_earliest_and_latest_times 已返回格式化的字符串（UTC）
                data_dict['start_time'] = earliest_dt
                data_dict['end_time'] = latest_dt
            
            for i, module in enumerate(modules):
                if not self.is_running:  # 检查标志位
                    return
                self.progress_text.emit(f"Start Loading and focusing {detector}, {module}")
                pidInfo_fn = os.path.join(p['instru_text'], module + ".txt")
                if not os.path.exists(pidInfo_fn):
                    self.error.emit(f"Please check the instru file of {module}!")
                    return
                neutron_data = load_histogram_data(p['run_fn'], pidInfo_fn, module,
                                                 p['base']["first_flight_distance"],
                                                 float(p['t0_text']))
                if p['is_mask']:
                    mask_file = p['mask_text'] + "/" + module + "_mask.txt"
                    if os.path.exists(mask_file): 
                        cal_dict = read_mask(mask_file)
                        neutron_data = mask_neutron_data(neutron_data, cal_dict["mask_list"])
                        data_dict["record"]["mask"] = p['instru_text']
                    else:
                        print(f"the mask file of {module} is not exist.")
                if p['is_maskTOF']:
                    neutron_data = mask_neutron_data_tof(neutron_data, p['maskTOFList'])
                    data_dict["record"]["maskTOF"] = p['maskTOFList']
                if p['is_crop']:
                    neutron_data = convert_unit_elastic(neutron_data, "wavelength")
                    neutron_data = crop_neutron_data(neutron_data, float(p['wave_min']),float(p['wave_max']))
                    # neutron_data = convert_unit_elastic(neutron_data, "tof")
                    data_dict["record"]["crop"] = f"{p['wave_min']}_{p['wave_max']}"
                if p['is_correction']:
                    # 下面这一步这么写，是为了确保correction_info里面必须有"density_num"这一项，这用于后面pdf的pho0的计算
                    if p['is_numdensity']:
                        p['correction_info']["density_num"] = float(p['num_density_text'])
                        cal_info = get_sample_properties(p['correction_info'])
                    else:
                        cal_info = get_sample_properties(p['correction_info'])
                        p['correction_info']["density_num"] = cal_info["density_num"]

                    neutron_data = convert_unit_elastic(neutron_data,"wavelength")
                    neutron_data = correct_carpenter(neutron_data, cal_info)
                    # neutron_data = convert_unit_elastic(neutron_data, "tof")
                    data_dict["record"]["carpenterCorrection"] = p['correction_info']
                if p['is_bkg_scale']:
                    # 下面这一步这么写，是为了确保correction_info里面必须有"density_num"这一项，这用于后面pdf的pho0的计算
                    if p['is_numdensity']:
                        p['correction_info']["density_num"] = float(p['num_density_text'])
                        cal_info = get_sample_properties(p['correction_info'])
                    else:
                        cal_info = get_sample_properties(p['correction_info'])
                    cal_info['cell_radius'] = p['correction_info']['cell_radius']
                    neutron_data = convert_unit_elastic(neutron_data, "wavelength")
                    neutron_data = scale_bkg(neutron_data, cal_info)
                    data_dict["record"]["scaleBkg"] = p['correction_info']
                if p['is_bkgAbs']:
                    neutron_data = convert_unit_elastic(neutron_data, "wavelength")
                    neutron_data = correct_bkg_abs_psd(neutron_data, p['holder_info'])
                    data_dict["record"]["holderAbsCorrection"] = p['holder_info']
                if p['is_offset']:
                    cal_fn = p['offset_text'] + "/" + module + "_offset.cal"
                    try:
                        cal_dict = read_cal(cal_fn)
                    except:
                        self.error.emit(f"Please check the offset file of {module}!")
                        return
                    neutron_data = convert_unit_elastic(neutron_data, "tof")
                    data_d = correct_tof_to_d(neutron_data, cal_dict)
                    data_d = mask_neutron_data(data_d, cal_dict["mask_list"])
                    data_d_focused = focus_neutron_data(data_d,None)
                    data_dict["record"]["offset"] = p['offset_text']
                else:
                    neutron_data = convert_unit_elastic(neutron_data, "tof")
                    neutron_data = convert_unit_elastic(neutron_data, "dspacing")
                    data_d_focused = focus_neutron_data(neutron_data,dvalue)
                data_d_focused = rebin_neutron_data(data_d_focused, dvalue)
                if i == 0:
                    data_dict['detector_focused'] = data_d_focused
                else:
                    data_dict["detector_focused"] = calculate_neutron_data("add", data_dict["detector_focused"], data_d_focused)
            if not self.is_running:  # 检查标志位
                break

            self.progress_text.emit(
                f"Start Loading and focusing {detector}, {self.parent_widget.parent.config['base']['normalization_monitor']}")
            try:
                pidInfo_fn = p['instru_text'] + "/" + p['base']["normalization_monitor"] + ".txt"
                monitor_data = load_histogram_data(p['run_fn'], pidInfo_fn,
                                                 p['base']["normalization_monitor"],
                                                 p['base']["first_flight_distance"],
                                                 float(p['t0_text']))
                if p['is_crop']:
                    monitor_data = convert_unit_elastic(monitor_data, "wavelength")
                    monitor_data = crop_neutron_data(monitor_data, float(p['wave_min']), float(p['wave_max']))
                    monitor_data = focus_neutron_data(monitor_data,None)
                data_dict["monitor"] = monitor_data.copy()
                mc = monitor_data["histogram"].values.sum()
                data_dict["monitor_counts"] = mc
            except:
                self.progress_text.emit(f"The Load of {p['base']['normalization_monitor']} failed!")
            self.get_name_of_data_dict(data_dict)
            self.data_ready.emit(data_dict)
            # self.parent.data_list.append(data_dict)
            # self.append_data([data_dict])
            # 计算并发射进度
            progress = int((index + 1) / total_tasks * 100)
            self.progress.emit(progress)

    def batchLoad_and_focus(self):
        p = self.params
        batch_sources = p.get('batch_sources') or []
        if batch_sources:
            run_sources = [(item['label'], item['files']) for item in batch_sources]
        else:
            run_sources = []
            for runno in p['runno']:
                run_sources.append((runno, self.extract_runfn_from_runno(p['run_fn'], runno)))
        detectors_list = p['detectors']
        total_tasks = len(run_sources) * len(detectors_list)
        task_index = 0
        for runno, extracted_runfn in run_sources:
            for detector in detectors_list:
                if not self.is_running:  # 检查标志位
                    return
                data_dict = {}
                data_dict['runno'] = runno
                data_dict['detector'] = detector
                data_dict['record'] = {}
                group, modules = get_all_from_detector(detector, p['base']['group_info'],
                                                       p['base']['bank_info'])
                dvalue = generate_x(p['base']['d_rebin'][group][0],
                                    p['base']['d_rebin'][group][1],
                                    p['base']['d_rebin'][group][2],
                                    p['base']['d_rebin']['mode'])
                earliest_dt, latest_dt = self.parent_widget.find_earliest_and_latest_times(extracted_runfn, get_time_from_hdf_safe)
                if earliest_dt and latest_dt:
                    # find_earliest_and_latest_times 已返回格式化的字符串（UTC）
                    data_dict['start_time'] = earliest_dt
                    data_dict['end_time'] = latest_dt
                
                for i, module in enumerate(modules):
                    if not self.is_running:  # 检查标志位
                        return
                    self.progress_text.emit(f"Start Loading and focusing {detector}, {module}")
                    pidInfo_fn = os.path.join(p['instru_text'], module + ".txt")
                    if not os.path.exists(pidInfo_fn):
                        self.error.emit(f"Please check the instru file of {module}!")
                        return
                    neutron_data = load_histogram_data(extracted_runfn, pidInfo_fn, module,
                                                       p['base']["first_flight_distance"],
                                                       float(p['t0_text']))
                    if p['is_mask']:
                        mask_file = p['mask_text'] + "/" + module + "_mask.txt"
                        if os.path.exists(mask_file): 
                            cal_dict = read_mask(mask_file)
                            neutron_data = mask_neutron_data(neutron_data, cal_dict["mask_list"])
                            data_dict["record"]["mask"] = p['instru_text']
                        else:
                            print(f"the mask file of {module} is not exist.")
                    if p['is_maskTOF']:
                        neutron_data = mask_neutron_data_tof(neutron_data, p['maskTOFList'])
                        data_dict["record"]["maskTOF"] = p['maskTOFList']
                    if p['is_crop']:
                        neutron_data = convert_unit_elastic(neutron_data, "wavelength")
                        neutron_data = crop_neutron_data(neutron_data, float(p['wave_min']), float(p['wave_max']))
                        # neutron_data = convert_unit_elastic(neutron_data, "tof")
                        data_dict["record"]["crop"] = f"{p['wave_min']}_{p['wave_max']}"
                    if p['is_correction']:
                        # 下面这一步这么写，是为了确保correction_info里面必须有"density_num"这一项，这用于后面pdf的pho0的计算
                        if p['is_numdensity']:
                            p['correction_info']["density_num"] = float(p['num_density_text'])
                            cal_info = get_sample_properties(p['correction_info'])
                        else:
                            cal_info = get_sample_properties(p['correction_info'])
                            p['correction_info']["density_num"] = cal_info["density_num"]

                        neutron_data = convert_unit_elastic(neutron_data, "wavelength")
                        neutron_data = correct_carpenter(neutron_data, cal_info)
                        # neutron_data = convert_unit_elastic(neutron_data, "tof")
                        data_dict["record"]["carpenterCorrection"] = p['correction_info']

                    if p['is_bkgAbs']:
                        neutron_data = convert_unit_elastic(neutron_data, "wavelength")
                        neutron_data = correct_bkg_abs_psd(neutron_data, p['holder_info'])
                        data_dict["record"]["holderAbsCorrection"] = p['holder_info']

                    if p['is_offset']:
                        cal_fn = p['offset_text'] + "/" + module + "_offset.cal"
                        try:
                            cal_dict = read_cal(cal_fn)
                        except:
                            self.error.emit(f"Please check the offset file of {module}!")
                            return
                        neutron_data = convert_unit_elastic(neutron_data, "tof")
                        data_d = correct_tof_to_d(neutron_data, cal_dict)
                        data_d = mask_neutron_data(data_d, cal_dict["mask_list"])
                        data_d_focused = focus_neutron_data(data_d, dvalue)
                        data_dict["record"]["offset"] = p['offset_text']
                    else:
                        neutron_data = convert_unit_elastic(neutron_data, "tof")
                        neutron_data = convert_unit_elastic(neutron_data, "dspacing")
                        data_d_focused = focus_neutron_data(neutron_data, dvalue)
                    # data_d_focused = rebin_neutron_data(data_d_focused, dvalue)
                    if i == 0:
                        data_dict['detector_focused'] = data_d_focused
                    else:
                        data_dict["detector_focused"] = calculate_neutron_data("add", data_dict["detector_focused"],
                                                                               data_d_focused)
                if not self.is_running:  # 检查标志位
                    break

                self.progress_text.emit(
                    f"Start Loading and focusing {detector}, {self.parent_widget.parent.config['base']['normalization_monitor']}")
                try:
                    pidInfo_fn = p['instru_text'] + "/" + p['base']["normalization_monitor"] + ".txt"
                    monitor_data = load_histogram_data(p['run_fn'], pidInfo_fn,
                                                       p['base']["normalization_monitor"],
                                                       p['base']["first_flight_distance"],
                                                       float(p['t0_text']))
                    if p['is_crop']:
                        monitor_data = convert_unit_elastic(monitor_data, "wavelength")
                        monitor_data = crop_neutron_data(monitor_data, float(p['wave_min']), float(p['wave_max']))
                        monitor_data = focus_neutron_data(monitor_data, None)
                    data_dict["monitor"] = monitor_data.copy()
                    mc = monitor_data["histogram"].values.sum()
                    data_dict["monitor_counts"] = mc
                except:
                    self.progress_text.emit(f"The Load of {p['base']['normalization_monitor']} failed!")
                self.get_name_of_data_dict(data_dict)
                # print(f"add the {data_dict['name']}")
                self.data_ready.emit(data_dict)
                # self.parent.data_list.append(data_dict)
                # self.append_data([data_dict])
                # 计算并发射进度
                task_index += 1
                progress = int(task_index / total_tasks * 100)
                self.progress.emit(progress)

    def get_unrepeated_modules_from_dectectors(self, detectors_list):
        modulesList = set()
        for detector in detectors_list:
            group, modules = get_all_from_detector(detector,
                                                   self.params['base']['group_info'],
                                                   self.params['base']['bank_info'])
            modulesList.update(modules)
        return list(modulesList)

    def get_name_of_data_dict(self, data_dict):
        name = data_dict["runno"]
        if "time_slice" in data_dict.keys():
            name = f"{name}_slicedTime({data_dict['time_slice']})"
        for key in data_dict["record"].keys():
            name = f"{name}_{key}"
        name = f"{name}_time({self.current_time})"
        data_dict["name"] = name

    def run_slice(self):
        try:
            p = self.params
            detectors_list = p['detectors']
            modules_list = self.get_unrepeated_modules_from_dectectors(detectors_list)
            self.slice_worker = TimeSlice(modules_list,p,self)
            self.slice_worker.setup_timeslice()
            time_list = self.slice_worker.generate_slice_time_list()
            total_tasks = len(self.slice_worker.moduleList) + len(detectors_list) * len(time_list)
            task_index = 0
            for module in self.slice_worker.moduleList:
                if not self.is_running:  # 检查标志位
                    break
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
                    break
                self.progress_text.emit(f"Start calculating the sliced data {i+1}")
                for detector in detectors_list:
                    if not self.is_running:  # 检查标志位
                        break
                    data_dict = {}
                    data_dict["runno"] = self.slice_worker.conf['sample_run'][-1]
                    data_dict["time_slice"] = f"{round(time_list[i][0],2)}-{round(time_list[i][1],2)}"
                    data_dict["detector"] = detector
                    data_dict["record"] = {}
                    data_dict["record"].update(self.slice_worker.record)
                    self.get_name_of_data_dict(data_dict)
                    group, modules = get_all_from_detector(detector,
                                                           p['base']['group_info'],
                                                           p['base']['bank_info'])
                    dvalue = generate_x(p['base']['d_rebin'][group][0],
                                        p['base']['d_rebin'][group][1],
                                        p['base']['d_rebin'][group][2], p['base']['d_rebin']['mode'])
                    
                    
                    for j, module in enumerate(modules):
                        data_d_focused = rebin_neutron_data(data[module], dvalue)
                        if j == 0:
                            data_dict['detector_focused'] = data_d_focused
                        else:
                            data_dict["detector_focused"] = calculate_neutron_data("add", data_dict["detector_focused"],
                                                                                   data_d_focused)
                    data_dict["detector_focused"]["proton_charge"] = sliced_pc[i]
                    try:
                        data_dict["monitor_counts"] = data[p['base']['normalization_monitor']]
                    except:
                        pass
                    self.data_ready.emit(data_dict)
                    # 计算并发射进度
                    task_index += 1
                    progress = int(task_index / total_tasks * 100)
                    self.progress.emit(progress)
            self.finished.emit()  # 任务完成，发送信号

        except Exception as e:
            import traceback
            traceback.print_exc()  # 打印异常的堆栈跟踪
            self.error.emit(str(e))  # 任务出错，发送信号

    def is_data_exist(self,data_list,runno,detector):
        for data in data_list:
            if runno == data["name"] and detector == data["detector"]:
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

    def run_rebuild_histogram(self):
        try:
            p = self.params
            detectors_list = p['detectors']
            modules_list = self.get_unrepeated_modules_from_dectectors(detectors_list)
            self.slice_worker = TimeSlice(modules_list, p, self)
            self.slice_worker.setup_timeslice()
            self.slice_worker.save_histogram = True
            self.slice_worker.conf["save_path"] = self.slice_worker.data_path

            total_tasks = len(self.slice_worker.moduleList) + 1
            for index, module in enumerate(self.slice_worker.moduleList):
                if not self.is_running:
                    return
                self.progress_text.emit(f"Start rebuilding histogram {module}")
                self.slice_worker.get_slice_module(module)
                progress = int((index + 1) / total_tasks * 100)
                self.progress.emit(progress)

            if not self.is_running:
                return
            self.progress_text.emit("Start saving histogram nexus files")
            self.slice_worker.slice_proton_charge()
            self.slice_worker.save_histogram_nxs()
            self.progress.emit(100)
            self.finished.emit()
        except Exception as e:
            traceback.print_exc()
            self.error.emit(str(e))
            self.finished.emit()

class TimeSlice:
    def __init__(self, modules,p, parent):
        self.params = p
        self.parent = parent
        self.conf = p["base"]
        self.conf["data_path"] = os.path.dirname(p['evt_text'])
        self.conf["sample_run"] = p["evt_runno"]
        self.conf["slice_part"] = {"evt_file_num": p['evt_num'],
                                    "tof_step": float(p['tof_step']),
                                    "start_pulseID":0,
                                    "slice_info":self.convert_to_num(p['slice_info'])}
        self.conf["param_path"] = p['instru_text']
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
        print(flist)
        pc_fn = flist[0]
        with h5py.File(pc_fn, "r") as hf:
            try:
                return hf["/csns/logs/proton_charge/pulse_time"][0]
            except:
                return hf["/csns/logs/pulse_time"][0]

    def save_chunk(self, buffer, chunk_counter, moduleName, config):
        p = self.params
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
                if p['is_crop']:
                    monitor_data = convert_unit_elastic(monitor_data, "wavelength")
                    monitor_data = crop_neutron_data(monitor_data,
                                                     float(p['wave_min']),
                                                     float(p['wave_max']))
                    monitor_data = focus_neutron_data(monitor_data,None)
                mc = monitor_data["histogram"].values.sum()
                self.focused_data[str(chunk_counter)][moduleName] = mc
            else:
                txt_fn = os.path.join(self.conf["param_path"], moduleName + ".txt")
                if not os.path.exists(txt_fn):
                    self.parent.error.emit(
                        f"Please check the instru file of {moduleName}!")
                    self.parent.finished.emit()  # 任务完成，发送信号
                try:
                    neutron_data = load_event_data(buffer['event_pixel_id'], buffer["event_time_of_flight"],
                                                         self.conf["slice_part"]["tof_step"], 1, txt_fn, moduleName,
                                                         self.conf["first_flight_distance"], x_offset=0)
                except:
                    self.parent.error.emit(f"Please check the evt files of {moduleName}!")
                    self.parent.finished.emit()  # 任务完成，发送信号
                if p['is_mask']:
                    mask_file = p['mask_text'] + "/" + moduleName + "_mask.txt"
                    if os.path.exists(mask_file):
                        cal_dict = read_mask(mask_file)
                        neutron_data = mask_neutron_data(neutron_data, cal_dict["mask_list"])
                        self.record["mask"] = p['mask_text']
                    else:
                        print(f"the mask file of {moduleName} is not exist.")
                if p['is_maskTOF']:
                    neutron_data = mask_neutron_data_tof(neutron_data, p['maskTOFList'])
                    self.record["maskTOF"] = p['maskTOFList']
                if p['is_crop']:
                    neutron_data = convert_unit_elastic(neutron_data, "wavelength")
                    neutron_data = crop_neutron_data(neutron_data, float(p['wave_min']),float(p['wave_max']))
                    # neutron_data = convert_unit_elastic(neutron_data, "tof")
                    self.record["crop"] = f"{p['wave_min']}_{p['wave_max']}"
                if p['is_correction']:
                    # 下面这一步这么写，是为了确保correction_info里面必须有"density_num"这一项，这用于后面pdf的pho0的计算
                    if p['is_numdensity']:
                        p['correction_info']["density_num"] = float(p['num_density_text'])
                        cal_info = get_sample_properties(p['correction_info'])
                    else:
                        cal_info = get_sample_properties(p['correction_info'])
                        p['correction_info']["density_num"] = cal_info["density_num"]

                    neutron_data = convert_unit_elastic(neutron_data, "wavelength")
                    neutron_data = correct_carpenter(neutron_data, cal_info)
                    # neutron_data = convert_unit_elastic(neutron_data, "tof")
                    self.record["carpenterCorrection"] = p['correction_info']
                if p['is_bkgAbs']:
                    neutron_data = convert_unit_elastic(neutron_data, "wavelength")
                    neutron_data = correct_bkg_abs_psd(neutron_data, p['holder_info'])
                    self.record["holderAbsCorrection"] = p['holder_info']

                if p['is_offset']:
                    cal_fn = p['offset_text'] + "/" + moduleName + "_offset.cal"
                    try:
                        cal_dict = read_cal(cal_fn)
                    except:
                        self.parent.error.emit(f"Please check the offset file of {moduleName}!")
                        self.parent.finished.emit()  # 任务完成，发送信号
                    neutron_data = convert_unit_elastic(neutron_data, "tof")
                    data_d = correct_tof_to_d(neutron_data, cal_dict)
                    data_d = mask_neutron_data(data_d, cal_dict["mask_list"])
                    data_d_focused = focus_neutron_data(data_d,None)
                    self.record["offset"] = p['offset_text']
                else:
                    neutron_data = convert_unit_elastic(neutron_data, "tof")
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
                    print(moduleName)
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


