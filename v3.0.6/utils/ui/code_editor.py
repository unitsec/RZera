from PyQt5.uic import loadUi
from utils.helper import get_resource_path
from PyQt5 import QtWidgets, QtGui, QtCore
from PyQt5.QtWidgets import QWidget, QMessageBox, QFileDialog
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QSettings
from PyQt5.QtGui import QFont, QTextCursor
import sys
import os
import traceback
import subprocess
from io import StringIO

# QScintilla is optional for syntax highlighting
# If not available, we'll use regular QTextEdit which works perfectly fine
# 尝试在运行时导入 QScintilla（如果可用则启用语法高亮编辑器）
try:
    from PyQt5.Qsci import QsciScintilla, QsciLexerPython  # type: ignore
    QSCI_AVAILABLE = True
except Exception:
    QSCI_AVAILABLE = False

class ScriptExecutor(QThread):
    """在独立线程中执行Python脚本（仅子进程执行）"""
    output_signal = pyqtSignal(str)
    error_signal = pyqtSignal(str)
    finished_signal = pyqtSignal()

    def __init__(self, code, custom_module_path=None, current_file=None, python_executable=None):
        super().__init__()
        self.code = code
        self.custom_module_path = custom_module_path
        self.current_file = current_file
        self.python_executable = python_executable
        # 子进程句柄与临时脚本路径，供外部 stop() 使用
        self._proc = None
        self._temp_script = None
        self._stop_requested = False

    def run(self):
        try:
            # 仅使用子进程执行，彻底移除在当前环境执行的风险
            self._execute_in_subprocess()
        except BaseException as e:
            # 捕获包括 SystemExit 在内的异常，避免导致主程序退出
            self.error_signal.emit(f"执行错误: {str(e)}\n{traceback.format_exc()}")
        finally:
            self.finished_signal.emit()
    
    # 已移除在当前环境执行的实现，统一使用子进程执行以提高稳定性
    
    def _execute_in_subprocess(self):
        """在子进程中执行代码"""
        import tempfile,sys,os,time

        # 当前脚本真实路径与目录
        script_file = self.current_file or "<editor>"
        script_dir  = os.path.dirname(script_file) if self.current_file else os.getcwd()

        # 为子进程添加matplotlib后端设置和编码设置
        # 构建自定义路径添加代码
        custom_path_code = ''
        if self.custom_module_path and os.path.isdir(self.custom_module_path):
            custom_path_code = f'''
# 添加自定义模块路径
custom_module_path = r"{self.custom_module_path}"
if custom_module_path not in sys.path:
    sys.path.insert(0, custom_module_path)
    print(f">>> 已添加自定义模块路径: {{custom_module_path}}")
'''
        
        subprocess_code = ('''
# -*- coding: utf-8 -*-
import sys
import os

# 强制刷新输出，确保实时显示
import functools
_original_print = print
print = functools.partial(_original_print, flush=True)

# 设置 __file__ 为真实脚本路径，而不是临时文件
__file__ = r"{script_file}"

# 设置输出编码为UTF-8，解决Windows下的编码问题
if sys.platform.startswith('win'):
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.detach())
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.detach())

import matplotlib
# 设置matplotlib后端以支持图形显示
try:
    matplotlib.use('Qt5Agg')  # 使用Qt5后端
except:
    try:
        matplotlib.use('TkAgg')  # 备用Tk后端
    except:
        matplotlib.use('Agg')  # 最后备用非交互后端

print(">>> 子进程环境已准备就绪")
print(f">>> __file__ = {{__file__}}")
print(f">>> 工作目录 = {{os.getcwd()}}")
print(f">>> Python 可执行文件 = {{sys.executable}}")
# print(">>> 如需使用 rongzai 模块，请在代码中添加:")
# print(">>> from rongzai.dataSvc import read_dataset, create_dataset")
print()

''').format(script_file=script_file) + custom_path_code + self.code
        
        # 创建临时脚本文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
            f.write(subprocess_code)
            temp_script = f.name
        # 保存临时脚本路径以便在 stop 时清理
        self._temp_script = temp_script
        
        try:
            # 确定将用于子进程的 Python 可执行文件（优先：传入值 -> 设置 -> 自动检测 openRongzai -> fallback sys.executable）
            python_exe = None
            try:
                if getattr(self, 'python_executable', None):
                    if os.path.isfile(self.python_executable):
                        python_exe = self.python_executable
                # 如果没有显式提供或路径无效，则尝试从编辑器设置读取（由 CodeEditor 传入或保存在 QSettings 中）
            except Exception:
                python_exe = None

            # 自动检测项目根目录下名为 openRongzai 的解压环境
            if not python_exe:
                try:
                    # 项目根：回溯到项目目录（与 get_default_module_path 中的逻辑一致）
                    file_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                    candidate_dirs = [
                        os.path.join(file_dir, 'openRongzai'),
                    ]
                    found = None
                    for d in candidate_dirs:
                        if os.path.isdir(d):
                            # 常见位置
                            candidates = [
                                os.path.join(d, 'python.exe'),
                                os.path.join(d, 'Scripts', 'python.exe'),
                                os.path.join(d, 'bin', 'python.exe'),
                                os.path.join(d, 'bin', 'python'),
                            ]
                            for c in candidates:
                                if os.path.isfile(c):
                                    found = c
                                    break
                        if found:
                            break
                    if found:
                        python_exe = found
                except Exception:
                    python_exe = None

            # 最后回退到当前解释器
            if not python_exe:
                python_exe = sys.executable

            # 设置环境变量，确保UTF-8编码并禁用缓冲
            env = os.environ.copy()
            env['PYTHONIOENCODING'] = 'utf-8'
            env['PYTHONUNBUFFERED'] = '1'
            if sys.platform.startswith('win'):
                env['PYTHONLEGACYWINDOWSSTDIO'] = '0'

            # 尝试清理可能导致不同 Qt 版本混用的环境（例如 PATH 中来自主程序的 Qt DLL）
            try:
                def _find_candidate_plugin_dirs(python_exe_path):
                    base = os.path.dirname(python_exe_path)
                    candidates = [
                        os.path.join(base, 'Lib', 'site-packages', 'PyQt5', 'Qt', 'plugins'),
                        os.path.join(base, 'Lib', 'site-packages', 'PySide2', 'Qt', 'plugins'),
                        os.path.join(base, 'plugins'),
                        os.path.join(base, 'Library', 'plugins'),
                    ]
                    return [p for p in candidates if os.path.isdir(p)]

                plugin_dirs = _find_candidate_plugin_dirs(python_exe)
                if plugin_dirs:
                    chosen_plugin = plugin_dirs[0]
                    env['QT_PLUGIN_PATH'] = chosen_plugin
                    env['QT_QPA_PLATFORM_PLUGIN_PATH'] = chosen_plugin
                    try:
                        self.output_signal.emit(f">>> 设置子进程 QT 插件路径: {chosen_plugin}\n")
                    except Exception:
                        pass
                else:
                    try:
                        self.output_signal.emit(
                            ">>> 未在目标解释器环境中找到 Qt 插件目录，继续启动但可能出现 Qt 版本冲突\n"
                        )
                    except Exception:
                        pass

                # 清理 PATH 中明显指向其他 Qt/PyQt/PySide 的条目，优先保留目标 python 可执行文件目录
                orig_path = env.get('PATH', '')
                path_parts = orig_path.split(os.pathsep) if orig_path else []
                new_parts = []
                python_dir = os.path.dirname(python_exe)
                for p in path_parts:
                    try:
                        lp = p.lower()
                    except Exception:
                        lp = ''
                    # 如果路径包含明显的 Qt 关键词且不属于目标解释器目录，则移除
                    if ('qt' in lp or 'pyqt' in lp or 'pyside' in lp) and (python_dir.lower() not in lp):
                        try:
                            self.output_signal.emit(f">>> 从 PATH 移除可能冲突项: {p}\n")
                        except Exception:
                            pass
                        continue
                    new_parts.append(p)
                # 确保目标 python 目录位于 PATH 前面
                if python_dir and python_dir not in new_parts:
                    new_parts.insert(0, python_dir)
                env['PATH'] = os.pathsep.join(new_parts)
            except Exception as e:
                try:
                    self.output_signal.emit(f">>> 清理子进程环境时发生错误: {e}\n")
                except Exception:
                    pass

            # 使用 Popen 实现实时输出流式读取（将 stderr 合并到 stdout，简化处理）
            try:
                proc = subprocess.Popen(
                    [python_exe, '-u', temp_script],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    bufsize=1,
                    universal_newlines=True,
                    encoding='utf-8',
                    env=env,
                    cwd=script_dir
                )
                # 保存子进程句柄
                self._proc = proc

                start_time = time.time()
                timeout_seconds = 60

                # 逐行读取子进程输出并实时发送到主界面
                while True:
                    # 如果外部请求停止，尽快终止子进程
                    if getattr(self, '_stop_requested', False):
                        try:
                            if self._proc and self._proc.poll() is None:
                                try:
                                    self._proc.terminate()
                                except Exception:
                                    pass
                        except Exception:
                            pass
                        break
                    line = proc.stdout.readline()
                    if line:
                        # 直接发送原始行（包含换行），主线程负责显示
                        self.output_signal.emit(line)
                        start_time = time.time()  # 读到输出，延长超时计时
                    else:
                        # 如果进程已结束且无更多输出，则退出循环
                        if proc.poll() is not None:
                            break
                        # 检查超时
                        if (time.time() - start_time) > timeout_seconds:
                            try:
                                proc.kill()
                            except Exception:
                                pass
                            self.error_signal.emit("脚本执行超时（60秒），已终止子进程\n")
                            break
                        time.sleep(0.05)  # 避免 busy-loop

                # 读取剩余缓冲（极端情况下）
                remaining = proc.stdout.read()
                if remaining:
                    self.output_signal.emit(remaining)

                returncode = proc.poll()
                if returncode is None:
                    returncode = proc.wait()

                if returncode != 0:
                    self.error_signal.emit(f"脚本执行失败，返回码: {returncode}\n")
                else:
                    self.output_signal.emit(">>> 子进程执行完成（图形窗口可能已显示）\n")

            except subprocess.TimeoutExpired:
                self.error_signal.emit("脚本执行超时（60秒）")
            except Exception as e:
                self.error_signal.emit(f"执行错误: {str(e)}\n{traceback.format_exc()}")
            finally:
                # 清理临时文件并确保子进程被终止
                try:
                    if getattr(self, '_proc', None) and self._proc.poll() is None:
                        try:
                            self._proc.kill()
                        except Exception:
                            pass
                except Exception:
                    pass
                try:
                    if self._temp_script:
                        os.unlink(self._temp_script)
                except Exception:
                    pass
                
        except subprocess.TimeoutExpired:
            self.error_signal.emit("脚本执行超时（60秒）")
        except Exception as e:
            self.error_signal.emit(f"执行错误: {str(e)}")
        finally:
            # 清理临时文件
            try:
                if self._temp_script:
                    os.unlink(self._temp_script)
            except:
                pass

    def stop(self, force=False, wait=3.0):
        """外部调用以请求停止正在运行的子进程与线程。

        - force: 若 True 则在普通 terminate 无效时强制 kill
        - wait: 等待子进程结束的秒数
        """
        try:
            self._stop_requested = True
            proc = getattr(self, '_proc', None)
            if proc and proc.poll() is None:
                try:
                    proc.terminate()
                except Exception:
                    pass
                # 等待短时间
                try:
                    proc.wait(timeout=wait)
                except Exception:
                    if force:
                        try:
                            proc.kill()
                        except Exception:
                            pass
        except Exception:
            pass

