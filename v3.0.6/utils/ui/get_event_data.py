import os
import posixpath
import re
import socket
import stat
import time
import traceback
from PyQt5.QtCore import QObject, QThread, pyqtSignal
from PyQt5.QtWidgets import QApplication, QDialog, QLabel, QMessageBox, QProgressBar, QVBoxLayout, QLineEdit, QPushButton, QHBoxLayout
from utils.browse import browse
from utils.transfer_password_config import verify_password
from utils.ui.BaseUI import CollapsibleWidget


class EventTransferProgressDialog(QDialog):
    def __init__(self, thread, parent_widget, parent=None):
        super().__init__(parent)
        self.thread = thread
        self.parent_widget = parent_widget
        self.allow_auto_close = False
        self.setWindowTitle("Event Data Transfer")
        self.resize(320, 110)

        layout = QVBoxLayout()
        self.info_label = QLabel("progress info:starting...", self)
        layout.addWidget(self.info_label)

        self.progress_bar = QProgressBar(self)
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        layout.addWidget(self.progress_bar)
        self.setLayout(layout)

    def update_info(self, info):
        self.info_label.setText(f"progress info:{info}")

    def closeEvent(self, event):
        if self.allow_auto_close:
            event.accept()
            return

        self.update_info("Start stopping, please wait...")
        self.progress_bar.setRange(0, 0)

        worker = getattr(self.parent_widget, "worker", None)
        if worker is not None:
            worker.stop()

        thread = self.thread
        if thread is not None:
            try:
                is_running = thread.isRunning()
            except RuntimeError:
                is_running = False

            if is_running:
                try:
                    thread.quit()
                except RuntimeError:
                    is_running = False

                while is_running:
                    QApplication.processEvents()
                    try:
                        thread.wait(100)
                        is_running = thread.isRunning()
                    except RuntimeError:
                        break

        self.progress_bar.setRange(0, 100)
        event.accept()


