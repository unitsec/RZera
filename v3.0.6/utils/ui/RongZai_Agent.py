from PyQt5 import QtWidgets
import re
import traceback,copy
from utils.ui.BaseUI import CollapsibleWidget
from utils.browse import browse
import numpy as np
import os
from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtGui import QDesktopServices
from PyQt5.QtCore import QUrl, QEventLoop
import posixpath
import tempfile
from rongzai.dataSvc.diffraction_format import DiffractionFormat
from rongzai.utils import get_all_from_detector
from rongzai.dataSvc import write_rmc
import json


class RongZai_Agent(CollapsibleWidget):
    def __init__(self, name, parent):
        super(RongZai_Agent, self).__init__(name, "utils/ui/RongZai_Agent.ui", parent)
        self.parent = parent

        #初始化RongZai Agent 接口
        self.server_host = self.parent.config['base']["rongzai_agent_config"]["server_host"]
        self.server_port = self.parent.config['base']["rongzai_agent_config"]["server_port"]
        self.remote_reduced_dir = self.parent.config['base']["rongzai_agent_config"]["remote_reduced_dir"]
        self.web_url = self.parent.config['base']["rongzai_agent_config"]["web_url"]

        try:
            self.server_username = self.parent.config['base']["rongzai_agent_config"]["server_username"]
            
        except:
            self.server_username = "dur"

        try:
            self.server_password = self.parent.config['base']["rongzai_agent_config"]["server_password"]
        except:
            self.server_password = "kobedu824"
        
        # 初始化数据加载
        self.browse_run = browse()
        self.selected_cif_files = []
        self.load_cif_button.clicked.connect(self._on_load_cif_clicked)
        self.open_agent_button.clicked.connect(self._on_open_agent)
        self.download_button.clicked.connect(self.download)
        self.selected_reduced_data = {}
        # 记录本次上传涉及的 runno，供下载阶段直接使用
        self.last_uploaded_runnos = []

    def _on_open_agent(self):
        data_list_backup = copy.deepcopy(self.parent.data_list)
        try:
            self.state_label.setText("Please Wait ...")
            # 发送必须的数据
            self._run_previous_modules()
            data_names = self.send_reduced_data()
            self.send_exp_dicts(data_names)
            self.send_cif(self.selected_cif_files)
            # 打开网页
            self.open_http()
            self.state_label.setText("Ready")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"执行失败：{e}")
        finally:
            # Agent 上传流程只应使用临时计算结果，结束后恢复原始数据，避免影响后续 Run。
            self.parent.data_list = data_list_backup
            self.state_label.setText("Ready")

    def download(self):
        """下载远程精修后文件到本地"""
        try:
            self.state_label.setText("Please Wait ...")
            local_dir = QtWidgets.QFileDialog.getExistingDirectory(
                self,
                "Select Local Directory to Save CIF Files",
                ""
            )
            if not local_dir:
                return

            # 使用上传时记录的 runno
            runnos = set(self.last_uploaded_runnos or [])
            if runnos:
                ssh, sftp = self._open_sftp()
                downloaded = 0
                missing = []
                for runno in sorted(runnos):
                    remote_run_dir = posixpath.join(self.remote_reduced_dir, runno)
                    try:
                        remote_files = sftp.listdir(remote_run_dir)
                    except Exception:
                        missing.append(f"{runno} (远端目录不存在)")
                        continue

                    local_run_dir = os.path.join(local_dir, runno)
                    os.makedirs(local_run_dir, exist_ok=True)

                    for fname in remote_files:
                        if not fname.lower().endswith((".gpx", ".cif")):
                            continue
                        remote_path = posixpath.join(remote_run_dir, fname)
                        local_path = os.path.join(local_run_dir, fname)
                        sftp.get(remote_path, local_path)
                        downloaded += 1
                sftp.close()
                ssh.close()
                msg = [f"已下载文件数: {downloaded}", f"保存到: {local_dir}"]
                if missing:
                    msg.append("未找到的 runno 目录:\n" + "\n".join(missing))
                QMessageBox.information(self, "Done", "\n".join(msg))
            else:
                QMessageBox.information(self, "Info", "没有可下载的 runno 信息（请先上传数据）")
            self.state_label.setText("Ready")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"下载 CIF 文件失败：{e}")

    def get_config(self):
        return {
            "is_use": self.toggle_button.isChecked(),
            "cif_files": self.selected_cif_files,
            "user_name": self.user_name_text.text(),
            "institute": self.institute_text.text()
        }

    def set_config(self,config):
        """根据配置更新模块状态"""
        self.toggle_button.setChecked(config.get("is_use", False))
        self.selected_cif_files = config.get("cif_files", [])
        self.load_cif_text.setText("; ".join(os.path.basename(p) for p in self.selected_cif_files))
        self.user_name_text.setText(config.get("user_name", ""))
        self.institute_text.setText(config.get("institute", ""))

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

        # 保护性地规范类型，避免从配置中读取到 tuple/list 导致 Paramiko 报错
        host = getattr(self, "server_host", None)
        if isinstance(host, (list, tuple)):
            host = host[0]
        port = getattr(self, "server_port", 22)
        if isinstance(port, (list, tuple)):
            port = port[0]
        username = getattr(self, "server_username", None)
        if isinstance(username, (list, tuple)):
            username = username[0]
        password = getattr(self, "server_password", None)
        if isinstance(password, (list, tuple)):
            password = password[0]

        # 转换为期望类型并做最小验证
        if host is None:
            raise RuntimeError("server_host 未配置")
        try:
            port = int(port)
        except Exception:
            raise RuntimeError(f"server_port 不是有效整数: {port}")
        if username is None:
            raise RuntimeError("server_username 未配置")
        # 确保为 str 类型
        host = str(host)
        username = str(username)
        password = str(password) if password is not None else None

        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())  # 自动接受服务器指纹，避免确认弹窗
        ssh.connect(
            hostname=host,
            port=port,
            username=username,
            password=password,
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

    def get_exp_dicts(self, data_names):
        data_dict = {item["name"]: item for item in self.parent.data_list}
        not_found = []
        exp_dicts = {}
        exp_dict = {
            "institute": self.institute_text.text().strip() or "unknown",
            "user_name": self.user_name_text.text().strip() or "unknown",
            "d_rebin":self.parent.config["base"]["d_rebin"],
            "beamline": "",
            "norm_by_pc": False,
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
        for data_name in data_names:
            if data_name not in data_dict:
                not_found.append(data_names)
                continue
            runno = data_dict[data_name]["runno"]
            if runno not in exp_dicts.keys() and "Merged" not in data_name and "Hermite" not in data_name:
                exp_dicts[runno] = exp_dict.copy()
                exp_dicts[runno]["beamline"] = self.parent.config["base"]["beamline"]
                exp_dicts[runno]["sample_run"] = runno.split("_")
                if "normalization" in data_dict[data_name]["record"]:
                    if data_dict[data_name]["record"]["normalization"] == "proton_charge":
                        exp_dicts[runno]["norm_by_pc"] = True
                if "d_rebin" in data_dict[data_name]["record"]:
                    exp_dicts[runno]["d_rebin"][data_dict[data_name]['detector']] = data_dict[data_name]["record"]["d_rebin"]
                if "division" in data_dict[data_name]["record"]:
                    exp_dicts[runno]["v_run"] = self.get_runno_from_name(data_dict[data_name]["record"]["division"]).split("_")
                if "subtraction_self" in data_dict[data_name]["record"]:
                    exp_dicts[runno]["sampleBG_run"] = self.get_runno_from_name(data_dict[data_name]["record"]["subtraction_self"]).split("_")
                if "subtraction_v" in data_dict[data_name]["record"]:
                    exp_dicts[runno]["vBG_run"] = self.get_runno_from_name(data_dict[data_name]["record"]["subtraction_v"]).split("_")
                if "carpenterCorrection" in data_dict[data_name]["record"]:
                    exp_dicts[runno]["sample_correction"] = data_dict[data_name]["record"]["carpenterCorrection"]
                if "crop" in data_dict[data_name]["record"]:
                    exp_dicts[runno]["wave_min"] = float(data_dict[data_name]["record"]["crop"].split("_")[0])
                    exp_dicts[runno]["wave_max"] = float(data_dict[data_name]["record"]["crop"].split("_")[1])
                else:
                    exp_dicts[runno]["wave_min"] = self.parent.config["base"]["wave_min"]
                    exp_dicts[runno]["wave_max"] = self.parent.config["base"]["wave_max"]
                if "start_time" in data_dict[data_name]:
                    exp_dicts[runno]["start_time"] = data_dict[data_name]["start_time"]
                if "end_time" in data_dict[data_name]:
                    exp_dicts[runno]["end_time"] = data_dict[data_name]["end_time"]
        return exp_dicts

    def send_exp_dicts(self,data_names):
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
            exp_dicts = self.get_exp_dicts(data_names)
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
                    json_name = f"experiment.json"

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
        msg = [f"实验信息上传完成！共上传 {uploaded} 个文件。"]
        if failed:
            msg.append(f"失败 {len(failed)} 项：\n" + "\n".join(failed))
        QMessageBox.information(self, "Done", "\n\n".join(msg))

    def send_reduced_data(self):
        """
        将指定格式的数据保存到远端目录：
          远端结构：<remote_reduced_dir>/<runno>/...
        每个样本各放在其 runno 子目录下，文件包括：
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

        # 打开 SFTP 连接
        try:
            ssh, sftp = self._open_sftp()
        except Exception:
            return

        uploaded_diffraction = 0
        uploaded_pdf = 0
        failed_diffraction = []
        failed_pdf = []
        data_name_collection = []
        runnos_record = set()
        # 用临时目录承载所有待上传的本地文件
        with tempfile.TemporaryDirectory(prefix="rz_upload_") as tmp_root:
            try:
                for data in self.parent.data_list:    
                    if data.get("record"):
                        if data["record"].get("division"):
                            # 1) 计算 runno
                            # runno = self.get_runno_from_name(data["name"])
                            runno = data["runno"]
                            if data.get("time_slice"):
                                runno = f"{runno}_{data['time_slice']}"
                            # 2) 计算探测器组名
                            groupname, _ = get_all_from_detector(
                                data["detector"],
                                self.parent.config["base"]["group_info"],
                                self.parent.config["base"]["bank_info"]
                            )
                            # 3) 本地 runno 目录（临时）
                            local_run_dir = os.path.join(tmp_root, runno)
                            os.makedirs(local_run_dir, exist_ok=True)
                            # 4) 生成本地衍射数据（GSAS / Igor / FullProf）
                            try:
                                difa = self.parent.config["base"]["focus_point"][groupname]["DIFA"]
                                difb = self.parent.config["base"]["focus_point"][groupname]["DIFB"]
                                difc = self.parent.config["base"]["focus_point"][groupname]["DIFC"]
                                zero = self.parent.config["base"]["focus_point"][groupname]["ZERO"]

                                base_out = os.path.join(local_run_dir, f"{runno}_{data['detector']}")
                                output = DiffractionFormat(
                                    data["detector_focused"],
                                    runno,
                                    data["detector"],
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
                                uploaded_diffraction += 1
                                runnos_record.add(runno)
                            except Exception as ex_item:
                                failed_diffraction.append(f"{data['name']}: {ex_item}")
                            # # 5) 生成本地pdf数据
                            # if data.get("pdf_data"):
                            #     try:
                            #         pdf_fn = os.path.join(local_run_dir, f"{data['pdf_type']}_{data['name'].replace(':', '')}.txt")
                            #         x = data["pdf_data"][0]
                            #         y = data["pdf_data"][1]
                            #         e = np.zeros(np.shape(y))
                            #         write_rmc(pdf_fn, x, y, e)
                            #         uploaded_pdf += 1
                            #     except Exception as ex_item:
                            #         failed_pdf.append(f"{data['name']}: {ex_item}")
                            # 5) 确保远端 runno 目录存在
                            remote_run_dir = posixpath.join(self.remote_reduced_dir, runno)
                            self._sftp_mkdirs(sftp, remote_run_dir)
                            # 6) 上传本地 runno 目录下的所有文件（单层）
                            for fname in os.listdir(local_run_dir):
                                lp = os.path.join(local_run_dir, fname)
                                if not os.path.isfile(lp):
                                    continue
                                rp = posixpath.join(remote_run_dir, fname)
                                sftp.put(lp, rp)
                            # 6) 记录数据名称用于传实验信息
                            data_name_collection.append(data["name"])
                    elif data["name"] == "merged_data" or "Hermite_" in data["name"]:
                        runno = data["runno"]
                        local_run_dir = os.path.join(tmp_root, runno)
                        os.makedirs(local_run_dir, exist_ok=True)
                        try:
                            pdf_fn = os.path.join(local_run_dir, f"{data['pdf_type']}_{data['name'].replace(':', '')}.txt")
                            x = data["pdf_data"][0]
                            y = data["pdf_data"][1]
                            e = np.zeros(np.shape(y))
                            write_rmc(pdf_fn, x, y, e)
                            uploaded_pdf += 1
                            runnos_record.add(runno)
                        except Exception as ex_item:
                            failed_pdf.append(f"{data['name']}: {ex_item}")
                        # 确保远端 runno 目录存在
                        remote_run_dir = posixpath.join(self.remote_reduced_dir, runno)
                        self._sftp_mkdirs(sftp, remote_run_dir)
                        # 上传本地 runno 目录下的所有文件（单层）
                        for fname in os.listdir(local_run_dir):
                            lp = os.path.join(local_run_dir, fname)
                            if not os.path.isfile(lp):
                                continue
                            rp = posixpath.join(remote_run_dir, fname)
                            sftp.put(lp, rp)
                        # 记录数据名称用于传实验信息
                        data_name_collection.append(data["name"])
                self.last_uploaded_runnos = sorted(runnos_record)
            except Exception as ex_all:
                traceback.print_exc()
                QMessageBox.critical(self, "Upload Error", f"处理/上传过程中发生错误：\n{ex_all}")
                try:
                    sftp.close()
                    ssh.close()
                except Exception:
                    pass

        # 关闭 SFTP 连接
        try:
            sftp.close()
            ssh.close()
        except Exception:
            pass

        # 汇报结果
        msg_lines = [f"实验数据上传完成,上传衍射数据{uploaded_diffraction}条，PDF数据{uploaded_pdf}条!"]
        if failed_diffraction:
            msg_lines.append(f"处理失败衍射数据：{len(failed_diffraction)} 项\n" + "\n".join(failed_diffraction))
        if failed_pdf:
            msg_lines.append(f"处理失败PDF数据：{len(failed_pdf)} 项\n" + "\n".join(failed_pdf))
        QMessageBox.information(self, "Done", "\n\n".join(msg_lines))
        return data_name_collection

    def send_cif(self, cif_files):
        """
		将选中的 CIF 文件全部上传到 remote_cif_dirs 目录
		"""
        remote_cif_dirs = [posixpath.join(self.remote_reduced_dir, runno, "cifFiles") for runno in self.last_uploaded_runnos]
        files = [p for p in (cif_files or []) if os.path.isfile(p)]
        if not files:
            QMessageBox.warning(self, "Warning", "所选 CIF 文件不存在或无效")
            return
        try:
            ssh, sftp = self._open_sftp()
        except Exception:
            return
        try:
            msgs=[]
            for remote_cif_dir in remote_cif_dirs:
                # 确保远端目录存在
                self._sftp_mkdirs(sftp, remote_cif_dir)
                uploaded = 0
                failed = []

                for local_path in files:
                    base = os.path.basename(local_path)
                    remote_path = posixpath.join(remote_cif_dir, base)
                    try:
                        sftp.put(local_path, remote_path)
                        uploaded += 1
                    except Exception as e_put:
                        failed.append(f"{base} -> {e_put}")

                msgs.append(f"CIF上传到{remote_cif_dir}完成：{uploaded} 个文件\n")
                if failed:
                    msgs.append(f"CIF上传到{remote_cif_dir}失败：{len(failed)} 项\n" + "\n".join(failed))
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

    def _run_previous_modules(self):
        """运行前置模块"""
        current_name = self.objectName()
        for i in range(self.parent.inner_layout.count()):
            module = self.parent.inner_layout.itemAt(i).widget()
            if module is None:
                continue
            if module.objectName() == current_name:
                break
            if hasattr(module, 'run'):
                if hasattr(module, 'finished'):
                    loop = QEventLoop()
                    is_finished = False

                    def on_finished():
                        nonlocal is_finished
                        is_finished = True
                        loop.quit()

                    module.finished.connect(on_finished)
                    module.run()
                    if not is_finished:
                        loop.exec_()
                else:
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
    