class CodeEditor(QtWidgets.QMainWindow):
    def setup_file_tree(self):
        """配置文件树控件"""
        from PyQt5.QtWidgets import QFileSystemModel
        self.file_model = QFileSystemModel()
        self.file_model.setRootPath("")
        self.file_tree_view.setModel(self.file_model)
        self.file_tree_view.setHeaderHidden(True)
        self.file_tree_view.setAnimated(True)
        self.file_tree_view.setIndentation(16)
        self.file_tree_view.setSortingEnabled(True)
        # 只显示文件名
        for i in range(1, 4):
            self.file_tree_view.hideColumn(i)
        # 连接点击事件
        self.file_tree_view.clicked.connect(self.on_file_tree_clicked)

    def refresh_file_tree_root(self):
        """刷新文件树根目录为当前模块路径"""
        if self.file_model and self.custom_module_path and os.path.isdir(self.custom_module_path):
            self.file_tree_view.setRootIndex(self.file_model.index(self.custom_module_path))

    def on_file_tree_clicked(self, index):
        """点击文件树节点，打开文件"""
        if not self.file_model:
            return
        file_path = self.file_model.filePath(index)
        if os.path.isfile(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                self.code_text_edit.setText(content)
                self.current_file = file_path
                self.status_label.setText(f"已打开: {os.path.basename(file_path)}")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"无法打开文件: {str(e)}")
    """代码编辑器窗口"""
    
    def __init__(self, parent=None):
        super().__init__(None)  # 不设置父窗口，使其成为独立窗口
        
        # 创建中央窗口部件并加载UI
        central_widget = QtWidgets.QWidget()
        loadUi(get_resource_path("utils/ui/code_editor.ui"), central_widget)
        self.setCentralWidget(central_widget)
        
        # 手动映射UI元素（确保所有控件可访问）
        # 编辑器和输出区域 - 支持 QsciScintilla 或 QTextEdit
        code_widget = None
        try:
            if QSCI_AVAILABLE:
                try:
                    from PyQt5.Qsci import QsciScintilla
                    code_widget = central_widget.findChild(QsciScintilla, 'code_text_edit')
                except Exception:
                    code_widget = None
        except Exception:
            code_widget = None

        if code_widget is None:
            code_widget = central_widget.findChild(QtWidgets.QTextEdit, 'code_text_edit')
        if code_widget is None:
            # 最后回退查找任意 QWidget 名称相同的占位
            code_widget = central_widget.findChild(QtWidgets.QWidget, 'code_text_edit')

        self.code_text_edit = code_widget
        self.output_text_edit = central_widget.findChild(QtWidgets.QTextEdit, 'output_text_edit')
        
        # 所有按钮
        self.new_button = central_widget.findChild(QtWidgets.QPushButton, 'new_button')
        self.open_button = central_widget.findChild(QtWidgets.QPushButton, 'open_button')
        self.save_button = central_widget.findChild(QtWidgets.QPushButton, 'save_button')
        self.save_as_button = central_widget.findChild(QtWidgets.QPushButton, 'save_as_button')
        self.run_button = central_widget.findChild(QtWidgets.QPushButton, 'run_button')
        self.stop_button = central_widget.findChild(QtWidgets.QPushButton, 'stop_button')
        self.clear_output_button = central_widget.findChild(QtWidgets.QPushButton, 'clear_output_button')
        self.set_module_path_button = central_widget.findChild(QtWidgets.QPushButton, 'set_module_path_button')
        self.set_python_exec_button = central_widget.findChild(QtWidgets.QPushButton, 'set_python_exec_button')
        
        # （已移除）执行模式下拉框：编辑器现在始终使用子进程执行
        
        # 状态标签
        self.status_label = central_widget.findChild(QtWidgets.QLabel, 'status_label')
        self.module_path_label = central_widget.findChild(QtWidgets.QLabel, 'module_path_label')
        self.python_exec_label = central_widget.findChild(QtWidgets.QLabel, 'python_exec_label')
        
        # 设置窗口属性
        self.setWindowTitle("RZera Python 脚本编辑器")
        self.resize(1200, 800)
        # 文件树相关（UI 中的 QTreeView）
        self.file_tree_view = central_widget.findChild(QtWidgets.QTreeView, 'file_tree_view')
        self.file_model = None
        if self.file_tree_view:
            try:
                self.setup_file_tree()
            except Exception:
                pass
        
        self.parent_ref = parent  # 避免与PyQt的parent属性冲突
        self.current_file = None
        self.executor_thread = None
        
        # 防止窗口意外关闭的保护标志
        self._execution_in_progress = False
        
        # 自定义模块路径配置
        self.settings = QSettings('RZera', 'PythonEditor')
        self.custom_module_path = self.load_custom_module_path()
        
        self.setup_ui()
        # self.setup_default_code()
        
    def setup_ui(self):
        """初始化UI设置"""
        # 设置代码编辑器
        self.setup_code_editor()
        
        # 更新模块路径显示
        self.update_module_path_display()
        # 更新解释器显示
        self.update_python_exec_display()
        
        # 连接信号
        self.connect_signals()
        # 确保编辑器位于输出之上并设置默认分割比例
        try:
            splitter = self.centralWidget().findChild(QtWidgets.QSplitter, 'main_splitter')
            if splitter is not None:
                # 如果为横向分割，给左侧（文件树）较小宽度，右侧为编辑区
                try:
                    splitter.setSizes([220, 980])
                except Exception:
                    pass
                # 如果右侧嵌套了 editor_splitter（垂直），设置其默认比例
                try:
                    editor_splitter = self.centralWidget().findChild(QtWidgets.QSplitter, 'editor_splitter')
                    if editor_splitter is not None:
                        editor_splitter.setSizes([700, 200])
                except Exception:
                    pass
        except Exception:
            pass
        # 打开时将文件树根设置为当前模块路径
        try:
            if hasattr(self, 'file_tree_view') and self.file_tree_view is not None:
                self.refresh_file_tree_root()
        except Exception:
            pass
        
    def setup_code_editor(self):
        """设置代码编辑器（始终使用 QScintilla）"""
        try:
            from PyQt5.Qsci import QsciScintilla, QsciLexerPython
        except Exception as e:
            # 如果 QScintilla 丢失，打印错误并让程序继续（编辑器将不可用）
            print(f"⚠️ QScintilla 未找到，编辑器初始化失败: {e}")
            return

        # 我们期望 UI 中的 `code_text_edit` 已经是一个 QsciScintilla（UI 已修改），但若不是则尝试替换
        try:
            editor = self.code_text_edit
            if not isinstance(editor, QsciScintilla):
                # 尝试通过布局替换占位控件
                try:
                    parent_widget = editor.parentWidget()
                    layout = parent_widget.layout() if parent_widget is not None else None
                    scintilla_editor = QsciScintilla(parent_widget)
                    if layout is not None:
                        for i in range(layout.count()):
                            item = layout.itemAt(i)
                            if item and item.widget() is editor:
                                layout.insertWidget(i, scintilla_editor)
                                layout.removeWidget(editor)
                                editor.hide()
                                editor.deleteLater()
                                break
                    else:
                        scintilla_editor.setGeometry(editor.geometry())
                    self.code_text_edit = scintilla_editor
                    editor = self.code_text_edit
                except Exception as e:
                    print(f"⚠️ 无法替换为 QScintilla 编辑器: {e}")

        except Exception:
            # 如果 UI 没有 code_text_edit，直接创建并放在窗口顶部不做复杂布局操作
            scintilla_editor = QsciScintilla(self.centralWidget())
            scintilla_editor.setGeometry(10, 50, 1180, 300)
            scintilla_editor.show()
            self.code_text_edit = scintilla_editor

        # 配置 QScintilla（确保 editor 已被设置为 QsciScintilla 实例）
        try:
            if not isinstance(self.code_text_edit, QsciScintilla):
                # 如果 self.code_text_edit 不是 QsciScintilla（例如 None 或其他控件），
                # 尝试把 QsciScintilla 插入到 splitter 的第一个位置
                scintilla_editor = QsciScintilla(self.centralWidget())
                splitter = self.centralWidget().findChild(QtWidgets.QSplitter, 'main_splitter')
                try:
                    if splitter is not None:
                        old = splitter.widget(0)
                        splitter.insertWidget(0, scintilla_editor)
                        try:
                            if old is not None:
                                old.hide()
                                old.deleteLater()
                        except Exception:
                            pass
                    else:
                        scintilla_editor.setGeometry(10, 50, 1180, 300)
                except Exception:
                    scintilla_editor.setGeometry(10, 50, 1180, 300)
                self.code_text_edit = scintilla_editor

            editor = self.code_text_edit

            lexer = QsciLexerPython()
            editor.setLexer(lexer)
            editor.setIndentationsUseTabs(False)
            editor.setIndentationWidth(4)
            editor.setAutoIndent(True)
            editor.setMarginType(0, QsciScintilla.NumberMargin)
            editor.setMarginLineNumbers(0, True)
            editor.setMarginWidth(0, "0000")
            
            # 增强功能：自动补全
            try:
                editor.setAutoCompletionSource(QsciScintilla.AcsAll)
                editor.setAutoCompletionThreshold(2)  # 输入2个字符后触发
                editor.setAutoCompletionCaseSensitivity(False)
            except Exception:
                pass
            
            # 增强功能：括号匹配
            try:
                editor.setBraceMatching(QsciScintilla.SloppyBraceMatch)
            except Exception:
                pass
            
            
            font = QFont("Consolas", 11)
            editor.setFont(font)
            try:
                editor.setUtf8(True)
            except Exception:
                pass

            # 兼容现有代码接口
            try:
                editor.toPlainText = editor.text
            except Exception:
                pass
            try:
                editor.setPlainText = editor.setText
            except Exception:
                pass

            # 快捷键与按键处理，仅保留注释切换
            from PyQt5.QtCore import Qt

            def custom_keyPressEvent(event):
                # Ctrl+/ 触发注释切换
                if event.modifiers() & Qt.ControlModifier and event.key() in (Qt.Key_Slash, Qt.Key_division):
                    self.toggle_comment()
                    return
                # 其它按键交给原始处理
                QsciScintilla.keyPressEvent(editor, event)
            editor.keyPressEvent = custom_keyPressEvent
            print("✅ QScintilla编辑器已启用，支持语法高亮")
        except Exception as e:
            print(f"⚠️ 配置 QScintilla 时出错: {e}")

    def setup_default_code(self):
        """设置默认代码示例（仅在编辑器为空时填充）"""
        default_code = ('# RZera Python 脚本编辑器\n'
                        '# 在此编写脚本，按 F5 或点击运行执行\n\n'
                        'import numpy as np\n'
                            'print("Hello from RZera editor")\n')
        try:
            if not self.code_text_edit.toPlainText().strip():
                try:
                    self.code_text_edit.setPlainText(default_code)
                except Exception:
                    try:
                        self.code_text_edit.setText(default_code)
                    except Exception:
                        pass
        except Exception:
            pass
        
    def load_custom_module_path(self):
        """加载自定义模块路径，优先使用用户设置，否则使用默认路径"""
        # 尝试从设置中读取
        saved_path = self.settings.value('custom_module_path', '')
        
        # 如果有保存的路径且存在，使用它
        if saved_path and os.path.isdir(saved_path):
            return saved_path
        
        # 否则使用默认路径
        default_path = self.get_default_module_path()
        return default_path
    
    def get_default_module_path(self):
        """获取默认的自定义模块路径"""
        # 检测是否为打包环境
        if hasattr(sys, '_MEIPASS'):
            # 打包环境：使用可执行文件所在目录下的user_scripts
            base_path = os.path.dirname(sys.executable)
        else:
            # 开发环境：使用项目根目录下的user_scripts
            base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        
        default_path = os.path.join(base_path, 'user_scripts')
        
        # 如果默认路径不存在，尝试创建
        if not os.path.exists(default_path):
            try:
                os.makedirs(default_path)
            except:
                home = os.path.expanduser("~")
                default_path = os.path.join(home, 'rzera_user_scripts')
                try:
                    os.makedirs(default_path, exist_ok=True)
                except Exception as e:
                    print(f"创建备用默认模块目录失败: {e}")
                    return None
            try:
                # 创建一个示例文件
                readme_path = os.path.join(default_path, 'README.txt')
                with open(readme_path, 'w', encoding='utf-8') as f:
                    f.write("""# 用户自定义Python模块目录

此目录用于存放您的自定义Python脚本和模块。
在Python编辑器中运行脚本时，此目录会被自动添加到Python搜索路径中。

## 使用方法：

1. 在此目录下创建.py文件，定义您的函数、类等
2. 在Python编辑器中，可以直接导入这些模块

## 示例：

假设您创建了 my_tools.py：
```python
def my_function():
    return "Hello from custom module!"
```

在编辑器中使用：
```python
from my_tools import my_function
print(my_function())
```

## 路径管理：

- 当前路径：通过编辑器工具栏的"设置模块路径"按钮查看和修改
- 可以更改为任意有效的目录路径
""")
            except Exception as e:
                print(f"写入README文件失败: {e}")
        
        return default_path
    
    def set_custom_module_path(self):
        """设置自定义模块路径"""
        # 显示当前路径
        current_path = self.custom_module_path or "未设置"
        
        # 选择目录
        selected_path = QFileDialog.getExistingDirectory(
            self,
            "选择自定义模块目录",
            self.custom_module_path or os.path.expanduser("~"),
            QFileDialog.ShowDirsOnly
        )
        
        if selected_path:
            self.custom_module_path = selected_path
            self.settings.setValue('custom_module_path', selected_path)
            self.update_module_path_display()
            QMessageBox.information(
                self,
                "路径已更新",
                f"自定义模块路径已设置为:\n{selected_path}\n\n"
                f"在此目录下的Python文件可以在脚本中直接导入。"
            )
                # 刷新文件树根目录
            self.refresh_file_tree_root()
    
    def update_module_path_display(self):
        """更新模块路径显示"""
        if hasattr(self, 'module_path_label'):
            path_display = self.custom_module_path or "未设置"
            # 如果路径太长，只显示最后部分
            if len(path_display) > 40:
                path_display = "..." + path_display[-37:]
            self.module_path_label.setText(f"模块路径: {path_display}")
            self.module_path_label.setToolTip(f"完整路径: {self.custom_module_path}")

    def update_python_exec_display(self):
        """更新解释器显示标签"""
        try:
            if hasattr(self, 'python_exec_label') and self.python_exec_label is not None:
                val = self.settings.value('python_executable', '')
                if val and os.path.isfile(val):
                    display = val
                    if len(display) > 40:
                        display = '...' + display[-37:]
                else:
                    display = '未设置'
                self.python_exec_label.setText(f"解释器: {display}")
                self.python_exec_label.setToolTip(f"完整路径: {val}")
        except Exception:
            pass

    def set_python_executable_dialog(self):
        """打开文件选择对话以选择 Python 可执行文件并保存到设置"""
        start_dir = self.settings.value('python_executable', '') or os.path.expanduser('~')
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择 Python 解释器",
            start_dir,
            "Python 可执行文件 (python*);;所有文件 (*)"
        )
        if file_path:
            # 保存到设置
            try:
                self.settings.setValue('python_executable', file_path)
                self.update_python_exec_display()
                QMessageBox.information(self, '已保存', f'解释器已保存为：\n{file_path}')
            except Exception as e:
                QMessageBox.critical(self, '错误', f'无法保存解释器路径: {e}')

    def get_python_executable(self):
        """返回用于子进程的 Python 可执行文件路径。

        优先级：
        1. 从 QSettings 中读取 'python_executable'（若存在且有效）
        2. 自动检测项目根下名为 'openRongzai' 的解压环境（常见位置：根/Script/python.exe 或 bin/python）
        3. 回退到当前解释器 `sys.executable`
        """
        # 1) 从设置读取（优先）
        try:
            saved = self.settings.value('python_executable', '')
            if saved and os.path.isfile(saved):
                return saved
        except Exception:
            pass

        # 2) 优先查找 openRongzai：
        #    - 如果应用已被打包（frozen），优先在可执行文件所在目录下查找 ./openRongzai
        #    - 如果未打包（开发模式），优先在项目根目录下查找 ./openRongzai
        try:
            runtime_root = None
            if hasattr(sys, '_MEIPASS') or getattr(sys, 'frozen', False):
                # PyInstaller onefile 解包时，sys.executable 指向临时解压目录，
                # 需要使用 sys.argv[0] 来定位原始 exe 的真实路径（exe 与 openRongzai 同级）
                try:
                    exe_path = None
                    if sys.argv and sys.argv[0]:
                        exe_path = os.path.realpath(sys.argv[0])
                    if exe_path and os.path.isabs(exe_path):
                        runtime_root = os.path.dirname(exe_path)
                    else:
                        runtime_root = os.path.dirname(sys.executable)
                except Exception:
                    runtime_root = os.path.dirname(sys.executable)

            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

            _internal_root = os.path.join(runtime_root or project_root, '_internal')

            # 构建优先搜索顺序
            if runtime_root:
                primary_roots = [runtime_root, _internal_root, project_root, os.getcwd()]
            else:
                primary_roots = [project_root, os.getcwd()]

            # 在 primary_roots 中优先查找 openRongzai 目录并检测常见解释器路径
            for root in primary_roots:
                try:
                    cand_dir = os.path.join(root, 'openRongzai')
                    if os.path.isdir(cand_dir):
                        candidates = [
                            os.path.join(cand_dir, 'python.exe'),
                            os.path.join(cand_dir, 'Scripts', 'python.exe'),
                            os.path.join(cand_dir, 'bin', 'python'),
                            os.path.join(cand_dir, 'bin', 'python3'),
                        ]
                        for c in candidates:
                            if os.path.isfile(c):
                                return c
                except Exception:
                    pass
        except Exception:
            pass

        # 3) 备选：在常见 virtualenv/venv 名称下查找（支持 Linux/Windows）
        try:
            venv_names = ['openRongzai', 'venv', '.venv', 'env', '.env', 'venv3']
            # candidate_roots 用于搜索虚拟环境（尽量包含项目相关路径）
            candidate_roots = []
            if hasattr(sys, '_MEIPASS') or getattr(sys, 'frozen', False):
                # 同上：在 frozen 模式尽量使用 exe 的真实目录而不是 sys.executable 指向的临时目录
                try:
                    exe_path = None
                    if sys.argv and sys.argv[0]:
                        exe_path = os.path.realpath(sys.argv[0])
                    if exe_path and os.path.isabs(exe_path):
                        candidate_roots.append(os.path.dirname(exe_path))
                    else:
                        candidate_roots.append(os.path.dirname(sys.executable))
                except Exception:
                    candidate_roots.append(os.path.dirname(sys.executable))
            candidate_roots.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
            candidate_roots.append(os.getcwd())

            for root in candidate_roots:
                try:
                    for name in venv_names:
                        cand = os.path.join(root, name)
                        if os.path.isdir(cand):
                            for py in ('bin/python', 'bin/python3', 'python.exe', 'Scripts/python.exe'):
                                p = os.path.join(cand, py)
                                if os.path.isfile(p):
                                    return p
                except Exception:
                    pass
        except Exception:
            pass

        # 4) 检查当前 CONDA_PREFIX 或常见用户 conda envs
        try:
            conda_prefix = os.environ.get('CONDA_PREFIX')
            if conda_prefix:
                p = os.path.join(conda_prefix, 'bin', 'python')
                if os.path.isfile(p):
                    return p

            home = os.path.expanduser('~')
            common_conda_roots = [
                os.path.join(home, 'anaconda3', 'envs'),
                os.path.join(home, 'miniconda3', 'envs'),
                os.path.join(home, 'mambaforge', 'envs'),
            ]
            for root in common_conda_roots:
                if os.path.isdir(root):
                    try:
                        for envname in os.listdir(root):
                            p = os.path.join(root, envname, 'bin', 'python')
                            if os.path.isfile(p):
                                return p
                    except Exception:
                        pass
        except Exception:
            pass

        # 5) 最后回退到当前解释器
        return sys.executable
    
    def connect_signals(self):
        """连接信号槽"""
        self.new_button.clicked.connect(self.new_file)
        self.open_button.clicked.connect(self.open_file)
        self.save_button.clicked.connect(self.save_file)
        self.save_as_button.clicked.connect(self.save_as_file)
        
        self.run_button.clicked.connect(self.run_script)
        self.stop_button.clicked.connect(self.stop_script)
        self.clear_output_button.clicked.connect(self.clear_output)
        
        # 添加模块路径设置按钮的连接（如果存在）
        if hasattr(self, 'set_module_path_button'):
            self.set_module_path_button.clicked.connect(self.set_custom_module_path)
        if hasattr(self, 'set_python_exec_button'):
            self.set_python_exec_button.clicked.connect(self.set_python_executable_dialog)
        
    def editor_key_press_event(self, event):
        """处理编辑器按键事件"""
        if event.key() == Qt.Key_F5:
            self.run_script()
        else:
            # 调用原始的按键处理
            if QSCI_AVAILABLE and hasattr(self.code_text_edit, 'setLexer'):
                try:
                    from PyQt5.Qsci import QsciScintilla
                    QsciScintilla.keyPressEvent(self.code_text_edit, event)
                except:
                    QtWidgets.QTextEdit.keyPressEvent(self.code_text_edit, event)
            else:
                QtWidgets.QTextEdit.keyPressEvent(self.code_text_edit, event)

    def toggle_comment(self):
        """切换所选行的注释状态（添加或移除开头的#）。

        支持两种编辑器：QTextEdit（原生）和 QsciScintilla（若已替换）。
        对于 QsciScintilla，我们使用整段文本替换的降级实现，尽量保留光标与选区。
        """
        try:
            # 情况 A：QTextEdit（带 document()/textCursor()）
            if hasattr(self.code_text_edit, 'document') and hasattr(self.code_text_edit, 'textCursor'):
                cursor = self.code_text_edit.textCursor()
                doc = self.code_text_edit.document()

                # 取得选区的起止行
                start = cursor.selectionStart()
                end = cursor.selectionEnd()

                start_block = doc.findBlock(start).blockNumber()
                end_block = doc.findBlock(end).blockNumber()

                # 如果没有选中内容，则操作当前行
                if start == end:
                    end_block = start_block

                # 逐行替换
                for block_no in range(start_block, end_block + 1):
                    block = doc.findBlockByNumber(block_no)
                    block_pos = block.position()
                    block_len = block.length() - 1
                    text = block.text()

                    stripped = text.lstrip()
                    leading_ws = text[: len(text) - len(stripped)]
                    if stripped.startswith('#'):
                        new_text = leading_ws + stripped[1:]
                    else:
                        new_text = leading_ws + '#' + stripped

                    c = self.code_text_edit.textCursor()
                    c.setPosition(block_pos)
                    c.setPosition(block_pos + block_len, QTextCursor.KeepAnchor)
                    c.insertText(new_text)

            else:
                # 情况 B：QScintilla 或其他编辑器：对整段文本或选区做替换
                try:
                    full = self.code_text_edit.text()
                except Exception:
                    # 最后一手：尝试 toPlainText
                    full = self.code_text_edit.toPlainText()

                # 选区文本
                try:
                    has_sel = self.code_text_edit.hasSelectedText()
                    sel = self.code_text_edit.selectedText()
                except Exception:
                    # 如果以上方法不可用，直接注释当前行
                    has_sel = False
                    sel = ''

                if has_sel and sel:
                    # 保存当前的第一可见行和光标位置，防止 setText 导致的滚动
                    first_visible_line = None
                    try:
                        first_visible_line = self.code_text_edit.firstVisibleLine()
                    except Exception:
                        pass
                    
                    # Scintilla 的 selectedText 可能使用 \n 或 Unicode 段落符，统一处理
                    sel_norm = sel.replace('\u2029', '\n')
                    start_idx = full.find(sel_norm)
                    if start_idx == -1:
                        # 无法定位选区，放弃
                        QMessageBox.information(self, '补充', '无法定位选区以切换注释')
                        return
                    end_idx = start_idx + len(sel_norm)

                    before = full[:start_idx]
                    target = full[start_idx:end_idx]
                    after = full[end_idx:]

                    # 对 target 的每一行切换注释
                    lines = target.splitlines(True)
                    new_lines = []
                    for line in lines:
                        stripped = line.lstrip('\r\n')
                        if stripped.lstrip().startswith('#'):
                            # 取消注释 - 移除第一个 #
                            idx = line.find('#')
                            if idx != -1:
                                new_lines.append(line[:idx] + line[idx+1:])
                            else:
                                new_lines.append(line)
                        else:
                            # 添加注释
                            # 保留缩进
                            ws = len(line) - len(line.lstrip())
                            new_lines.append(line[:ws] + '#' + line[ws:])

                    new_target = ''.join(new_lines)
                    new_full = before + new_target + after
                    # 应用文本并尝试恢复选区（简单方式：设置为新_target）
                    try:
                        self.code_text_edit.setText(new_full)
                    except Exception:
                        try:
                            self.code_text_edit.setPlainText(new_full)
                        except Exception as e:
                            QMessageBox.warning(self, '错误', f'无法写回编辑器文本: {e}')
                            return
                    
                    # 恢复原来的滚动位置
                    if first_visible_line is not None:
                        try:
                            self.code_text_edit.setFirstVisibleLine(first_visible_line)
                        except Exception:
                            pass
                else:
                    # 没有选区：注释当前行
                    try:
                        # 尝试使用 Qsci 的 cursor 获取当前行
                        cur_line, cur_index = self.code_text_edit.getCursorPosition()
                        
                        # 保存当前的第一可见行，防止 setCursorPosition 导致的滚动
                        first_visible_line = None
                        try:
                            first_visible_line = self.code_text_edit.firstVisibleLine()
                        except Exception:
                            pass
                        
                        all_text = full
                        lines = all_text.splitlines(True)
                        if cur_line < 0 or cur_line >= len(lines):
                            return
                        line = lines[cur_line]
                        if line.lstrip().startswith('#'):
                            idx = line.find('#')
                            if idx != -1:
                                lines[cur_line] = line[:idx] + line[idx+1:]
                        else:
                            ws = len(line) - len(line.lstrip())
                            lines[cur_line] = line[:ws] + '#' + line[ws:]

                        new_full = ''.join(lines)
                        try:
                            self.code_text_edit.setText(new_full)
                        except Exception:
                            self.code_text_edit.setPlainText(new_full)
                        
                        # 恢复光标到原位置
                        try:
                            self.code_text_edit.setCursorPosition(cur_line, cur_index)
                        except Exception:
                            pass
                        
                        # 恢复原来的滚动位置（防止 setCursorPosition 自动滚动）
                        if first_visible_line is not None:
                            try:
                                self.code_text_edit.setFirstVisibleLine(first_visible_line)
                            except Exception:
                                pass
                    except Exception:
                        QMessageBox.information(self, '提示', '当前编辑器不支持注释切换')

        except Exception as e:
            QMessageBox.warning(self, '错误', f'切换注释失败: {e}')

                
    def new_file(self):
        """新建文件"""
        self.code_text_edit.clear()
        self.current_file = None
        self.status_label.setText("新建文件")
        
    def open_file(self):
        """打开文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "打开Python文件", "", "Python文件 (*.py);;所有文件 (*)"
        )
        
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                self.code_text_edit.setText(content)
                self.current_file = file_path
                self.status_label.setText(f"已打开: {os.path.basename(file_path)}")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"无法打开文件: {str(e)}")
                
    def save_file(self):
        """保存文件"""
        if self.current_file:
            self.save_to_file(self.current_file)
        else:
            self.save_as_file()
            
    def save_as_file(self):
        """另存为文件"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "保存Python文件", "", "Python文件 (*.py);;所有文件 (*)"
        )
        
        if file_path:
            self.save_to_file(file_path)
            self.current_file = file_path
            
    def save_to_file(self, file_path):
        """保存到指定文件"""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(self.code_text_edit.toPlainText())
            self.status_label.setText(f"已保存: {os.path.basename(file_path)}")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"无法保存文件: {str(e)}")
            
    def run_script(self):
        """运行脚本"""
        if self.executor_thread and self.executor_thread.isRunning():
            QMessageBox.warning(self, "警告", "有脚本正在运行中，请等待完成或停止当前执行")
            return
            
        code = self.code_text_edit.toPlainText().strip()
        if not code:
            QMessageBox.information(self, "提示", "请输入要执行的代码")
            return
        # 清空输出
        self.output_text_edit.clear()
        self.output_text_edit.append(">>> 开始执行脚本...\n")
        
        # 显示自定义模块路径信息
        if self.custom_module_path and os.path.isdir(self.custom_module_path):
            self.append_output(f">>> 自定义模块路径: {self.custom_module_path}\n")
        
        # 强制使用子进程执行：显示子进程模式的说明
        self.append_output(">>> 子进程执行模式 - 优势:\n")
        self.append_output(">>> • 🖼️ matplotlib图形可正常显示窗口\n") 
        self.append_output(">>> • 🛡️ 执行环境完全隔离，更安全\n")
        self.append_output(">>> • 🧪 可用于测试可能不稳定的代码\n")
        self.append_output(">>> • ⚠️ 注意: 无法访问主程序变量和数据\n")
        self.append_output("\n")
        
        # 确定要使用的 Python 可执行文件（优先设置 -> 自动检测 openRongzai -> 回退 sys.executable）
        python_exec = self.get_python_executable()

        # 显示将使用的解释器，便于用户验证
        self.append_output(f">>> 使用解释器: {python_exec}\n")

        # 创建执行线程，传递自定义模块路径、当前文件路径和 python 可执行文件（仅子进程）
        self.executor_thread = ScriptExecutor(code, self.custom_module_path, self.current_file, python_executable=python_exec)
        self.executor_thread.output_signal.connect(self.append_output)
        self.executor_thread.error_signal.connect(self.append_error)
        self.executor_thread.finished_signal.connect(self.execution_finished)
        
        # 更新界面状态
        self._execution_in_progress = True
        self.run_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.status_label.setText("脚本执行中...")
        print("[DEBUG] 脚本执行线程已创建，准备启动")
        
        # 启动执行
        self.executor_thread.start()
        
    def stop_script(self):
        """停止脚本执行"""
        if self.executor_thread and self.executor_thread.isRunning():
            try:
                # 请求线程内部停止子进程
                try:
                    self.executor_thread.stop(force=True, wait=2.0)
                except Exception:
                    pass
                # 等待线程退出
                self.executor_thread.wait(5000)  # 最多等5秒
            except Exception:
                pass
            self.append_error(">>> 脚本执行已被用户停止\n")
            self.execution_finished()
            
    def clear_output(self):
        """清空输出"""
        self.output_text_edit.clear()
        
    def check_matplotlib_usage(self, code):
        """检查代码中是否包含matplotlib绘图操作"""
        import re
        
        # 检查matplotlib相关的导入和绘图操作
        matplotlib_patterns = [
            r'import\s+matplotlib',
            r'from\s+matplotlib',
            r'import\s+matplotlib\.pyplot',
            r'plt\.show\s*\(',
            r'pyplot\.show\s*\(',
            r'plt\.figure\s*\(',
            r'plt\.plot\s*\(',
            r'plt\.scatter\s*\(',
            r'plt\.bar\s*\(',
            r'plt\.hist\s*\(',
            r'plt\.imshow\s*\(',
            r'plt\.savefig\s*\(',
        ]
        
        found_imports = []
        found_plots = []
        
        # 逐行检查代码
        lines = code.split('\n')
        for i, line in enumerate(lines, 1):
            line_clean = line.strip()
            if not line_clean or line_clean.startswith('#'):
                continue
                
            # 检查导入
            for pattern in matplotlib_patterns[:3]:
                if re.search(pattern, line_clean, re.IGNORECASE):
                    found_imports.append(f"第{i}行: {line_clean}")
                    break
            
            # 检查绘图操作
            for pattern in matplotlib_patterns[3:]:
                if re.search(pattern, line_clean, re.IGNORECASE):
                    found_plots.append(f"第{i}行: {line_clean}")
                    
        # 如果发现matplotlib使用，返回警告信息
        if found_imports or found_plots:
            warning_msg = "检测到matplotlib绘图操作:"
            
            if found_imports:
                warning_msg += f"\n\n导入语句:\n" + "\n".join(found_imports[:3])
                if len(found_imports) > 3:
                    warning_msg += f"\n... (共{len(found_imports)}处导入)"
                    
            if found_plots:
                warning_msg += f"\n\n绘图操作:\n" + "\n".join(found_plots[:3])
                if len(found_plots) > 3:
                    warning_msg += f"\n... (共{len(found_plots)}处绘图)"
                    
            return warning_msg
            
        return None
        
    def append_output(self, text):
        """添加标准输出"""
        self.output_text_edit.setTextColor(Qt.white)
        self.output_text_edit.append(text)
        
    def append_error(self, text):
        """添加错误输出"""
        self.output_text_edit.setTextColor(Qt.red)
        self.output_text_edit.append(text)
        
    def closeEvent(self, event):
        """重写关闭事件，防止脚本执行期间意外关闭"""
        if self._execution_in_progress:
            print("[DEBUG] 检测到脚本执行期间窗口关闭请求，询问用户确认")
            from PyQt5.QtWidgets import QMessageBox
            reply = QMessageBox.question(
                self, 
                '确认关闭',
                '脚本正在执行中，确定要关闭编辑器吗？',
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                # 停止执行线程
                if self.executor_thread and self.executor_thread.isRunning():
                    self.executor_thread.terminate()
                    self.executor_thread.wait(3000)
                event.accept()
            else:
                event.ignore()
        else:
            # 正常关闭
            event.accept()
        self.output_text_edit.setTextColor(Qt.white)
        
    def execution_finished(self):
        """脚本执行完成"""
        self._execution_in_progress = False
        self.run_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.status_label.setText("脚本执行完成")
        self.append_output("\n>>> 脚本执行完成\n")
        
        # 确保窗口保持可见
        if not self.isVisible():
            print("[DEBUG] 警告：检测到窗口被隐藏，正在恢复显示")
            self.show()
            self.raise_()
            self.activateWindow()
        else:
            print("[DEBUG] 脚本执行完成，窗口正常可见")

# 为了集成到主窗口，创建一个简单的入口函数
def create_code_editor_window(parent=None):
    """创建代码编辑器窗口"""
    editor = CodeEditor(parent)
    return editor

# if __name__ == "__main__":
#     import sys
#     from PyQt5.QtWidgets import QApplication
    
#     app = QApplication(sys.argv)
#     editor = CodeEditor()
#     editor.show()
#     sys.exit(app.exec_())