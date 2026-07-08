from PyQt5.uic import loadUi
from PyQt5 import QtWidgets,QtGui
from utils.browse import browse
import traceback,re,copy
from rongzai.utils import get_all_from_detector
# from rongzai.dataSvc import load_histogram_data
from PyQt5.QtWidgets import QApplication, QTableWidget, QTableWidgetItem, QCheckBox, QWidget, QVBoxLayout, QHBoxLayout, QHeaderView
from PyQt5.QtCore import Qt

class load_data(QtWidgets.QWidget):
    def __init__(self, parent):
        super(load_data, self).__init__(parent)
        loadUi("utils/ui/load_data.ui", self)
        self.setStyleSheet(f"QFrame#load_data {{ background-color: lightblue; border: 1px solid black; }}")
        self.parent = parent

        self.run_fn = []
        self.browse_run = browse()
        self.run_button.clicked.connect(lambda: (self.browse_run.select_nxsfiles(self.run_text, self.run_fn), print(self.run_fn)))

        self.detector_button.clicked.connect(
            lambda: self.browse_run.select_detectors(self.detector_text, self.parent.config['base']['group_info'], self.parent.config['base']['bank_info']))

        self.instru_button.clicked.connect(lambda: self.browse_run.select_folder(self.instru_text))

        doubleValidator = QtGui.QDoubleValidator()
        self.t0_text.setValidator(doubleValidator) # 将 doubleValidator 设置到 QLineEdit 控件上 (只能输入浮点数)
        self.t0_text.setText('0.0')

        self.merge_load.clicked.connect(lambda: self.load('merge'))

        self.batch_load.clicked.connect(lambda: self.load('batch'))

        self.checkboxes = [] # 存储复选框引用
        self.delete_button.clicked.connect(lambda:self.delete_selected_rows())

    def load(self,mode):
        try:
            if mode == 'merge':
                runno = self.extract_runs_from_lineedit(self.run_text,mode=mode)
                detectors_list = self.extract_detectors_from_lineedit(self.detector_text)
                for detector in detectors_list:
                    judge = self.is_data_exist(self.parent.data_list,runno,detector)
                    print(judge)
                    if judge is True:
                        continue
                    else:
                        data_dict = {}
                        data_dict['name'] = runno
                        data_dict['detector'] = detector
                        data_dict['modules'] = {}
                        _, modules = get_all_from_detector(detector, self.parent.config['base']['group_info'],
                                                           self.parent.config['base']['bank_info'])
                        for module in modules:
                            judge_, index = self.is_runno_exist(self.parent.data_list,runno)
                            print('runno exist:', judge_)
                            if judge_ is True:
                                judge__ = self.is_module_exist(self.parent.data_list[index], module)
                                if judge__ is True:
                                    data_dict['modules'][module] = self.parent.data_list[index]['modules'][module]
                                else:
                                    pidInfo_fn = self.instru_text.text() + "/" + module + ".txt"
                                    neutron_data = load_neutron_data(self.run_fn, pidInfo_fn, module,
                                                                     self.parent.config['base']["first_flight_distance"],
                                                                     float(self.t0_text.text()))
                                    data_dict['modules'][module] = neutron_data
                            else:
                                pidInfo_fn = self.instru_text.text() + "/" + module + ".txt"
                                neutron_data = load_neutron_data(self.run_fn, pidInfo_fn, module,
                                                                 self.parent.config['base']["first_flight_distance"],
                                                                 float(self.t0_text.text()))
                                data_dict['modules'][module] = neutron_data
                        self.parent.data_list.append(data_dict)
                        self.append_data([data_dict])
            elif mode == 'batch':
                runno_list = self.extract_runs_from_lineedit(self.run_text, mode=mode)
                detectors_list = self.extract_detectors_from_lineedit(self.detector_text)
                for runno in runno_list:
                    extracted_runfn = self.extract_runfn_from_runno(self.run_fn,runno)
                    for detector in detectors_list:
                        judge = self.is_data_exist(self.parent.data_list, runno, detector)
                        if judge is True:
                            continue
                        else:
                            data_dict = {}
                            data_dict['name'] = runno
                            data_dict['detector'] = detector
                            data_dict['modules'] = {}
                            _, modules = get_all_from_detector(detector, self.parent.config['base']['group_info'],
                                                               self.parent.config['base']['bank_info'])
                            for module in modules:
                                judge_, index = self.is_runno_exist(self.parent.data_list, runno)
                                print('runno exist:',judge_, index)
                                if judge_ is True:
                                    judge__ = self.is_module_exist(self.parent.data_list[index], module)
                                    print('module exist:', judge__)
                                    if judge__ is True:
                                        data_dict['modules'][module] = self.parent.data_list[index]['modules'][module].copy()
                                    else:
                                        pidInfo_fn = self.instru_text.text() + "/" + module + ".txt"
                                        neutron_data = load_neutron_data(extracted_runfn, pidInfo_fn, module,
                                                                         self.parent.config['base'][
                                                                             "first_flight_distance"],
                                                                         float(self.t0_text.text()))
                                        data_dict['modules'][module] = neutron_data
                                else:
                                    pidInfo_fn = self.instru_text.text() + "/" + module + ".txt"
                                    neutron_data = load_neutron_data(extracted_runfn, pidInfo_fn, module,
                                                                     self.parent.config['base']["first_flight_distance"],
                                                                     float(self.t0_text.text()))
                                    data_dict['modules'][module] = neutron_data
                            self.parent.data_list.append(data_dict)
                            self.append_data([data_dict])
        except Exception as e:
            print(f'Reason: {e}')
            traceback.print_exc()  # 打印异常的堆栈跟踪

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

    def extract_runfn_from_runno(self, run_fn, runno):
        # 使用列表推导式从 run_fn 中提取包含 runno 的元素
        filtered_list = [fn for fn in run_fn if runno in fn]
        return filtered_list

    def extract_detectors_from_lineedit(self,lineEdit):
        detector_list = lineEdit.text().split('; ')
        return detector_list

    def is_data_exist(self,data_list,runno,detector):
        for data in data_list:
            if runno == data["name"] and detector == data["detector"]:
                return True
        return False

    def is_runno_exist(self,data_list,runno):
        for i,data in enumerate(data_list):
            if runno == data["name"]:
                return True, i
        return False, None

    def is_module_exist(self,data,module):
        if module in data['modules'].keys():
            return True
        return False

    def insert_data(self, row, data):
        self.tableWidget.setItem(row, 0, QTableWidgetItem(data["name"])) # 第一列 - RunNo
        self.tableWidget.setItem(row, 1, QTableWidgetItem(data["detector"])) # 第二列 - Detector

        # 第三列 - 复选框
        chk_box_item = QWidget()
        layout = QHBoxLayout()
        layout.setAlignment(Qt.AlignCenter)
        checkbox = QCheckBox()
        layout.addWidget(checkbox)
        chk_box_item.setLayout(layout)
        self.tableWidget.setCellWidget(row, 2, chk_box_item)

        self.checkboxes.append((row, checkbox)) # 保存复选框的引用

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
            import traceback
            traceback.print_exc()  # 打印异常的堆栈跟踪

    def get_config(self):
        return {
            "detector_text": self.detector_text.text(),
            "run_text": self.run_text.text(),
            "instru_text": self.instru_text.text(),
            "t0_text": self.t0_text.text(),
            # "load_info": self.save_table(),
            "run_fn": self.run_fn,
            # "check_info": self.checkboxes
        }

    def set_config(self,config):
        """根据配置更新模块状态"""
        self.detector_text.setText(config.get("detector_text", ""))
        self.run_text.setText(config.get("run_text", ""))
        self.instru_text.setText(config.get("instru_text", ""))
        self.t0_text.setText(config.get("t0_text", ""))
        self.run_fn = config.get("run_fn",[])
