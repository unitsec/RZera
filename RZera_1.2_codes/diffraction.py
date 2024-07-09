from PyQt5 import QtWidgets
from PyQt5 import QtGui
from PyQt5.QtCore import Qt
from ui_design.ui_diffraction import Ui_Form
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
from workers.browse_file import browse_file
from workers.combobox_operation import browse_mode_check,change_rebin_mode
from workers.checkbox_operation import checkbox_operation
from utils_ui.NonZeroIntValidator import NonZeroIntValidator
from workers.plot_item_operation import change_item
from workers.data_plot import data_plot
from workers.ui_mapping import save_diff_config,load_diff_config
from workers.data_save import save_diff
import workers.diffraction_thread
import json
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
        self.diff_config = {'sam_fn': [], 'v_fn': [], 'hold_fn': []}
        self.browse_run = browse_file()

        if getattr(sys, 'frozen', False):
            temp_dir = getattr(sys, '_MEIPASS', os.path.abspath(os.path.dirname(sys.executable)))
            bl16_config = os.path.join(temp_dir, 'bl16_config.json')
        else:
            temp_dir = os.path.abspath(os.path.dirname(__file__))
            bl16_config = os.path.join(temp_dir, 'utils_ui', 'bl16_config.json')

        with open(bl16_config, 'r', encoding='utf-8') as json_file:
            self.bl16_configure = json.load(json_file)

        self.figure = Figure()
        self.canvas = FigureCanvas(self.figure)
        self.ax = self.figure.add_subplot(111)
        self.graphicView.setLayout(QtWidgets.QVBoxLayout())
        self.graphicView.layout().addWidget(self.canvas)
        self.toolbar = NavigationToolbar(self.canvas, self)
        self.graphicView.layout().addWidget(self.toolbar)
        self.figure.tight_layout()
        self.figure.subplots_adjust(bottom=0.17)

        self.sample_run_button.clicked.connect(
            lambda: (self.browse_run.select_nxsfiles(self.sample_run_text,self.diff_config['sam_fn']),print(self.diff_config['sam_fn'])))

        self.instru_path_button.clicked.connect(lambda: self.browse_run.select_folder(self.instru_path_text))

        self.checkbox_operation = checkbox_operation()
        self.offset_file_button.setEnabled(False)
        self.offset_file_text.setEnabled(False)
        self.offset_correction_check.stateChanged.connect(
            lambda: self.checkbox_operation.check_set(self.offset_correction_check, self.offset_file_button,
                                                      self.offset_file_text,
                                                      use_combobox=False))
        self.offset_file_button.clicked.connect(lambda: self.browse_run.select_folder(self.offset_file_text))

        doubleValidator = QtGui.QDoubleValidator()
        self.wave_start_text.setValidator(doubleValidator)
        self.wave_end_text.setValidator(doubleValidator)

        doubleValidator = QtGui.QDoubleValidator()
        self.T0_offset_text.setValidator(doubleValidator)
        self.T0_offset_text.setText('0.0')

        self.van_run_button.setEnabled(False)
        self.van_run_text.setEnabled(False)
        self.van_run_mode.setEnabled(False)

        self.checkbox_operation = checkbox_operation()
        self.v_check.stateChanged.connect(
            lambda: self.checkbox_operation.check_set(self.v_check, self.van_run_button, self.van_run_text,
                                                      use_combobox=True,
                                                      combobox=self.van_run_mode))

        self.van_run_mode.currentTextChanged.connect(
            lambda: (self.van_run_text.setText(''), self.diff_config.update({'v_fn': []})))
        self.van_run_button.clicked.connect(
            lambda: browse_mode_check(self.van_run_mode, self.diff_config['v_fn'], self.van_run_text,
                                                     self))

        self.hold_run_button.setEnabled(False)
        self.hold_run_text.setEnabled(False)
        self.hold_run_mode.setEnabled(False)

        self.checkbox_operation = checkbox_operation()
        self.hold_check.stateChanged.connect(
            lambda: self.checkbox_operation.check_set(self.hold_check, self.hold_run_button, self.hold_run_text,
                                                      use_combobox=True,
                                                      combobox=self.hold_run_mode))
        self.hold_run_mode.currentTextChanged.connect(
            lambda: (self.hold_run_text.setText(''), self.diff_config.update({'hold_fn': []})))
        self.hold_run_button.clicked.connect(
            lambda: browse_mode_check(self.hold_run_mode, self.diff_config['hold_fn'], self.hold_run_text,
                                                     self))  # 点击hold_run_button后，根据hold_run_mode选择导入文件的模式


        self.sample_hold_text.setEnabled(False)
        self.v_hold_text.setEnabled(False)

        doubleValidator = QtGui.QDoubleValidator()
        self.sample_hold_text.setValidator(doubleValidator)
        self.v_hold_text.setValidator(doubleValidator)

        self.checkbox_operation = checkbox_operation()
        self.v_check.stateChanged.connect(
            lambda: self.checkbox_operation.scale_use_check(self.hold_check, self.v_check, self.sample_hold_text,
                                                            self.v_hold_text))
        self.hold_check.stateChanged.connect(
            lambda: self.checkbox_operation.scale_use_check(self.hold_check, self.v_check, self.sample_hold_text,
                                                            self.v_hold_text))

        doubleValidator = QtGui.QDoubleValidator()
        self.d_rebin_start.setValidator(doubleValidator)
        self.d_rebin_end.setValidator(doubleValidator)

        self.nozerointvalidator = NonZeroIntValidator(1, 2147483647)
        self.d_rebin_number.setValidator(self.nozerointvalidator)
        change_rebin_mode(
            self.diff_bankname.currentText(), self.d_rebin_start, self.d_rebin_end, self.d_rebin_number,self.bl16_configure)
        self.diff_bankname.currentTextChanged.connect(
            lambda: change_rebin_mode(
                self.diff_bankname.currentText(), self.d_rebin_start, self.d_rebin_end, self.d_rebin_number,self.bl16_configure))

        self.reduction_thread = workers.diffraction_thread.start_reduction_thread()
        self.Reduction.clicked.connect(
            lambda: self.reduction_thread.start_reduction(
                self, self.diff_config,
                self.plot_list_dict, self.sam_list,self.other_list, self.Reduction
                )
        )

        self.save_config.clicked.connect(lambda: save_diff_config(self, self.diff_config, self.bl16_configure))

        self.Load_Config.clicked.connect(lambda:(load_diff_config(self),print(self.diff_config)))

        all_item = QtWidgets.QListWidgetItem("ALL")
        all_item.setFlags(all_item.flags() | Qt.ItemIsUserCheckable)
        all_item.setCheckState(Qt.Unchecked)
        self.sam_list.insertItem(0, all_item)

        all_item_v = QtWidgets.QListWidgetItem("ALL")
        all_item_v.setFlags(all_item_v.flags() | Qt.ItemIsUserCheckable)
        all_item_v.setCheckState(Qt.Unchecked)
        self.other_list.insertItem(0, all_item_v)

        self.change_sam_item = change_item(self.sam_list)
        self.sam_list.itemChanged.connect(self.change_sam_item.handle_item_changed)

        self.change_other_item = change_item(self.other_list)
        self.other_list.itemChanged.connect(self.change_other_item.handle_item_changed)

        self.data_plot = data_plot()
        self.plot_button.clicked.connect(lambda:(
            self.data_plot.plot_data(self.sam_list,self.sam_list_dict,self.canvas,self.ax, 'd (Å)', 'Intensity (a.u.)'),
            self.data_plot.plot_data(self.other_list,self.other_list_dict,self.canvas,self.ax, 'd (Å)', 'Intensity (a.u.)',False)
        )
                                         )

        self.save_button.clicked.connect(lambda:
            save_diff(self, self.diff_config,
                      self.sam_list,self.other_list, self.plot_list_dict)
                                         )

        self.del_button.clicked.connect(lambda: (self.change_sam_item.delete_item(self.sam_list_dict),
                                                 self.change_other_item.delete_item(self.other_list_dict)))