class EventTransferWorker(QObject):
    finished = pyqtSignal()
    error = pyqtSignal(str, str)
    success = pyqtSignal(str)
    progress = pyqtSignal(int)
    progress_text = pyqtSignal(str)

    def __init__(self, source_ip, source_port, source_password, source_directory, target_directory, run_number_list):
        super().__init__()
        self.source_ip = source_ip
        self.source_port = source_port
        self.source_password = source_password
        self.source_directory = source_directory
        self.target_directory = target_directory
        self.run_number_list = run_number_list
        self._is_running = True
        self._downloaded_files = 0
        self._total_files = 0
        self._last_progress_emit_ts = 0.0
        self._ssh = None
        self._sftp = None
        self._sftp_channel = None

    def stop(self):
        self._is_running = False
        self._close_connections()

    def _close_connections(self):
        if self._sftp_channel is not None:
            try:
                self._sftp_channel.close()
            except Exception:
                pass
            self._sftp_channel = None

        if self._sftp is not None:
            try:
                self._sftp.close()
            except Exception:
                pass
            self._sftp = None

        if self._ssh is not None:
            try:
                self._ssh.close()
            except Exception:
                pass
            self._ssh = None

    def _check_running(self):
        if not self._is_running:
            raise RuntimeError("Transfer canceled by user.")

    def _get_connection_info(self):
        if "@" not in self.source_ip:
            raise ValueError(f"Invalid event_source_ip: {self.source_ip}")

        username, host = self.source_ip.split("@", 1)
        if not username or not host:
            raise ValueError(f"Invalid event_source_ip: {self.source_ip}")

        try:
            port = int(self.source_port)
        except Exception as e:
            raise ValueError(f"Invalid event_source_port: {self.source_port}") from e

        return host, port, username, self.source_password

    def _open_sftp(self):
        try:
            import paramiko
        except ImportError as e:
            raise RuntimeError("缺少依赖 paramiko，请先安装后再传输事件数据。") from e

        host, port, username, password = self._get_connection_info()

        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        try:
            ssh.connect(
                hostname=host,
                port=port,
                username=username,
                password=password,
                timeout=15,
                banner_timeout=15,
                auth_timeout=15,
            )
            sftp = ssh.open_sftp()
            transport = ssh.get_transport()
            if transport is not None:
                transport.set_keepalive(30)
            try:
                sftp_channel = sftp.get_channel()
                sftp_channel.settimeout(60)
            except Exception:
                sftp_channel = None
        except paramiko.AuthenticationException as e:
            ssh.close()
            raise ConnectionError(f"无法连接远程服务器 {host}:{port}，用户名或密码错误。") from e
        except (paramiko.SSHException, socket.timeout, OSError) as e:
            ssh.close()
            raise ConnectionError(
                f"无法连接远程服务器 {host}:{port}，请确认网络连通、服务器在线且 SSH 服务可用。\n原始错误: {e}"
            ) from e
        except Exception:
            ssh.close()
            raise

        self._ssh = ssh
        self._sftp = sftp
        self._sftp_channel = sftp_channel
        return ssh, sftp

    def _validate_remote_run_dir(self, sftp, run_number):
        remote_run_dir = posixpath.join(self.source_directory, run_number)
        try:
            remote_stat = sftp.stat(remote_run_dir)
        except FileNotFoundError as e:
            raise FileNotFoundError(f"远程目录不存在: {remote_run_dir}") from e
        except OSError as e:
            raise RuntimeError(f"无法访问远程目录: {remote_run_dir}\n原始错误: {e}") from e

        if not stat.S_ISDIR(remote_stat.st_mode):
            raise RuntimeError(f"远程路径不是目录: {remote_run_dir}")

        return remote_run_dir

    def _count_files_in_remote_dir(self, sftp, remote_dir):
        self._check_running()
        count = 0
        for entry in sftp.listdir_attr(remote_dir):
            self._check_running()
            if entry.filename == "detector.nxs":
                continue

            remote_path = posixpath.join(remote_dir, entry.filename)
            if stat.S_ISDIR(entry.st_mode):
                count += self._count_files_in_remote_dir(sftp, remote_path)
            else:
                count += 1
        return count

    def _count_run_files(self, sftp, run_number):
        remote_run_dir = self._validate_remote_run_dir(sftp, run_number)
        return self._count_files_in_remote_dir(sftp, remote_run_dir)

    def _emit_progress(self, text, current_file_percent=None, force=False):
        if self._total_files > 0:
            current_ratio = max(0.0, min(1.0, (current_file_percent or 0) / 100.0))
            completed_files = self._downloaded_files + current_ratio
            progress_value = min(100, int(completed_files * 100 / self._total_files))
        else:
            progress_value = min(99, int(current_file_percent or 0))

        now = time.monotonic()
        if force or (now - self._last_progress_emit_ts >= 0.2):
            self.progress.emit(progress_value)
            self.progress_text.emit(text)
            self._last_progress_emit_ts = now

    def _download_remote_tree(self, sftp, remote_dir, local_dir, run_number):
        self._check_running()
        os.makedirs(local_dir, exist_ok=True)
        for entry in sftp.listdir_attr(remote_dir):
            self._check_running()
            if entry.filename == "detector.nxs":
                continue

            remote_path = posixpath.join(remote_dir, entry.filename)
            local_path = os.path.join(local_dir, entry.filename)

            if stat.S_ISDIR(entry.st_mode):
                self._download_remote_tree(sftp, remote_path, local_path, run_number)
            else:
                file_size = max(0, int(entry.st_size or 0))

                def _progress_callback(transferred, total):
                    self._check_running()
                    file_total = total if total and total > 0 else file_size
                    if file_total <= 0:
                        return
                    percent = min(100, int(transferred * 100 / file_total))
                    self._emit_progress(
                        f"{run_number}: {entry.filename} ({percent}%)",
                        current_file_percent=percent,
                    )

                self._emit_progress(f"{run_number}: {entry.filename}", current_file_percent=0, force=True)
                sftp.get(remote_path, local_path, callback=_progress_callback)
                self._downloaded_files += 1
                self._emit_progress(f"{run_number}: {entry.filename}", current_file_percent=100, force=True)

    def _download_run_directory(self, sftp, run_number):
        remote_run_dir = posixpath.join(self.source_directory, run_number)
        local_run_dir = os.path.join(self.target_directory, run_number)
        os.makedirs(local_run_dir, exist_ok=True)
        self._download_remote_tree(sftp, remote_run_dir, local_run_dir, run_number)

    def run(self):
        ssh = None
        sftp = None
        try:
            self.progress.emit(0)
            self.progress_text.emit("Connecting to remote server...")
            os.makedirs(self.target_directory, exist_ok=True)

            ssh, sftp = self._open_sftp()

            self.progress_text.emit("Scanning file counts...")
            for run_number in self.run_number_list:
                self._check_running()
                self._total_files += self._count_run_files(sftp, run_number)

            if self._total_files == 0:
                self.progress.emit(100)
                self.success.emit(
                    f"已检查并处理 {len(self.run_number_list)} 个 RUN 目录，但没有发现可下载文件。\n\n所有 detector.nxs 文件都会被跳过。"
                )
                return

            for run_number in self.run_number_list:
                self._check_running()
                self.progress_text.emit(f"Downloading {run_number}...")
                self._download_run_directory(sftp, run_number)

            self.progress.emit(100)
            if self._downloaded_files == 0:
                self.success.emit(
                    f"已检查并处理 {len(self.run_number_list)} 个 RUN 目录，但没有发现可下载文件。\n\n所有 detector.nxs 文件都会被跳过。"
                )
            else:
                self.success.emit(
                    f"已传输 {len(self.run_number_list)} 个 RUN 目录到:\n{self.target_directory}\n\n目录内容会一并下载，且已跳过所有 detector.nxs 文件。"
                )
        except ValueError as e:
            self.error.emit("Invalid Input", str(e))
        except ConnectionError as e:
            if not self._is_running:
                self.error.emit("Transfer Canceled", "用户已取消传输。")
            else:
                self.error.emit("Connection Error", str(e))
        except FileNotFoundError as e:
            if not self._is_running:
                self.error.emit("Transfer Canceled", "用户已取消传输。")
            else:
                self.error.emit("Transfer Error", str(e))
        except OSError as e:
            if not self._is_running:
                self.error.emit("Transfer Canceled", "用户已取消传输。")
            else:
                self.error.emit("Transfer Error", f"本地目录创建或文件写入失败:\n{e}")
        except RuntimeError as e:
            if str(e) == "Transfer canceled by user.":
                self.error.emit("Transfer Canceled", "用户已取消传输。")
            else:
                self.error.emit("Transfer Error", str(e))
        except Exception as e:
            if not self._is_running:
                self.error.emit("Transfer Canceled", "用户已取消传输。")
            else:
                self.error.emit("Transfer Error", f"传输过程中出现未预期错误:\n{e}")
                print(f'Reason: {e}')
                traceback.print_exc()
        finally:
            self._close_connections()
            self.finished.emit()


