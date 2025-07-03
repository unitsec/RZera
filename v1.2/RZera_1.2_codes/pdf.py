from PyQt5 import QtWidgets
from PyQt5 import QtGui
from PyQt5.QtCore import Qt
from ui_design.ui_pdf import Ui_Form
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
from workers.browse_file import browse_file
from workers.combobox_operation import browse_mode_check
from workers.checkbox_operation import checkbox_operation
from utils_ui.NonZeroIntValidator import NonZeroIntValidator
from workers.data_save import save_sq,save_pdf
from workers.plot_item_operation import change_item
from workers.data_plot import data_plot
from workers.ui_mapping import save_pdf_config, load_pdf_config
import workers.pdf_thread
import traceback


class pdf(QtWidgets.QWidget, Ui_Form):
    def __init__(self, parent=None):
        super(pdf, self).__init__(parent)
        self.setupUi(self)
        self.mainwindow = self.parent()
        self.plot_list_dict = {'sam_list': {}, 'other_list': {}}
        self.pdf_config = {'sam_fn': [], 'v_fn': [], 'hold_fn': [], 'bkg_fn': []}
        self.browse_run = browse_file()

        self.figure = Figure()
        self.canvas = FigureCanvas(self.figure)
        self.ax = self.figure.add_subplot(111)
        self.graphicView.setLayout(QtWidgets.QVBoxLayout())
        self.graphicView.layout().addWidget(self.canvas)
        self.toolbar = NavigationToolbar(self.canvas, self)
        self.graphicView.layout().addWidget(self.toolbar)
        self.figure.tight_layout()
        self.figure.subplots_adjust(bottom=0.17)

        self.pdf_samrun_button.clicked.connect(
            lambda: self.browse_run.select_nxsfiles(self.pdf_samrun_text, self.pdf_config['sam_fn']))
        self.van_run_mode.currentTextChanged.connect(
            lambda: (self.pdf_vanrun_text.setText(''), self.pdf_config.update({'v_fn': []})))
        self.pdf_vanrun_button.clicked.connect(
            lambda: browse_mode_check(self.van_run_mode, self.pdf_config['v_fn'], self.pdf_vanrun_text,
                                                     self))

        doubleValidator = QtGui.QDoubleValidator()
        self.pdf_mass.setValidator(doubleValidator)
        self.pdf_radius.setValidator(doubleValidator)
        self.pdf_height.setValidator(doubleValidator)

        self.browse_run = browse_file()
        self.pdf_instrupath_button.clicked.connect(lambda: self.browse_run.select_folder(self.pdf_instrupath_text))

        self.hold_run_mode.currentTextChanged.connect(
            lambda: (self.pdf_holdrun_text.setText(''), self.pdf_config.update({'hold_fn': []})))
        self.pdf_holdrun_button.clicked.connect(
            lambda: browse_mode_check(self.hold_run_mode, self.pdf_config['hold_fn'], self.pdf_holdrun_text,
                                                     self))

        self.checkbox_operation = checkbox_operation()
        self.pdf_offset_button.setEnabled(False)
        self.pdf_offset_text.setEnabled(False)
        self.pdf_offset_check.stateChanged.connect(
            lambda: self.checkbox_operation.check_set(self.pdf_offset_check, self.pdf_offset_button,
                                                      self.pdf_offset_text,
                                                      use_combobox=False))
        self.pdf_offset_button.clicked.connect(lambda: self.browse_run.select_folder(self.pdf_offset_text))

        doubleValidator = QtGui.QDoubleValidator()
        self.pdf_sam_hold.setValidator(doubleValidator)
        self.pdf_van_hold.setValidator(doubleValidator)
        self.pdf_sam_bkg.setValidator(doubleValidator)
        self.pdf_van_bkg.setValidator(doubleValidator)
        self.pdf_sam_hold.setText('0.1')
        self.pdf_van_hold.setText('0.5')
        self.pdf_sam_bkg.setText('0.0')
        self.pdf_van_bkg.setText('0.0')

        self.checkbox_operation = checkbox_operation()
        self.pdf_bkgrun_button.setEnabled(False)
        self.pdf_bkgrun_text.setEnabled(False)
        self.pdf_bkg_check.stateChanged.connect(
            lambda: self.checkbox_operation.check_set(self.pdf_bkg_check, self.pdf_bkgrun_button,
                                                      self.pdf_bkgrun_text,
                                                      use_combobox=False))
        self.bkg_run_mode.currentTextChanged.connect(
            lambda: (self.pdf_bkgrun_text.setText(''), self.pdf_config.update({'bkg_fn': []})))
        self.pdf_bkgrun_button.clicked.connect(
            lambda: browse_mode_check(self.bkg_run_mode, self.pdf_config['bkg_fn'], self.pdf_bkgrun_text,
                                      self))

        doubleValidator = QtGui.QDoubleValidator()
        self.pdf_wavestart.setValidator(doubleValidator)
        self.pdf_waveend.setValidator(doubleValidator)

        doubleValidator = QtGui.QDoubleValidator()
        self.pdf_T0_offset.setValidator(doubleValidator)
        self.pdf_T0_offset.setText('0.0')

        self.mainwindow = self.parent()
        self.cal_sq_thread = workers.pdf_thread.start_pdf_thread()  # 实例化start_reduction_thread
        self.pdf_cal_sq.clicked.connect(
            lambda: self.cal_sq_thread.start_sqcal(
                self,  self.pdf_config,
                self.plot_list_dict, self.pdf_sam_list, self.pdf_other_list, self.pdf_cal_sq
                )
        )

        self.pdf_save_config.clicked.connect(
            lambda:save_pdf_config(
                self,self.pdf_config))

        self.pdf_load_config.clicked.connect(lambda:load_pdf_config(self))

        all_item_plot = QtWidgets.QListWidgetItem("ALL")
        all_item_plot.setFlags(all_item_plot.flags() | Qt.ItemIsUserCheckable)
        all_item_plot.setCheckState(Qt.Unchecked)
        self.pdf_sam_list.insertItem(0, all_item_plot)

        all_item_other = QtWidgets.QListWidgetItem("ALL")
        all_item_other.setFlags(all_item_other.flags() | Qt.ItemIsUserCheckable)
        all_item_other.setCheckState(Qt.Unchecked)
        self.pdf_other_list.insertItem(0, all_item_other)

        self.change_sam_item = change_item(self.pdf_sam_list)
        self.pdf_sam_list.itemChanged.connect(self.change_sam_item.handle_item_changed)

        self.change_other_item = change_item(self.pdf_other_list)
        self.pdf_other_list.itemChanged.connect(self.change_other_item.handle_item_changed)

        self.data_plot = data_plot()
        self.pdf_plot_sq.clicked.connect(lambda: self.data_plot.plot_sq_data(
            self.pdf_sam_list,self.pdf_other_list,self.plot_list_dict,self.canvas,self.ax,
            r'Q (Å$^{-1}$)','d (Å)','Intensity (a.u.)'))

        doubleValidator = QtGui.QDoubleValidator()
        self.pdf_qrebin_start.setValidator(doubleValidator)
        self.pdf_qrebin_end.setValidator(doubleValidator)

        self.nozerointvalidator = NonZeroIntValidator(1, 2147483647)
        self.pdf_qrebin_number.setValidator(self.nozerointvalidator)

        self.merge_thread = workers.pdf_thread.start_pdf_thread()
        self.pdf_merge.clicked.connect(
            lambda: self.merge_thread.start_merge(
                self, self.pdf_config,
                self.plot_list_dict['sam_list'],self.pdf_sam_list, self.pdf_merge))

        self.pdf_save_sq.clicked.connect(lambda: save_sq(self,self.pdf_sam_list,self.pdf_other_list,self.plot_list_dict))

        self.pdf_del_sq.clicked.connect(lambda: (self.change_sam_item.delete_item(self.plot_list_dict['sam_list']),
                                                 self.change_other_item.delete_item(self.plot_list_dict['other_list'])
                                                 ))

        doubleValidator = QtGui.QDoubleValidator()
        self.pdf_r_start.setValidator(doubleValidator)
        self.pdf_r_end.setValidator(doubleValidator)

        self.nozerointvalidator = NonZeroIntValidator(1, 2147483647)
        self.pdf_r_number.setValidator(self.nozerointvalidator)

        self.data_plot = data_plot()
        self.pdf_cal_button.clicked.connect(
            lambda: self.data_plot.plot_pdf_data(self,
                self.pdf_config,
                self.pdf_sam_list,self.plot_list_dict['sam_list'],self.canvas,self.ax,'r (Å)','Intensity (a.u.)'))

        self.pdf_save_button.clicked.connect(
            lambda: save_pdf(
                self, self.pdf_config,
                self.pdf_sam_list, self.plot_list_dict['sam_list'])
        )
