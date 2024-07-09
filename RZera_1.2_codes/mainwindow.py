from PyQt5.QtWidgets import QMainWindow,QApplication
from ui_design.ui_mainwindow import Ui_MainWindow
from diffraction import diffraction
from pdf import pdf


class MainWindow(QMainWindow, Ui_MainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
        self.setupUi(self)

        self.statusBar().showMessage("technique support: wanghao96@ihep.ac.cn")

        self.diffraction_instance = diffraction(self)
        self.tabWidget.addTab(self.diffraction_instance, "Diffraction")

        self.pdf_instance = pdf(self)
        self.tabWidget.addTab(self.pdf_instance, 'PDF')

    def closeEvent(self, event):
        if self.diffraction_instance.reduction_thread.reduction_thread != None and self.diffraction_instance.reduction_thread.reduction_thread.isRunning():
            self.diffraction_instance.reduction_thread.reduction_thread.stop()
            self.diffraction_instance.reduction_thread.reduction_thread.wait()
        if self.pdf_instance.cal_sq_thread.sqcal_thread != None and self.pdf_instance.cal_sq_thread.sqcal_thread.isRunning():
            self.pdf_instance.cal_sq_thread.sqcal_thread.stop()
            self.pdf_instance.cal_sq_thread.sqcal_thread.wait()
        super().closeEvent(event)


if __name__ == "__main__":
    app = QApplication([])
    window = MainWindow()
    window.show()
    app.exec_()