class PasswordInputDialog(QDialog):
    """自定义密码输入对话框"""
    def __init__(self, beamline, parent=None):
        super().__init__(parent)
        self.setWindowTitle("传输密码验证")
        self.setModal(True)
        self.setMinimumWidth(300)
        self.password = ""

        layout = QVBoxLayout()
        
        label = QLabel(f"请输入 {beamline} 的传输密码:")
        layout.addWidget(label)
        
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        layout.addWidget(self.password_input)
        
        button_layout = QHBoxLayout()
        ok_button = QPushButton("确定")
        cancel_button = QPushButton("取消")
        button_layout.addWidget(ok_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
        
        ok_button.clicked.connect(self.accept)
        cancel_button.clicked.connect(self.reject)
        self.password_input.returnPressed.connect(self.accept)
    
    def get_password(self):
        return self.password_input.text()


class get_event_data(CollapsibleWidget):
    def __init__(self, name, parent):
        super(get_event_data, self).__init__(name, "utils/ui/get_event_data.ui", parent)
        self.parent = parent
        self.thread = None
        self.worker = None
        self.progress_dialog = None
        try:
            self.target_directory = self.parent.config["base"]["event_target_directory"]
            self.targetDirectoryText.setText(self.target_directory)
            self.source_directory = self.parent.config["base"]["event_source_directory"]
            self.source_ip = self.parent.config["base"].get("event_source_ip", "")
            self.source_port = self.parent.config["base"].get("event_source_port", 22)
        except Exception as e:
            print(f'Reason: {e}')
            traceback.print_exc()

        self.source_password = self.parent.config["base"].get("event_source_password", "")
        if not self.source_password:
            QMessageBox.critical(self, "无数据存储服务器密码", "先配置服务器密码，否则无法进行传输。")

        self.browse_run = browse()
        self.targetDirectoryButton.clicked.connect(lambda: self.browse_run.select_folder(self.targetDirectoryText))

        if hasattr(self, "sendButton"):
            self.sendButton.clicked.connect(self.send_data)

    def _normalize_run_numbers(self, run_number_text):
        raw_tokens = [token.strip() for token in re.split(r"[，,\s]+", run_number_text.strip()) if token.strip()]
        if not raw_tokens:
            raise ValueError("Run number cannot be empty.")

        normalized_runs = []
        for token in raw_tokens:
            match = re.fullmatch(r"(?:RUN)?(\d+)", token, re.IGNORECASE)
            if not match:
                raise ValueError(f"Invalid run number: {token}")
            normalized_runs.append(f"RUN{match.group(1).zfill(7)}")

        return normalized_runs

    def send_data(self):
        try:
            if self.thread is not None and self.thread.isRunning():
                QMessageBox.information(self, "Transfer Running", "当前已有传输任务正在进行，请等待完成。")
                return

            beamline = self.parent.config["base"].get("beamline", "")
            if not beamline:
                QMessageBox.warning(self, "Configuration Error", "无法获取 beamline 信息，请检查配置。")
                return

            password_dialog = PasswordInputDialog(beamline, self)
            if password_dialog.exec_() != QDialog.Accepted:
                return
            
            password = password_dialog.get_password()
            if not password:
                return

            if not verify_password(beamline, password):
                QMessageBox.critical(self, "密码错误", "您输入的密码不正确，无法进行传输。")
                return

            run_number_list = self._normalize_run_numbers(self.runNumberText.text())
            target_directory = self.targetDirectoryText.text().strip()

            if not target_directory:
                raise ValueError("Target directory cannot be empty.")

            os.makedirs(target_directory, exist_ok=True)
            self.runNumberText.setText(",".join(run_number_list))

            self.thread = QThread()
            self.worker = EventTransferWorker(
                self.source_ip,
                self.source_port,
                self.source_password,
                self.source_directory,
                target_directory,
                run_number_list,
            )
            self.worker.moveToThread(self.thread)

            self.progress_dialog = EventTransferProgressDialog(self.thread, self)
            self.progress_dialog.update_info("Preparing transfer...")
            self.progress_dialog.progress_bar.setValue(0)
            self.progress_dialog.show()

            self.thread.started.connect(self.worker.run)
            self.worker.finished.connect(self.thread.quit)
            self.worker.finished.connect(self.worker.deleteLater)
            self.thread.finished.connect(self.thread.deleteLater)
            self.worker.progress.connect(self.progress_dialog.progress_bar.setValue)
            self.worker.progress_text.connect(self.progress_dialog.update_info)
            self.worker.error.connect(self._handle_transfer_error)
            self.worker.success.connect(self._handle_transfer_success)
            self.thread.finished.connect(self._on_transfer_finished)

            self.thread.start()
        except ValueError as e:
            QMessageBox.warning(self, "Invalid Input", str(e))
        except OSError as e:
            QMessageBox.critical(self, "Transfer Error", f"本地目录创建或文件写入失败:\n{e}")
        except Exception as e:
            QMessageBox.critical(self, "Transfer Error", f"启动传输任务失败:\n{e}")
            print(f'Reason: {e}')
            traceback.print_exc()

    def _handle_transfer_error(self, title, message):
        QMessageBox.critical(self, title, message)

    def _handle_transfer_success(self, message):
        QMessageBox.information(self, "Success", message)

    def _on_transfer_finished(self):
        if self.progress_dialog is not None:
            self.progress_dialog.allow_auto_close = True
            self.progress_dialog.close()
            self.progress_dialog = None
        self.worker = None
        self.thread = None

    def get_config(self):
        return {
            "is_use": self.toggle_button.isChecked(),
            "run_number_text": self.runNumberText.text(),
            "target_directory_text": self.targetDirectoryText.text()
        }

    def set_config(self, config):
        """根据配置更新模块状态"""
        self.toggle_button.setChecked(config.get("is_use", False))
        self.runNumberText.setText(config.get("run_number_text", ""))
        self.targetDirectoryText.setText(config.get("target_directory_text", ""))

