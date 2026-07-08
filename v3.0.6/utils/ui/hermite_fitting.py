import traceback,time
from typing import List
from PyQt5.QtGui import QDoubleValidator
from PyQt5.QtCore import QObject, QThread, pyqtSignal
from PyQt5.QtWidgets import QVBoxLayout, QProgressBar, QDialog,QMessageBox
from rongzai.utils import chebyshev,fockstate,get_all_from_detector
from rongzai.algSvc.base import (data_expansion,fit_chebyshev,convolve_instr_hermite_parallel,convolve_box_function,lorch_filter)
from scipy.interpolate import interp1d
from utils.ui.BaseUI import CollapsibleWidget
import numpy as np
import copy

class hermite_fitting(CollapsibleWidget):
    finished = pyqtSignal()
    def __init__(self, parent):
        super(hermite_fitting, self).__init__("Hermite Fitting", "utils/ui/hermite_fitting.ui", parent)
        self.parent = parent
        self.validator = QDoubleValidator()
        self.q_min.setValidator(self.validator)
        self.q_max.setValidator(self.validator)
        self.q_num.setValidator(self.validator)
        self.r_min.setValidator(self.validator)
        self.r_max.setValidator(self.validator)
        self.r_num.setValidator(self.validator)
        self.nhermites_text.setValidator(self.validator)
        self.nhermites_text.setText("8")
        self.self_term.setValidator(self.validator)
        self.chebyshev_order.setValidator(self.validator)
        self.nhermites_select.currentIndexChanged.connect(self.on_combobox_changed)
        self.nhermites_select.setCurrentText("Auto")

    def on_combobox_changed(self):
        if self.nhermites_select.currentText() == 'Auto':
            self.nhermites_text.setEnabled(False)
        else:
            self.nhermites_text.setEnabled(True)

    def run(self):
        if self.toggle_button.isChecked():
            # 创建线程和 Worker 对象
            self.thread = QThread()
            self.worker = LoadThreadManager(self)
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
            self.worker.warning_info.connect(self.massage_box)
            self.worker.progress.connect(self.progress_dialog.progress_bar.setValue)  # 更新进度条
            self.worker.r_max.connect(self.r_max.setText) # 更新r_max
            self.worker.finished.connect(self.progress_dialog.close)  # 任务完成后关闭进度条窗口
            self.worker.finished.connect(self.operation_after_finish)  # 任务完成后执行，是供上层检测任务是否完成的信号

            # 启动线程
            self.thread.start()
        else:
            self.operation_after_finish()

    # 该方法需要在run方法的最后调用，目的是供上层在调用该模块时，检测任务是否完成。
    def operation_after_finish(self):
        self.finished.emit()  # 定义一个信号
        return

    def massage_box(self, title, content):
        QMessageBox.warning(self,title,content)

    def handle_error(self, error_message):
        print(f"Error: {error_message}")

    def plot_data(self):
        if self.toggle_button.isChecked():
            plot_data = []
            if self.is_hermite_fitting.isChecked():
                for data in self.parent.data_list:
                    if "pdf_data" in data:
                        # 在 name 后添加时间戳，便于区分不同运行/时间点的结果
                        ts = time.strftime('%H%M%S', time.localtime())
                        plot_data.append({"name": f"{data['pdf_type']}_{data['name']}_{ts}",
                                          "data": copy.deepcopy(data["pdf_data"]),
                                          "x_label": 'r (Å)',
                                          "y_label": "Intensity (a.u.)"
                                          })

            else:
                for data in self.parent.data_list:
                    if "qiq_data" in data:
                        plot_data.append({"name":f"{data['name']} to qiq",
                                          "data":copy.deepcopy(data['qiq_data']),
                                          "x_label": r'Q (Å$^{-1}$)',
                                          "y_label": "Intensity (a.u.)"
                                          })
            return plot_data
        else:
            return []

    def get_config(self):
        return {
            "plot": self.plot.isChecked(),
            "q_min": self.q_min.text(),
            "q_max": self.q_max.text(),
            "q_num": self.q_num.text(),
            "r_min": self.r_min.text(),
            "r_max": self.r_max.text(),
            "r_num": self.r_num.text(),
            "nhermites_select": self.nhermites_select.currentText(),
            "nhermites_text": self.nhermites_text.text(),
            "self_term": self.self_term.text(),
            "is_chebyshev": self.is_chebyshev.isChecked(),
            "chebyshev_order": self.chebyshev_order.text(),
            "is_crystal": self.is_crystal.isChecked(),
            "is_lorch": self.is_lorch.isChecked(),
            "is_hermite_fitting": self.is_hermite_fitting.isChecked(),
            "is_instru": self.is_instru.isChecked(),
            "is_use": self.toggle_button.isChecked()
        }

    def set_config(self,config):
        """根据配置更新模块状态"""
        self.plot.setChecked(config.get("plot", False))
        self.q_min.setText(config.get("q_min", ""))
        self.q_max.setText(config.get("q_max", ""))
        self.q_num.setText(config.get("q_num", ""))
        self.r_min.setText(config.get("r_min", ""))
        self.r_max.setText(config.get("r_max", ""))
        self.r_num.setText(config.get("r_num", ""))
        self.nhermites_select.setCurrentText(config.get("nhermites_select", "Auto"))
        self.nhermites_text.setText(config.get("nhermites_text", ""))
        self.self_term.setText(config.get("self_term", "1"))
        self.is_chebyshev.setChecked(config.get("is_chebyshev", False))
        self.chebyshev_order.setText(config.get("chebyshev_order", "8"))
        self.is_crystal.setChecked(config.get("is_crystal", False))
        self.is_lorch.setChecked(config.get("is_lorch", False))
        self.is_hermite_fitting.setChecked(config.get("is_hermite_fitting", False))
        self.is_instru.setChecked(config.get("is_instru", False))
        self.toggle_button.setChecked(config.get("is_use", False))


