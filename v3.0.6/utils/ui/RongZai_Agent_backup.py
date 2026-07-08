from PyQt5 import QtWidgets, QtCore
import re
import traceback,copy
from utils.ui.BaseUI import CollapsibleWidget
from utils.browse import browse
from matplotlib.backends.backend_qt5agg import (
    FigureCanvasQTAgg as FigureCanvas,
    NavigationToolbar2QT as NavigationToolbar
)
from matplotlib.figure import Figure
from scipy.interpolate import interp1d
import numpy as np
import os
from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtGui import QDesktopServices
from PyQt5.QtCore import QUrl
import posixpath
import tempfile
from rongzai.dataSvc.diffraction_format import DiffractionFormat
from rongzai.utils import get_all_from_detector
import json


class RongZai_Agent(CollapsibleWidget):
    def __init__(self, name, parent):
        super(RongZai_Agent, self).__init__(name, "utils/ui/RongZai_Agent.ui", parent)
        self.parent = parent
        # 初始化数据加载
        self.browse_run = browse()
        self.load_pattern_button.clicked.connect(self._on_load_pattern_clicked)
        # 设置Matplotlib图形
        self.figure = Figure()
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setStyleSheet("background-color: transparent;")
        # 配置工具栏
        self.toolbar = NavigationToolbar(self.canvas, self)
        self.toolbar.setIconSize(QtCore.QSize(16, 16))
        # 设置布局
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.canvas)
        layout.addWidget(self.toolbar)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.graphicsView.setLayout(layout)

        #初始化RongZai Agent
        self.selected_cif_files = []
        self.load_cif_button.clicked.connect(self._on_load_cif_clicked)
        self.selected_reduced_data = {}
        self.open_agent_button.clicked.connect(self._on_open_agent_clicked)
        self.server_host = self.parent.config['base']["rongzai_agent_config"]["server_host"]
        self.server_port = self.parent.config['base']["rongzai_agent_config"]["server_port"]
        self.server_username = self.parent.config['base']["rongzai_agent_config"]["server_username"]
        self.server_password = self.parent.config['base']["rongzai_agent_config"]["server_passward"]
        self.remote_reduced_dir = self.parent.config['base']["rongzai_agent_config"]["remote_reduced_dir"]
        self.remote_cif_dir = self.parent.config['base']["rongzai_agent_config"]["remote_cif_dir"]
        self.web_url = self.parent.config['base']["rongzai_agent_config"]["web_url"]

    def get_config(self):
        return {
            "is_use": self.toggle_button.isChecked()
        }

    def set_config(self,config):
        """根据配置更新模块状态"""
        self.toggle_button.setChecked(config.get("is_use", False))

    def _on_load_pattern_clicked(self):
        """处理样品加载按钮点击"""
        try:
            # 执行前置模块
            data_list_backup = copy.deepcopy(self.parent.data_list)
            self._run_previous_modules()
            dataList_for_browse = []
            for data in self.parent.data_list:
                if data["record"].get("division"):
                    dataList_for_browse.append(data['name'])
            self.browse_run.select_utils(self.load_pattern_text,dataList_for_browse)
            self.compute_figure()
            self.parent.data_list = data_list_backup
        except Exception as e:
            print(f'Reason: {e}')
            traceback.print_exc()  # 打印异常的堆栈跟踪

    def _on_load_cif_clicked(self):
        try:
            options = QtWidgets.QFileDialog.Options()
            files, _ = QtWidgets.QFileDialog.getOpenFileNames(
                self,
                "Select CIF Files",
                "",
                "CIF Files (*.cif);;All Files (*)",
                options=options
            )
            if not files:
                return

            # 方式1：把完整路径放入 lineEdit（推荐，便于后续读取）
            # self.load_cif_text.setText("; ".join(files))

            # 如仅想显示文件名而非完整路径，改用下面这行：
            self.load_cif_text.setText("; ".join(os.path.basename(p) for p in files))

            # 可选：把文件列表保存起来，后续处理用
            self.selected_cif_files = files

            # 可选：长文本时将光标移到开头，避免只看到末尾
            self.load_cif_text.setCursorPosition(0)
        except Exception as e:
            print(f'Reason: {e}')
            traceback.print_exc()  # 打印异常的堆栈跟踪

    def _on_open_agent_clicked(self):
        btn = self.open_agent_button  # 你的按钮对象名称
        orig_text = btn.text()

        # 禁用按钮并提示进行中
        btn.setEnabled(False)
        btn.setText("Please wait")
        QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
        QtWidgets.QApplication.processEvents()  # 立即刷新界面

        # 执行前置模块
        data_list_backup = copy.deepcopy(self.parent.data_list)
        self._run_previous_modules()

        try:
            # 原有检查逻辑
            raw_text = (self.load_pattern_text.text() or "").strip()
            sam_list = [s.strip() for s in raw_text.split(";") if s.strip()]
            if not sam_list:
                QMessageBox.warning(self, "warning", "please select the data for AI analysis!")
                return

            # 执行任务
            self.send_reduced_data()
            self.send_exp_dicts()
            self.send_cif(self.selected_cif_files)
            self.open_http()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"执行失败：{e}")
        finally:
            # 恢复按钮与光标
            QtWidgets.QApplication.restoreOverrideCursor()
            btn.setText(orig_text)
            btn.setEnabled(True)
            self.parent.data_list = data_list_backup

    def compute_figure(self):
        """计算并更新图形（包含清除旧标记）"""
        try:
            # 清除所有图形元素
            self.figure.clear()

            # 初始化新图形
            ax = self.figure.add_subplot(111)
            ax.set_navigate(True)
            self.ax = ax  # 保存ax引用供后续使用

            # 获取数据
            sam_list = [s for s in self.load_pattern_text.text().split('; ') if s]
            data_dict = {item['name']: item for item in self.parent.data_list}

            if sam_list:
                # 绘制数据曲线并保存颜色信息
                self._plot_data(ax, sam_list, data_dict)
            else:
                ax.text(0.5, 0.5, "No valid data",
                        fontsize=8, ha='center', va='center',
                        transform=ax.transAxes)

            # 图形样式设置
            ax.tick_params(axis='both', which='major', labelsize=6, pad=1)
            for spine in ax.spines.values():
                spine.set_linewidth(0.5)

            self.figure.tight_layout(pad=0.5)
            self.figure.subplots_adjust(
                left=0.1, right=0.98,
                bottom=0.1, top=0.95
            )

            self.canvas.draw()
        except Exception as e:
            self._show_error_message(str(e))

    def _open_sftp(self):
        """
        打开到服务器的 SFTP 连接（使用账号密码，避免任何交互认证）
        需要事先在 self 上配置：
            self.server_host, self.server_port, self.server_username, self.server_password
        """
        try:
            import paramiko
        except ImportError:
            QMessageBox.critical(self, "Error", "缺少依赖：请先安装 paramiko（pip install paramiko）")
            raise

        if not all([
            getattr(self, "server_host", None),
            getattr(self, "server_port", 22) is not None,
            getattr(self, "server_username", None),
            getattr(self, "server_password", None),
        ]):
            QMessageBox.critical(self, "Error", "服务器配置不完整：请设置 server_host/port/username/password")
            raise RuntimeError("server config missing")

        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())  # 自动接受服务器指纹，避免确认弹窗
        ssh.connect(
            hostname=self.server_host,
            port=int(getattr(self, "server_port", 22)),
            username=self.server_username,
            password=self.server_password,
            timeout=20,
        )
        sftp = ssh.open_sftp()
        return ssh, sftp

    def _sftp_mkdirs(self, sftp, remote_dir):
        """
        递归创建远端目录（若已存在则忽略）
        使用 posix 路径，确保在 Linux 服务器上正常
        """
        if not remote_dir or remote_dir == "/":
            return
        parts = remote_dir.strip("/").split("/")
        path = ""
        for p in parts:
            path = "/" + p if path == "" else posixpath.join(path, p)
            try:
                sftp.listdir(path)
            except IOError:
                sftp.mkdir(path)

    def get_exp_dicts(self):
        raw_text = (self.load_pattern_text.text() or "").strip()
        sam_list = [s.strip() for s in raw_text.split(";") if s.strip()]
        data_dict = {item["name"]: item for item in self.parent.data_list}
        not_found = []
        exp_dicts = {}
        exp_dict = {
            "beamline": "",
            "sample_run": [],
            "v_run":[],
            "sampleBG_run":[],
            "vBG_run":[],
            "sample_correction":[],
            "wave_min": 0.0,
            "wave_max": 0.0,
            "start_time":"unknown",
            "end_time":"unknown"
        }
        for sam in sam_list:
            if sam not in data_dict:
                not_found.append(sam)
                continue
            runno = data_dict[sam]["runno"]
            if runno not in exp_dicts.keys():
                exp_dicts[runno] = exp_dict.copy()
                exp_dicts[runno]["beamline"] = self.parent.config["base"]["beamline"]
                exp_dicts[runno]["sample_run"] = runno.split("_")
                if "division" in data_dict[sam]["record"]:
                    exp_dicts[runno]["v_run"] = self.get_runno_from_name(data_dict[sam]["record"]["division"]).split("_")
                if "subtraction_self" in data_dict[sam]["record"]:
                    exp_dicts[runno]["sampleBG_run"] = self.get_runno_from_name(data_dict[sam]["record"]["subtraction_self"]).split("_")
                if "subtraction_v" in data_dict[sam]["record"]:
                    exp_dicts[runno]["vBG_run"] = self.get_runno_from_name(data_dict[sam]["record"]["subtraction_v"]).split("_")
                if "carpenterCorrection" in data_dict[sam]["record"]:
                    exp_dicts[runno]["sample_correction"] = data_dict[sam]["record"]["carpenterCorrection"]
                if "crop" in data_dict[sam]["record"]:
                    exp_dicts[runno]["wave_min"] = float(data_dict[sam]["record"]["crop"].split("_")[0])
                    exp_dicts[runno]["wave_max"] = float(data_dict[sam]["record"]["crop"].split("_")[1])
                else:
                    exp_dicts[runno]["wave_min"] = self.parent.config["base"]["wave_min"]
                    exp_dicts[runno]["wave_max"] = self.parent.config["base"]["wave_max"]
        return exp_dicts

    def send_exp_dicts(self):
        """
        生成并上传实验描述 JSON：
          - 从 get_exp_dicts() 获取 {runno: exp_dict}
          - 为每个 runno 生成文件名为 f"{beamline}_diffraction.json" 的 JSON
          - 远端路径：<remote_reduced_dir>/<runno>/<beamline>_diffraction.json
          - 与 send_reduced_data 一致，使用 SFTP 上传，确保远端目录存在
        """

        # 1) 校验远端目录配置
        if not getattr(self, "remote_reduced_dir", None):
            QMessageBox.critical(self, "Error", "未配置 remote_reduced_dir（远端上传目录）")
            return

        # 2) 获取 runno->exp_dict
        try:
            exp_dicts = self.get_exp_dicts()
        except Exception as e:
            QMessageBox.warning(self, "Warning", f"实验信息获取失败：{e}")
            return
        if not exp_dicts:
            QMessageBox.warning(self, "Warning", "没有可发送的实验信息（exp_dicts 为空）")
            return

        # 3) 打开 SFTP
        try:
            ssh, sftp = self._open_sftp()
        except Exception as e:
            QMessageBox.critical(self, "SFTP Error", f"无法连接 SFTP：\n{e}")
            return

        uploaded = 0
        failed = []

        # 4) 生成本地临时文件并上传
        with tempfile.TemporaryDirectory(prefix="rz_expjson_") as tmp_root:
            for runno, info in exp_dicts.items():
                try:
                    # beamline 名称优先使用 exp 字段，否则回退到配置
                    bl = (info.get("beamline")
                          or self.parent.config["base"].get("beamline_name")
                          or self.parent.config["base"].get("beamline")
                          or "beamline")
                    # 安全文件名
                    safe_bl = re.sub(r'[^A-Za-z0-9_.-]+', '_', str(bl).strip() or "beamline")
                    json_name = f"{safe_bl}_diffraction.json"

                    # 本地临时目录
                    local_run_dir = os.path.join(tmp_root, runno)
                    os.makedirs(local_run_dir, exist_ok=True)
                    local_json = os.path.join(local_run_dir, json_name)

                    # 写 JSON（确保可序列化）
                    def _default(o):
                        try:
                            import numpy as np
                            if isinstance(o, (np.generic,)):
                                return o.item()
                            if hasattr(o, "tolist"):
                                return o.tolist()
                        except Exception:
                            pass
                        return str(o)

                    with open(local_json, "w", encoding="utf-8") as f:
                        json.dump(info, f, ensure_ascii=False, indent=2, default=_default)

                    # 远端目录与上传
                    remote_run_dir = posixpath.join(self.remote_reduced_dir, runno)
                    self._sftp_mkdirs(sftp, remote_run_dir)
                    remote_json = posixpath.join(remote_run_dir, json_name)
                    sftp.put(local_json, remote_json)
                    uploaded += 1
                except Exception as ex_item:
                    failed.append(f"{runno}: {ex_item}")

        # 5) 关闭连接
        try:
            sftp.close()
            ssh.close()
        except Exception:
            pass

        # 6) 汇报
        msg = [f"实验 JSON 上传完成！共上传 {uploaded} 个文件。"]
        if failed:
            msg.append(f"失败 {len(failed)} 项：\n" + "\n".join(failed))
        QMessageBox.information(self, "Done", "\n\n".join(msg))

    def send_reduced_data(self):
        """
        将指定格式的数据保存到远端目录：
          远端结构：<remote_reduced_dir>/<runno>/...
        每个样本各放在其 runno 子目录下，文件包括：
          - I-d:   <name_无冒号>_<detector>.txt
          - GSAS:  <runno>_<detector>.gsa
          - Igor:  <runno>_<detector>.histogramIgor
          - FullProf: <runno>_<detector>.dat
        说明：
          - 先写到本地临时目录，再通过 SFTP 上传，避免远端路径作为本地路径导致失败。
          - 需要 self.remote_reduced_dir，self._open_sftp(self)，self._sftp_mkdirs(self, sftp, remote_dir)
        """
        if not getattr(self, "remote_reduced_dir", None):
            QMessageBox.critical(self, "Error", "未配置 remote_reduced_dir（远端上传目录）")
            return

        # 从行编辑读取选择列表；按你现有的分隔符拆分，容错去空白
        raw_text = (self.load_pattern_text.text() or "").strip()
        sam_list = [s.strip() for s in raw_text.split(";") if s.strip()]
        if not sam_list:
            QMessageBox.warning(self, "Warning", "没有可发送的实验数据（未选择样本）")
            return

        # 构建 name -> data 的索引，方便取数
        try:
            data_dict = {item["name"]: item for item in self.parent.data_list}
        except Exception:
            QMessageBox.critical(self, "Error", "data_list 结构异常，无法构建样本索引")
            return

        # 打开 SFTP 连接
        try:
            ssh, sftp = self._open_sftp()
        except Exception:
            return

        uploaded_total = 0
        not_found = []
        failed = []

        # 用临时目录承载所有待上传的本地文件
        with tempfile.TemporaryDirectory(prefix="rz_upload_") as tmp_root:
            try:
                for sam in sam_list:
                    if sam not in data_dict:
                        not_found.append(sam)
                        continue
                    item = data_dict[sam]

                    try:
                        # 1) 计算 runno
                        runno = self.get_runno_from_name(item["name"])
                        if "time_slice" in item:
                            runno = f"{runno}_{item['time_slice']}"
                        # datatype = self.get_datatype_from_name(item["name"])
                        # if datatype:
                        #     runno = f"{datatype}_{runno}"

                        # 2) 计算探测器组名
                        groupname, _ = get_all_from_detector(
                            item["detector"],
                            self.parent.config["base"]["group_info"],
                            self.parent.config["base"]["bank_info"]
                        )

                        # 3) 本地 runno 目录（临时）
                        local_run_dir = os.path.join(tmp_root, runno)
                        os.makedirs(local_run_dir, exist_ok=True)

                        # 4) 生成 I-d 文本（清洗后的文件名，移除单引号等）
                        # name_clean = self._sanitize_filename(item["name"])
                        # det_clean = self._sanitize_filename(item["detector"])
                        # fn_id = os.path.join(local_run_dir, f"{name_clean}_{det_clean}.txt")
                        # x = item["detector_focused"]["xvalue"].values[0]
                        # y = item["detector_focused"]["histogram"].values[0]
                        # e = item["detector_focused"]["error"].values[0]
                        # write_ascii(fn_id, x, y, e)

                        # 5) 生成 refine 数据（GSAS / Igor / FullProf）
                        difa = self.parent.config["base"]["focus_point"][groupname]["DIFA"]
                        difb = self.parent.config["base"]["focus_point"][groupname]["DIFB"]
                        difc = self.parent.config["base"]["focus_point"][groupname]["DIFC"]
                        zero = self.parent.config["base"]["focus_point"][groupname]["ZERO"]

                        base_out = os.path.join(local_run_dir, f"{runno}_{item['detector']}")
                        output = DiffractionFormat(
                            item["detector_focused"],
                            runno,
                            item["detector"],
                            self.parent.config["base"]["beamline_name"],
                            difa, difb, difc, zero
                        )
                        output.writeGSAS_psd(base_out + ".gsa")
                        output.writeZR(base_out + ".histogramIgor")
                        output.writeFP(
                            base_out + ".dat",
                            self.parent.config["base"]["multiply_factor_fullprof"],
                            self.parent.config["base"]["focus_point"][groupname]["2_theta"]
                        )

                        # 6) 确保远端 runno 目录存在
                        remote_run_dir = posixpath.join(self.remote_reduced_dir, runno)
                        self._sftp_mkdirs(sftp, remote_run_dir)

                        # 7) 上传本地 runno 目录下的所有文件（单层）
                        for fname in os.listdir(local_run_dir):
                            lp = os.path.join(local_run_dir, fname)
                            if not os.path.isfile(lp):
                                continue
                            rp = posixpath.join(remote_run_dir, fname)
                            sftp.put(lp, rp)
                            uploaded_total += 1

                    except Exception as ex_item:
                        failed.append(f"{sam}: {ex_item}")

            except Exception as ex_all:
                QMessageBox.critical(self, "Upload Error", f"处理/上传过程中发生错误：\n{ex_all}")
                try:
                    sftp.close()
                    ssh.close()
                except Exception:
                    pass
                return

        # 关闭 SFTP 连接
        try:
            sftp.close()
            ssh.close()
        except Exception:
            pass

        # 汇报结果
        msg_lines = [f"实验数据上传完成!"]
        if not_found:
            msg_lines.append(f"未找到样本：{len(not_found)} 个\n" + "; ".join(not_found))
        if failed:
            msg_lines.append(f"处理失败：{len(failed)} 项\n" + "\n".join(failed))
        QMessageBox.information(self, "Done", "\n\n".join(msg_lines))

    def send_cif(self, cif_files):
        """
		将选中的 CIF 文件全部上传到 self.remote_cif_dir 目录
		"""

        if not getattr(self, "remote_cif_dir", None):
            QMessageBox.critical(self, "Error", "未配置 remote_cif_dir（远端 CIF 上传目录）")
            return
        files = [p for p in (cif_files or []) if os.path.isfile(p)]
        if not files:
            QMessageBox.warning(self, "Warning", "所选 CIF 文件不存在或无效")
            return
        try:
            ssh, sftp = self._open_sftp()
        except Exception:
            return
        uploaded = 0
        failed = []
        try:
            # 确保远端目录存在
            self._sftp_mkdirs(sftp, self.remote_cif_dir)

            for local_path in files:
                base = os.path.basename(local_path)
                remote_path = posixpath.join(self.remote_cif_dir, base)
                try:
                    sftp.put(local_path, remote_path)
                    uploaded += 1
                except Exception as e_put:
                    failed.append(f"{base} -> {e_put}")

            msgs = [f"CIF 上传完成：{uploaded} 个文件"]
            if failed:
                msgs.append(f"失败：{len(failed)} 项\n" + "\n".join(failed))
            QMessageBox.information(self, "Done", "\n\n".join(msgs))
        except Exception as e:
            QMessageBox.critical(self, "Upload Error", f"上传 CIF 失败：\n{e}")
        finally:
            try:
                sftp.close()
                ssh.close()
            except Exception:
                pass

    def open_http(self):
        """
        使用系统默认浏览器打开指定网址
        需要配置：self.web_url
        """
        url = getattr(self, "web_url", None)
        if not url:
            QMessageBox.warning(self, "Warning", "未配置 web_url")
            return
        QDesktopServices.openUrl(QUrl(url))


    def _show_error_message(self, message):
        """显示错误信息"""
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        ax.text(0.5, 0.5, f"Error: {message}",
                fontsize=8, ha='center', va='center',
                transform=ax.transAxes)
        self.canvas.draw()

    def _plot_data(self, ax, sam_list, data_dict):
        """绘制数据曲线并添加图例"""
        lines = []  # 存储所有线条对象
        labels = []  # 存储对应标签
        self.line_colors = {}

        for sam in sam_list:
            try:
                # 绘制曲线并保存引用
                x = data_dict[sam]["detector_focused"]["xvalue"].values[0]
                y = data_dict[sam]["detector_focused"]["histogram"].values[0]
                line, = ax.plot(x, y, linestyle='-', linewidth=2)

                # 添加图例标签
                lines.append(line)
                labels.append(f"{sam}")
                self.line_colors[sam] = line.get_color()


            except Exception as e:
                print(f"Error processing {sam}: {e}")
                traceback.print_exc()

        # 添加图例（仅在有多条曲线时）
        if len(lines) > 1:
            legend = ax.legend(
                lines,
                labels,
                loc='upper right',
                fontsize=6,  # 与坐标轴标签大小一致
                framealpha=0.5,
                handlelength=1.5,
                handletextpad=0.5,
                borderaxespad=0.5
            )
            # 设置图例边框线条宽度
            legend.get_frame().set_linewidth(0.5)

            # 调整布局避免图例遮挡
            self.figure.subplots_adjust(right=0.85)  # 为图例留出空间

        self.y_min_origin, y_max = self.ax.get_ylim()

    def reorganize_data(self,x,y,d_range):
        interp = interp1d(x, y, kind='linear', bounds_error=False, fill_value=0)
        I_interp = interp(d_range)
        I_interp /= np.max(I_interp)
        return I_interp

    def _run_previous_modules(self):
        """运行前置模块"""
        current_name = self.objectName()
        for i in range(self.parent.inner_layout.count()):
            module = self.parent.inner_layout.itemAt(i).widget()
            if module.objectName() == current_name:
                break
            if hasattr(module, 'run'):
                module.run()


    def get_runno_from_name(self, name):
        # 使用正则表达式匹配所有 RUN 后跟数字的字符串
        run_pattern = re.compile(r'RUN\d+')
        runnos = run_pattern.findall(name)

        # 检查是否有匹配的运行号
        if not runnos:
            return "unknown"

        # 将所有运行号用下划线连接成一个字符串
        combined_runno = '_'.join(runnos)
        return combined_runno

    def get_datatype_from_name(self, name):
        # 定义正则表达式模式
        pattern = re.compile(r'samBG|sam|vBG|v')

        # 搜索匹配
        match = pattern.search(name)

        if match:
            print(f"Matched: {match.group()}")  # 调试输出
            return match.group()
        else:
            print("Nothing matched")  # 调试输出
            return False

    def _sanitize_filename(self, s: str) -> str:
        """
        清洗文件名：去掉引号、冒号等非法字符，空白转为下划线
        """
        s = str(s)
        # 去掉最常见的引号与冒号
        s = s.replace("'", "").replace('"', "").replace(":", "")
        # 去掉 Windows 非法字符，避免跨平台问题
        s = re.sub(r'[\\\/:*?\<\>\|]', "", s)
        # 把连续空白替换为下划线，并去掉首尾下划线
        s = re.sub(r"\s+", "_", s).strip("_")
        return s

    def _normalize_runno(self, raw: str) -> str:
        """
        规范化 runno，提取形如 RUN1234567 的段落，去掉任何前缀（如 sam_）
        若未匹配到，返回原值的大写。
        """
        m = re.search(r"(RUN\d+)", str(raw).upper())
        return m.group(1) if m else str(raw).upper()
