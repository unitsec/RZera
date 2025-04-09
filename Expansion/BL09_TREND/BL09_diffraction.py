from PyQt5 import QtWidgets
from PyQt5 import QtGui
from PyQt5.QtCore import Qt
from BL09_TREND.ui.ui_BL09_diffraction import Ui_Form
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
from BL09_TREND.workers.browse_file import browse_file
from BL09_TREND.workers.combobox_operation import browse_mode_check,change_rebin_mode
from BL09_TREND.workers.checkbox_operation import checkbox_operation
from utils.NonZeroIntValidator import NonZeroIntValidator
from BL09_TREND.workers.plot_item_operation import change_item
from BL09_TREND.workers.data_plot import data_plot
from BL09_TREND.workers.ui_mapping import save_diff_config,load_diff_config
from BL09_TREND.workers.data_save import save_diff
import BL09_TREND.workers.diffraction_thread
import json
from utils.redisHelper import getRedisHelper
import traceback
import os
import sys


class diffraction(QtWidgets.QWidget, Ui_Form):
    def __init__(self, parent=None):
        super(diffraction, self).__init__(parent)
        self.setupUi(self)
        self.mainwindow = self.parent()
        self.plot_list_dict = {'sam_list': {}, 'other_list': {}}
        self.sam_list_dict = self.plot_list_dict['sam_list']
        self.other_list_dict = self.plot_list_dict['other_list']
        self.diff_config = {'sam_fn': [], 'v_fn': [], 'samBG_fn': [], 'vBG_fn': []}
        self.browse_run = browse_file()
        doubleValidator = QtGui.QDoubleValidator()  # 创建一个 QDoubleValidator 对象

        # 如果是 PyInstaller 打包后的临时目录中运行
        if getattr(sys, 'frozen', False):
            # 获取 PyInstaller 打包后的临时目录路径
            temp_dir = getattr(sys, '_MEIPASS', os.path.abspath(os.path.dirname(sys.executable)))
            BL09_config = os.path.join(temp_dir, 'BL09_base.json')
        else:
            # 如果是在源码中运行
            temp_dir = os.path.abspath(os.path.dirname(__file__))
            BL09_config = os.path.join(temp_dir, '..', 'CSNS_Alg','configure', 'BL09_base.json')

        with open(BL09_config, 'r', encoding='utf-8') as json_file:
            self.BL09_configure = json.load(json_file)

        # # 如果是 PyInstaller 打包后的临时目录中运行
        # if getattr(sys, 'frozen', False):
        #     # 获取 PyInstaller 打包后的临时目录路径
        #     temp_dir = getattr(sys, '_MEIPASS', os.path.abspath(os.path.dirname(sys.executable)))
        #     redis_config = os.path.join(temp_dir, 'online', 'configure', 'redis_hrd.json')
        # else:
        #     # 如果是在源码中运行
        #     temp_dir = os.path.abspath(os.path.dirname(__file__))
        #     redis_config = os.path.join(temp_dir, 'online', 'configure', 'redis_hrd.json')
        #
        # with open(redis_config, 'r', encoding='utf-8') as json_file:
        #     self.redis_configure = json.load(json_file)

        ############################# get redis information #################################
        # # 如果是 PyInstaller 打包后的临时目录中运行
        # if getattr(sys, 'frozen', False):
        #     # 获取 PyInstaller 打包后的临时目录路径
        #     temp_dir = getattr(sys, '_MEIPASS', os.path.abspath(os.path.dirname(sys.executable)))
        #     redis_conf = os.path.join(temp_dir, 'conf_redis.json')
        # else:
        #     # 如果是在源码中运行
        #     temp_dir = os.path.abspath(os.path.dirname(__file__))
        #     redis_conf = os.path.join(os.path.dirname(temp_dir), 'utils', 'conf_redis.json')
        #
        # # redis_conf = "./utils/conf_redis.json"
        # with open(redis_conf, "r") as jf:
        #     rdsConf = json.load(jf)
        # self.rds = getRedisHelper(rdsConf)

        ################################ 初始化绘图区域 ######################################
        # 创建 Figure 和 FigureCanvas 对象
        self.figure = Figure()
        self.canvas = FigureCanvas(self.figure)
        self.ax = self.figure.add_subplot(111)

        # 将 FigureCanvas 添加到 graphicView 容器中
        self.graphicView.setLayout(QtWidgets.QVBoxLayout())
        self.graphicView.layout().addWidget(self.canvas)

        # 创建 NavigationToolbar 对象并添加到 graphicView 容器中
        self.toolbar = NavigationToolbar(self.canvas, self)
        self.graphicView.layout().addWidget(self.toolbar)

        self.figure.tight_layout()  # 设置为紧凑布局
        self.figure.subplots_adjust(bottom=0.17)  # 可以调整这个值以设置适当的空隙
        # ####################### 根据mainwindow中offline和online的切换控制sample_run相关控件的状态 #############################
        # self.mainwindow = self.parent()
        # self.mainwindow.mode.currentTextChanged.connect(
        #     lambda: mode_check(self.mainwindow.mode.currentText(),self.sample_run_button,
        #                                          self.sample_run_text,self.is_batch))  # 改变sample_run相关控件的状态
        # mode_check(
        #     self.mainwindow.mode.currentText(),self.sample_run_button,self.sample_run_text,self.is_batch) # 初始化sample_run相关控件的状态

        #################################### 配置 Sample 及其 Background  #######################################################
        ####################### 读取sample_run文件 #############################
        self.sample_run_button.clicked.connect(
            lambda: (self.browse_run.select_nxsfiles(self.sample_run_text,self.diff_config['sam_fn']),print(self.diff_config['sam_fn'])))
        # self.clear_button.clicked.connect(
        #     lambda: lineedit_clear(self.diff_config['sam_fn'], self.sample_run_text))
        #################################### 读取 Sample-bkg  #################################
        # 初始化设置hold_run_button、hold_run_text、hold_run_mode为不可用, hold_run_filePath为空列表
        self.sambkg_button.setEnabled(False)
        self.sambkg_text.setEnabled(False)
        self.sambkg_mode.setEnabled(False)
        self.sam_bkg_text.setEnabled(False)
        self.sam_bkg_check.setEnabled(False)

        self.sam_bkg_text.setValidator(doubleValidator)

        self.checkbox_operation = checkbox_operation()  # 实例化checkbox_operation
        self.sambkg_check.stateChanged.connect(
            lambda: (self.checkbox_operation.check_set(self.sambkg_check, pushbutton=self.sambkg_button,
                                                      lineedit=self.sambkg_text,
                                                      combobox=self.sambkg_mode),
                     self.checkbox_operation.scale_use_check(self.sambkg_check, self.sam_bkg_text),
                     self.checkbox_operation.sync_checkboxes(self.sambkg_check, self.sam_bkg_check)))
        self.sambkg_mode.currentTextChanged.connect(
            lambda: (self.sambkg_text.setText(''),
                     self.diff_config.update({'samBG_fn': []})))
        self.sambkg_button.clicked.connect(
            lambda: browse_mode_check(self.sambkg_mode, self.diff_config['samBG_fn'], self.sambkg_text,
                                      self))

        #################################### 配置 Van 和 vanbkg  #######################################################

            #################################### 读取 Van  #################################
        # 初始化设置van_run_button、van_run_text、van_run_mode为不可用, van_run_filePath为空列表
        self.v.setEnabled(False)
        self.v.setChecked(True)
        self.vni.setEnabled(False)
        self.num_dens.setEnabled(False)
        self.num_dens.setText(str(self.BL09_configure['vanadium_correction']['density_num']))
        self.num_dens.setValidator(doubleValidator)
        self.van_radius.setEnabled(False)
        self.van_radius.setText(str(self.BL09_configure['vanadium_correction']['radius']))
        self.van_radius.setValidator(doubleValidator)
        self.beam_height.setEnabled(False)
        self.beam_height.setText(str(self.BL09_configure['vanadium_correction']['beam_height']))
        self.beam_height.setValidator(doubleValidator)
        self.van_run_button.setEnabled(False)
        self.van_run_text.setEnabled(False)
        self.van_run_mode.setEnabled(False)
        self.sam_van_check.setEnabled(False)

        self.checkbox_operation = checkbox_operation()  # 实例化checkbox_operation
        self.v_check.stateChanged.connect(
            lambda: (self.checkbox_operation.check_set(self.v_check, self.van_run_button, self.van_run_text,
                                                      self.van_run_mode),
                     self.checkbox_operation.check_set(self.v_check, radiobutton=self.v),
                     self.checkbox_operation.check_set(self.v_check, radiobutton=self.vni),
                     self.checkbox_operation.check_set(self.v_check, lineedit=self.num_dens),
                     self.checkbox_operation.check_set(self.v_check, lineedit=self.van_radius),
                     self.checkbox_operation.check_set(self.v_check, lineedit=self.beam_height),
                     self.checkbox_operation.check_set(self.v_check,checkbox2=self.vbkg_check),
                     self.checkbox_operation.check_set(self.vbkg_check, pushbutton=self.vanbkg_button,
                                                       lineedit=self.vanbkg_text,
                                                       combobox=self.vanbkg_mode),
                     self.checkbox_operation.sync_checkboxes(self.v_check, self.sam_van_check)))  # 根据 v_check 的勾选状态设置van_run_button、van_run_text、van_run_mode的可用状态
        try:
            self.van_run_mode.currentTextChanged.connect(
                lambda: (self.van_run_text.setText(''), self.diff_config.update({'v_fn': []})))  # van_run_mode的选择变化会清空van_run_filePath和van_run_text
        except Exception as e:
            print(f"An error occurred: {e}")
            traceback.print_exc()  # 打印异常的堆栈跟踪
        self.van_run_button.clicked.connect(
            lambda: browse_mode_check(self.van_run_mode, self.diff_config['v_fn'], self.van_run_text,
                                                     self))  # 点击van_run_button后，根据van_run_mode选择导入文件的模式

            #################################### 读取 vanbkg  #################################
        self.vanbkg_button.setEnabled(False)
        self.vanbkg_text.setEnabled(False)
        self.vanbkg_mode.setEnabled(False)
        self.van_bkg_text.setEnabled(False)
        self.van_bkg_check.setEnabled(False)

        self.van_bkg_text.setValidator(doubleValidator)

        self.checkbox_operation = checkbox_operation()  # 实例化checkbox_operation
        self.vbkg_check.stateChanged.connect(
            lambda: (self.checkbox_operation.check_set(self.vbkg_check, pushbutton=self.vanbkg_button, lineedit=self.vanbkg_text,
                                                      combobox=self.vanbkg_mode),
                     self.checkbox_operation.scale_use_check(self.vbkg_check, self.van_bkg_text),
                     self.checkbox_operation.sync_checkboxes(self.vbkg_check, self.van_bkg_check)))
        self.vanbkg_mode.currentTextChanged.connect(
            lambda: (self.vanbkg_text.setText(''), self.diff_config.update({'vBG_fn': []})))
        self.vanbkg_button.clicked.connect(
            lambda: browse_mode_check(self.vanbkg_mode, self.diff_config['vBG_fn'], self.vanbkg_text,
                                                     self))

        ####################### 读取instrument path #############################
        self.instru_path_button.clicked.connect(lambda: self.browse_run.select_folder(self.param_path))

        ####################### 读取 offset_file 文件 #############################
        self.checkbox_operation = checkbox_operation()
        self.offset_file_button.setEnabled(False)
        self.cal_path.setEnabled(False)
        self.has_cal.stateChanged.connect(
            lambda: self.checkbox_operation.check_set(self.has_cal, self.offset_file_button,
                                                      self.cal_path))
        self.offset_file_button.clicked.connect(lambda: self.browse_run.select_folder(self.cal_path))

        ####################### 设置wave_start和wave_end #############################
        # 创建一个 QDoubleValidator 对象
        doubleValidator = QtGui.QDoubleValidator()
        # 将 doubleValidator 设置到 QLineEdit 控件上 (只能输入浮点数)
        self.wave_start_text.setValidator(doubleValidator)
        self.wave_end_text.setValidator(doubleValidator)

        # ####################### 设置 T0_offset #############################
        # # 创建一个 QDoubleValidator 对象
        # doubleValidator = QtGui.QDoubleValidator()
        # # 将 doubleValidator 设置到 QLineEdit 控件上 (只能输入浮点数)
        # self.T0_offset_text.setValidator(doubleValidator)
        # # T0_offset 初始值设为0
        # self.T0_offset_text.setText('0.0')





        #################################### 配置 d_rebin  #######################################################
        self.comboBox_1_start.setValidator(doubleValidator)  # 将doubleValidator设置到 QLineEdit 控件上(只能输入浮点数)
        self.comboBox_1_end.setValidator(doubleValidator)
        self.comboBox_2_start.setValidator(doubleValidator)
        self.comboBox_2_end.setValidator(doubleValidator)
        self.comboBox_3_start.setValidator(doubleValidator)
        self.comboBox_3_end.setValidator(doubleValidator)
        self.comboBox_4_start.setValidator(doubleValidator)
        self.comboBox_4_end.setValidator(doubleValidator)
        self.comboBox_5_start.setValidator(doubleValidator)
        self.comboBox_5_end.setValidator(doubleValidator)
        self.comboBox_6_start.setValidator(doubleValidator)
        self.comboBox_6_end.setValidator(doubleValidator)

        self.nozerointvalidator = NonZeroIntValidator(1, 2147483647)  # 实例化自定义的NonZeroIntValidator
        self.comboBox_1_number.setValidator(self.nozerointvalidator)  # 将NonZeroIntValidator设置到 QLineEdit 控件上(只能输入正整数)
        self.comboBox_2_number.setValidator(self.nozerointvalidator)
        self.comboBox_3_number.setValidator(self.nozerointvalidator)
        self.comboBox_4_number.setValidator(self.nozerointvalidator)
        self.comboBox_5_number.setValidator(self.nozerointvalidator)
        self.comboBox_6_number.setValidator(self.nozerointvalidator)

        self.checkbox_operation = checkbox_operation()
        self.checkbox_operation.check_set(self.comboBox_1_check, lineedit=self.comboBox_1_start)
        self.checkbox_operation.check_set(self.comboBox_1_check, lineedit=self.comboBox_1_end)
        self.checkbox_operation.check_set(self.comboBox_1_check, lineedit=self.comboBox_1_number)
        self.checkbox_operation.check_set(self.comboBox_1_check, combobox=self.comboBox_1)
        self.checkbox_operation.check_set(self.comboBox_2_check, lineedit=self.comboBox_2_start)
        self.checkbox_operation.check_set(self.comboBox_2_check, lineedit=self.comboBox_2_end)
        self.checkbox_operation.check_set(self.comboBox_2_check, lineedit=self.comboBox_2_number)
        self.checkbox_operation.check_set(self.comboBox_2_check, combobox=self.comboBox_2)
        self.checkbox_operation.check_set(self.comboBox_3_check, lineedit=self.comboBox_3_start)
        self.checkbox_operation.check_set(self.comboBox_3_check, lineedit=self.comboBox_3_end)
        self.checkbox_operation.check_set(self.comboBox_3_check, lineedit=self.comboBox_3_number)
        self.checkbox_operation.check_set(self.comboBox_3_check, combobox=self.comboBox_3)
        self.checkbox_operation.check_set(self.comboBox_4_check, lineedit=self.comboBox_4_start)
        self.checkbox_operation.check_set(self.comboBox_4_check, lineedit=self.comboBox_4_end)
        self.checkbox_operation.check_set(self.comboBox_4_check, lineedit=self.comboBox_4_number)
        self.checkbox_operation.check_set(self.comboBox_4_check, combobox=self.comboBox_4)
        self.checkbox_operation.check_set(self.comboBox_5_check, lineedit=self.comboBox_5_start)
        self.checkbox_operation.check_set(self.comboBox_5_check, lineedit=self.comboBox_5_end)
        self.checkbox_operation.check_set(self.comboBox_5_check, lineedit=self.comboBox_5_number)
        self.checkbox_operation.check_set(self.comboBox_5_check, combobox=self.comboBox_5)
        self.checkbox_operation.check_set(self.comboBox_6_check, lineedit=self.comboBox_6_start)
        self.checkbox_operation.check_set(self.comboBox_6_check, lineedit=self.comboBox_6_end)
        self.checkbox_operation.check_set(self.comboBox_6_check, lineedit=self.comboBox_6_number)
        self.checkbox_operation.check_set(self.comboBox_6_check, combobox=self.comboBox_6)
        self.comboBox_1_check.stateChanged.connect(
            lambda: (self.checkbox_operation.set_bank(self.comboBox_1_check, self.comboBox_1, self.comboBox_1_start, config=self.BL09_configure),
                     self.checkbox_operation.set_bank(self.comboBox_1_check, self.comboBox_1, self.comboBox_1_end, config=self.BL09_configure),
                     self.checkbox_operation.set_bank(self.comboBox_1_check, self.comboBox_1, self.comboBox_1_number, config=self.BL09_configure),
                     self.checkbox_operation.check_set(self.comboBox_1_check, combobox=self.comboBox_1)
                     ))
        self.comboBox_2_check.stateChanged.connect(
            lambda: (self.checkbox_operation.set_bank(self.comboBox_2_check, self.comboBox_2, self.comboBox_2_start, config=self.BL09_configure),
                     self.checkbox_operation.set_bank(self.comboBox_2_check, self.comboBox_2, self.comboBox_2_end, config=self.BL09_configure),
                     self.checkbox_operation.set_bank(self.comboBox_2_check, self.comboBox_2, self.comboBox_2_number, config=self.BL09_configure),
                     self.checkbox_operation.check_set(self.comboBox_2_check, combobox=self.comboBox_2)
                     ))
        self.comboBox_3_check.stateChanged.connect(
            lambda: (self.checkbox_operation.set_bank(self.comboBox_3_check, self.comboBox_3, self.comboBox_3_start, config=self.BL09_configure),
                     self.checkbox_operation.set_bank(self.comboBox_3_check, self.comboBox_3, self.comboBox_3_end, config=self.BL09_configure),
                     self.checkbox_operation.set_bank(self.comboBox_3_check, self.comboBox_3, self.comboBox_3_number, config=self.BL09_configure),
                     self.checkbox_operation.check_set(self.comboBox_3_check, combobox=self.comboBox_3)
                     ))
        self.comboBox_4_check.stateChanged.connect(
            lambda: (self.checkbox_operation.set_bank(self.comboBox_4_check, self.comboBox_4, self.comboBox_4_start, config=self.BL09_configure),
                     self.checkbox_operation.set_bank(self.comboBox_4_check, self.comboBox_4, self.comboBox_4_end, config=self.BL09_configure),
                     self.checkbox_operation.set_bank(self.comboBox_4_check, self.comboBox_4, self.comboBox_4_number, config=self.BL09_configure),
                     self.checkbox_operation.check_set(self.comboBox_4_check, combobox=self.comboBox_4)
                     ))
        self.comboBox_5_check.stateChanged.connect(
            lambda: (self.checkbox_operation.set_bank(self.comboBox_5_check, self.comboBox_5, self.comboBox_5_start, config=self.BL09_configure),
                     self.checkbox_operation.set_bank(self.comboBox_5_check, self.comboBox_5, self.comboBox_5_end, config=self.BL09_configure),
                     self.checkbox_operation.set_bank(self.comboBox_5_check, self.comboBox_5, self.comboBox_5_number, config=self.BL09_configure),
                     self.checkbox_operation.check_set(self.comboBox_5_check, combobox=self.comboBox_5)
                     ))
        self.comboBox_6_check.stateChanged.connect(
            lambda: (self.checkbox_operation.set_bank(self.comboBox_6_check, self.comboBox_6, self.comboBox_6_start, config=self.BL09_configure),
                     self.checkbox_operation.set_bank(self.comboBox_6_check, self.comboBox_6, self.comboBox_6_end, config=self.BL09_configure),
                     self.checkbox_operation.set_bank(self.comboBox_6_check, self.comboBox_6, self.comboBox_6_number, config=self.BL09_configure),
                     self.checkbox_operation.check_set(self.comboBox_6_check, combobox=self.comboBox_6)
                     ))

        ######################################### 配置 reduction button  ################################################
        self.reduction_thread = BL09_TREND.workers.diffraction_thread.start_reduction_thread()  # 实例化start_reduction_thread
        self.Reduction.clicked.connect(
            lambda: self.reduction_thread.start_reduction(
                self, self.diff_config,
                self.plot_list_dict, self.sam_list,self.filterbox,self.other_list, self.Reduction
                )
        )  # 保存配置的字典文件到json, 然后进行规约

        ######################################### 配置 save_config  #######################################################
        self.save_config.clicked.connect(lambda: save_diff_config(self, self.diff_config, self.BL09_configure))

        ######################################### 配置 load_config  #######################################################
        self.Load_Config.clicked.connect(lambda:(load_diff_config(self),print(self.diff_config)))  # 从配置文件读取配置

        ######################################### 配置 plot_list  #######################################################
        # 添加 "ALL" 条目到 sam_list 的第一行
        all_item = QtWidgets.QListWidgetItem("ALL")
        all_item.setFlags(all_item.flags() | Qt.ItemIsUserCheckable)
        all_item.setCheckState(Qt.Unchecked)
        self.sam_list.insertItem(0, all_item)

        # 添加 "ALL" 条目到 other_list 的第一行
        all_item_v = QtWidgets.QListWidgetItem("ALL")
        all_item_v.setFlags(all_item_v.flags() | Qt.ItemIsUserCheckable)
        all_item_v.setCheckState(Qt.Unchecked)
        self.other_list.insertItem(0, all_item_v)

        self.change_sam_item = change_item(self.sam_list, self.sam_list_dict)  # 实例化change_item
        self.sam_list.itemChanged.connect(self.change_sam_item.handle_item_changed)  # 配置sam_list中item的变化

        self.change_other_item = change_item(self.other_list, self.other_list_dict)  # 实例化change_item
        self.other_list.itemChanged.connect(self.change_other_item.handle_item_changed)  # 配置other_list中item的变化

        self.filterbox.itemChecked.connect(self.change_sam_item.filter_items)

        ######################################### 配置 plot_button  #######################################################
        self.data_plot = data_plot()  # 实例化data_plot
        self.plot_button.clicked.connect(lambda:(
            self.data_plot.plot_data(self.sam_list,self.sam_list_dict,self.canvas,self.ax, 'd (Å)', 'Intensity (a.u.)'),
            self.data_plot.plot_data(self.other_list,self.other_list_dict,self.canvas,self.ax, 'd (Å)', 'Intensity (a.u.)',False)
        )
                                         )  # 根据plot_list中勾选的items画图

        ######################################### 配置 Save  #######################################################
        self.save_button.clicked.connect(lambda:
            save_diff(self, self.diff_config,
                      self.sam_list,self.other_list, self.plot_list_dict)
                                         )

        ######################################### 配置 Delete  #######################################################
        self.del_button.clicked.connect(lambda: (self.change_sam_item.delete_item(self.sam_list_dict),
                                                 self.change_other_item.delete_item(self.other_list_dict)))