class LoadThreadManager(QObject):
    finished = pyqtSignal()  # 任务完成信号
    error = pyqtSignal(str)  # 任务错误信号
    progress = pyqtSignal(int)  # 进度信号
    r_max= pyqtSignal(str) # r_max更新信号
    warning_info = pyqtSignal(str, str)

    def __init__(self, parent_widget):
        super().__init__()
        self.parent_widget = parent_widget
        self.is_running = True  # 标志位，控制线程是否继续运行

    def run(self):
        try:
            start_time = time.time()
            total_tasks = 9
            index = 0
            self.qmin, self.qmax, self.qnum = float(self.parent_widget.q_min.text()), float(self.parent_widget.q_max.text()), int(self.parent_widget.q_num.text())
            self.rmin, self.rmax, self.rnum = float(self.parent_widget.r_min.text()), float(self.parent_widget.r_max.text()), int(self.parent_widget.r_num.text())

            self.setup_hermite()
            data_hermite = self.get_data4Hermite()
            print(f"Setup and data preparation took {time.time() - start_time:.4f} seconds")
            index += 1
            progress = int(index / total_tasks * 100)
            self.progress.emit(progress)

            if not self.is_running:  # 检查标志位
                self.finished.emit()  # 任务完成，发送信号
                return

            # 是否做切比雪夫拟合
            if self.parent_widget.is_chebyshev.isChecked():
                start_time = time.time()
                print("start chebysev")
                data_hermite, background = self._apply_chebyshev_hermite(data_hermite)
                print(f"Chebyshev fitting took {time.time() - start_time:.4f} seconds")

            index += 1
            progress = int(index / total_tasks * 100)
            self.progress.emit(progress)
            if not self.is_running:  # 检查标志位
                self.finished.emit()  # 任务完成，发送信号
                return

            # 最小bank的q扩展到0
            start_time = time.time()
            print("start expand to zero")
            data_hermite = self._expand2zero(data_hermite)
            print(f"Expand to zero took {time.time() - start_time:.4f} seconds")

            index += 1
            progress = int(index / total_tasks * 100)
            self.progress.emit(progress)
            if not self.is_running:  # 检查标志位
                self.finished.emit()  # 任务完成，发送信号
                return

            # 是否晶体，做卷积
            if self.parent_widget.is_crystal.isChecked():
                start_time = time.time()
                print("start convolve box function")
                data_hermite = self._apply_box_function(data_hermite)
                print(f"Convolution with box function took {time.time() - start_time:.4f} seconds")

            index += 1
            progress = int(index / total_tasks * 100)
            self.progress.emit(progress)
            if not self.is_running:  # 检查标志位
                self.finished.emit()  # 任务完成，发送信号
                return

            # 是否做 lorch 过滤
            if self.parent_widget.is_lorch.isChecked():
                start_time = time.time()
                print("start lorch")
                data_hermite = self._apply_lorch(data_hermite)
                print(f"Lorch filtering took {time.time() - start_time:.4f} seconds")

            index += 1
            progress = int(index / total_tasks * 100)
            self.progress.emit(progress)
            if not self.is_running:  # 检查标志位
                self.finished.emit()  # 任务完成，发送信号
                return

            self.data_hermite = data_hermite

            if self.parent_widget.is_hermite_fitting.isChecked():
                start_time = time.time()
                print("create hermite")
                hermite_matrix_qiq = self._create_hermite_qiq(data_hermite)
                print(f"Hermite creation took {time.time() - start_time:.4f} seconds")

                index += 1
                progress = int(index / total_tasks * 100)
                self.progress.emit(progress)
                if not self.is_running:  # 检查标志位
                    self.finished.emit()  # 任务完成，发送信号
                    return

                # 是否卷积仪器参数
                if self.parent_widget.is_instru.isChecked():
                    start_time = time.time()
                    print("convolve instr res for hermite")
                    hermite_matrix_qiq = self._apply_instr_hermite(hermite_matrix_qiq, data_hermite)
                    print(f"Convolution with instrument response took {time.time() - start_time:.4f} seconds")

                index += 1
                progress = int(index / total_tasks * 100)
                self.progress.emit(progress)
                if not self.is_running:  # 检查标志位
                    self.finished.emit()  # 任务完成，发送信号
                    return

                start_time = time.time()
                coef = self._apply_hermite_fit(hermite_matrix_qiq, data_hermite)
                print(f"Hermite fitting took {time.time() - start_time:.4f} seconds")

                index += 1
                progress = int(index / total_tasks * 100)
                self.progress.emit(progress)
                if not self.is_running:  # 检查标志位
                    self.finished.emit()  # 任务完成，发送信号
                    return

                if coef is None:
                    return

                # 从拟合的hermite多项式构建pdf
                start_time = time.time()
                r, dr = self._reconstruct_pdf(coef)
                print(f"PDF reconstruction took {time.time() - start_time:.4f} seconds")

                pdf_data = {}
                pdf_data["name"] = "Hermite_" + "_".join(data_hermite["detector_order"])
                pdf_data["runno"] = self.unique_join(data_hermite["runno_list"])
                pdf_data["detector"] = "_".join(data_hermite["detector_order"])
                pdf_data["correction_info"] = []
                for corr in data_hermite["correction_info"]:
                    if corr == {} or corr in pdf_data["correction_info"]:
                        continue
                    else:
                        pdf_data["correction_info"].append(corr)
                correction_info = self._get_correction_info(pdf_data)
                pdf, pdf_type = self._transfer_pdf(r, dr, correction_info)
                pdf_data["pdf_data"] = [r, pdf]
                pdf_data["pdf_type"] = pdf_type

                self.parent_widget.parent.data_list.append(pdf_data)

                index += 1
                progress = int(index / total_tasks * 100)
                self.progress.emit(progress)
                if not self.is_running:  # 检查标志位
                    self.finished.emit()  # 任务完成，发送信号
                    return
            else:
                index += 4
                progress = int(index / total_tasks * 100)
                self.progress.emit(progress)

            self.finished.emit()  # 任务完成，发送信号
        except Exception as e:
            print(f"An error occurred: {e}")
            traceback.print_exc()  # 打印异常的堆栈跟踪

    def setup_hermite(self):
        if self.parent_widget.nhermites_select.currentText() == 'Auto':
            self.nh = int(np.round(self.rmax * self.qmax / 4))
        else:
            try:
                self.nh = int(self.parent_widget.nhermites_text.text())
            except:
                self.nh = 8
                self.parent_widget.nhermites_text.setText(str(self.nh))
        self.rmax = np.round(4 * self.nh / self.qmax)
        print(f"new rmax = {self.rmax}")
        self.r_max.emit(str(self.rmax))
        # self.r_max.setText(self.rmax)
        self.qp = np.sqrt(self.qmax / self.rmax)
        self.dr = (self.rmax -self.rmin) / self.rnum
        print(f"after setup for hermite: nh = {self.nh}")

    def get_data4Hermite(self):
        self.qstep = (self.qmax - self.qmin) / self.qnum
        print(f"qstep = {self.qstep}")
        data4Hermite = {}
        qdict = {}
        qiqdict = {}
        detector_list = []
        correction_info_list = []
        runno_list = []
        for data in self.parent_widget.parent.data_list:
            if "sq_data" in data:
                detector_name = data['detector']
                detector_list.append(detector_name)
                q,iq = data["sq_data"][0],data["sq_data"][1]
                # 根据qmin和qmax的设置来截掉两侧的范围外数据
                if q[-1] > self.qmax:
                    idx = np.where(q > self.qmax)[0][0]
                    q = q[:idx - 1]
                    iq = iq[:idx - 1]
                if q[0] < self.qmin:
                    idx = np.where(q < self.qmin)[0][0]
                    q = q[idx:]
                    iq = iq[idx:]

                #将q，iq插值为uniform分布状态
                step_sizes = np.diff(q)
                is_uniform = np.allclose(step_sizes, step_sizes[0], atol=1e-2)
                iterp = False
                if is_uniform:
                    if q[1] - q[0] < self.qstep:
                        iterp = True
                else:
                    iterp = True
                if iterp:
                    new_x = np.arange(q[0], q[-1] + self.qstep, self.qstep)
                    if iq.ndim == 1:
                        interpolator = interp1d(q, iq, kind='linear', fill_value="extrapolate")
                        new_y = interpolator(new_x)
                    else:
                        raise ValueError("y must be either 1D array.")
                    q = new_x
                    iq = new_y

                iq = iq - float(self.parent_widget.self_term.text())
                qiq = iq * q

                qdict[detector_name] = q
                qiqdict[detector_name] = qiq
                data["qiq_data"] = [qdict[detector_name],qiqdict[detector_name]]
                correction_info_list.append(data.get("correction_info",{}))
                runno_list.append(data.get("runno",""))
        data4Hermite["q"] = qdict
        data4Hermite["qiq"] = qiqdict
        data4Hermite["detector_order"] = detector_list
        data4Hermite["correction_info"] = correction_info_list
        data4Hermite["runno_list"] = runno_list
        return data4Hermite

    def update_data_list(self,data_hermite):
        for data in self.parent_widget.parent.data_list:
            if "sq_data" in data:
                detector_name = data['detector']
                data["qiq_data"] = [data_hermite["q"][detector_name],data_hermite["qiq"][detector_name]]

    def _apply_chebyshev_hermite(self,data_hermite):
        y_fit = {}
        for i in range(len(data_hermite["detector_order"])):
            detector_name = data_hermite["detector_order"][i]
            cheby, npuse = chebyshev(data_hermite["q"][detector_name],self.qmax,int(self.parent_widget.chebyshev_order.text()))
            data_hermite["qiq"][detector_name], y_fit[detector_name] = fit_chebyshev(
                                            data_hermite["q"][detector_name],
                                            data_hermite["qiq"][detector_name],
                                            self.qmin, cheby)
            # print(data_hermite["qiq"][detector_name].shape, y_fit[detector_name].shape)
            print(f"chebyshev order (calculated from fitting order) = {npuse} for {detector_name}")
            self.update_data_list(data_hermite)
        return data_hermite, y_fit

    def _expand2zero(self, data_hermite):
        detector_name = data_hermite["detector_order"][0]
        new_q, new_qiq = data_expansion(data_hermite["q"][detector_name], data_hermite["qiq"][detector_name])
        data_hermite["q"][detector_name] = new_q
        data_hermite["qiq"][detector_name] = new_qiq
        self.update_data_list(data_hermite)
        return data_hermite

    def _apply_box_function(self, data_hermite):
        for i in range(len(data_hermite["detector_order"])):
            detector_name = data_hermite["detector_order"][i]
            data_hermite["qiq"][detector_name] = convolve_box_function(self.rmax, data_hermite["q"][detector_name],
                                                                       data_hermite["qiq"][detector_name])
            self.update_data_list(data_hermite)
        return data_hermite

    def _apply_lorch(self, data_hermite):
        for i in range(len(data_hermite["detector_order"])):
            detector_name = data_hermite["detector_order"][i]
            data_hermite["qiq"][detector_name] = lorch_filter(data_hermite["q"][detector_name], self.qmax,
                                                              data_hermite["qiq"][detector_name])
            self.update_data_list(data_hermite)
        return data_hermite

    def _create_hermite_qiq(self, data_hermite):
        hermite_matrix_qiq = {}
        for i in range(len(data_hermite["detector_order"])):
            detector_name = data_hermite["detector_order"][i]
            q = data_hermite["q"][detector_name]
            new_xh = np.zeros((len(q), self.nh))
            x = q / self.qp
            for ih in range(1, self.nh + 1):
                k = 2 * ih - 1
                new_xh[:, ih - 1] = fockstate(k, x)
            hermite_matrix_qiq[detector_name] = new_xh
        return hermite_matrix_qiq

    def _apply_instr_hermite(self, hermite_matrix, data_hermite):
        for i in range(len(data_hermite["detector_order"])):
            detector_name = data_hermite["detector_order"][i]
            group_name, _ = get_all_from_detector(detector_name,
                                                  self.parent_widget.parent.config['base']["group_info"],
                                                  self.parent_widget.parent.config['base']["bank_info"])
            hermite_matrix[detector_name] = convolve_instr_hermite_parallel(
                self.parent_widget.parent.config['base']["resolution_information"][group_name]["a"],
                self.parent_widget.parent.config['base']["resolution_information"][group_name]["c"],
                hermite_matrix[detector_name], self.nh, data_hermite["q"][detector_name])
        return hermite_matrix

    def _apply_hermite_fit(self, hermite_matrix, data_hermite):
        qiq_val = []
        h_val = []
        for i in range(len(data_hermite["detector_order"])):
            detector_name = data_hermite["detector_order"][i]
            qiq_val.append(data_hermite["qiq"][detector_name])
            h_val.append(hermite_matrix[detector_name])
        merge_qiq = np.concatenate(qiq_val, axis=0)
        merge_hermite = np.concatenate(h_val, axis=0)
        coef = np.linalg.lstsq(merge_hermite, merge_qiq, rcond=None)[0]
        if np.any(np.isnan(coef)):
            print("can't fit, there is nan, please check your data")
            return None
        else:
            return coef

    def _reconstruct_pdf(self, coef):
        xxx = np.arange(self.dr, self.qmax, self.dr) / self.qp
        hermite_matrix_dr = np.zeros((len(xxx), self.nh))
        for ih in range(self.nh):
            k = 2 * ih + 1
            hermite_matrix_dr[:, ih] = fockstate(k, xxx)
        data = np.zeros_like(xxx)
        for ih in range(self.nh):
            data += (-1) ** ih * coef[ih] * hermite_matrix_dr[:, ih]
        data *= self.qp * np.sqrt(2 / np.pi)
        # if self.conf["lorch"]:
        #     data = lorch_filter(xxx/self.qp,self.conf["r_rebin"][1],data)
        return xxx / self.qp, data

    def _transfer_pdf(self, r, dr, correction_info):
        if correction_info != {} and "density_num" in correction_info and "scale" in correction_info:
            rho0 = correction_info["density_num"] * correction_info["scale"]
        else:
            rho0 = None
        if self.parent_widget.data_mode.currentText() == "G(r)":
            return dr, "Gr"
        elif self.parent_widget.data_mode.currentText() == "g(r)":
            if rho0 is not None:
                return dr / (4 * np.pi * r * rho0) + 1, "gr"
            else:
                return dr, "Gr"
        elif self.parent_widget.data_mode.currentText() == "RDF":
            if rho0 is not None:
                return r * dr + 4 * np.pi * rho0 * r ** 2, "RDF"
            else:
                return dr, "Gr"
        else:
            raise ValueError("PDF_type must be one of 'G(r)', 'g(r)', 'RDF'")


    def _get_correction_info(self,data):
        # 拿第一个字典作为基准
        try:
            first_corr = data["correction_info"][0]
        except:
            self.warning_info.emit("warning","The correction info is not exist, so you only can get the G(r), can't get the g(r) and RDF.")
            return {}
        # 检查所有字典是否都与第一个字典相同
        judge = all(corr == first_corr for corr in data["correction_info"])
        if not judge:
            self.warning_info.emit("warning", "The correction info from the data used to fitting are different, the first would be selected as the correct one.")
        return first_corr

    def unique_join(self, strings: List[str], sep: str = "_", ignore_case: bool = False, sort_result: bool = False) -> str:
        """
        从字符串列表中挑选不同的字符串，用下划线（或自定义分隔符）拼接后返回。
        
        参数:
            strings: 输入字符串列表
            sep: 拼接用分隔符，默认 "_"
            ignore_case: 是否忽略大小写进行去重，默认 False
            sort_result: 是否对去重后的结果排序（按字母序）。
                        若为 True，则在保留“首次出现的原样”的前提下排序。
        
        返回:
            去重并拼接后的字符串
        """
        seen = set()
        out = []
        for s in strings:
            key = s.casefold() if ignore_case else s
            if key not in seen:
                seen.add(key)
                out.append(s)
        if sort_result:
            out = sorted(out, key=(str.casefold if ignore_case else None))
        return sep.join(out)
    
    def show_error_message(self, message):
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Critical)
        msg.setWindowTitle("Input Error")
        msg.setText(message)
        msg.setStandardButtons(QMessageBox.Ok)
        msg.exec_()  # Show the message box

    def stop(self):
        """停止线程"""
        self.is_running = False

class ProgressDialog(QDialog):
    def __init__(self, thread, parent_widget, parent=None):
        super().__init__(parent)
        self.thread = thread
        self.parent_widget = parent_widget

        # 设置窗口标题
        self.setWindowTitle("Progress")

        # 创建布局
        layout = QVBoxLayout()

        # 添加进度条
        self.progress_bar = QProgressBar(self)
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        layout.addWidget(self.progress_bar)

        # 设置布局
        self.setLayout(layout)

    def closeEvent(self, event):
        """重写关闭事件，确保线程停止"""
        self.parent_widget.worker.stop()  # 停止线程
        if self.thread.isRunning():
            self.thread.quit()  # 请求线程退出
            self.thread.wait()  # 等待线程完全退出
        event.accept()

