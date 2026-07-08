from utils.browse import browse
from utils.helper import upgrade_positions_to_8cols, upgrade_runno
import traceback,os,json
from PyQt5.QtWidgets import QTableWidgetItem, QCheckBox, QWidget, QHBoxLayout,QHeaderView,QMessageBox
from PyQt5.QtCore import Qt
from rongzai.dataSvc import read_dataset
from utils.ui.BaseUI import CollapsibleWidget

class load_focused_data(CollapsibleWidget):
    def __init__(self, name, parent):
        super(load_focused_data, self).__init__(name, "utils/ui/load_focused_data.ui", parent)
        self.parent = parent

        self.nc_fn = []
        self.loaded_ncPath = []
        self.browse_run = browse()
        self.load_button.clicked.connect(lambda: (self.browse_run.select_ncfiles(self.nc_fn),self.load()))

        self.checkboxes = [] # 存储复选框引用
        self.delete_button.clicked.connect(lambda:self.delete_selected_rows())
        self.delete_all_button.clicked.connect(lambda: self.delete_all_rows())

    def load(self):
        try:
            for fn in self.nc_fn:
                name,_ = os.path.splitext(os.path.basename(fn))
                judge = self.is_data_exist(self.parent.data_list, name)
                if judge is True:
                    continue
                else:
                    data_dict = {'name': name}
                    dataset = read_dataset(fn)
                    dataset = upgrade_positions_to_8cols(dataset) #如果是老版本数据，positions只有3列，扩展成8列以和新版本rongzai兼容
                    dataset = upgrade_runno(dataset,fn) # 如果没有runno属性，则从文件名中提取runno并赋值
                    data_dict['runno'] = dataset.runno
                    data_dict['detector'] = dataset.name
                    data_dict['detector_focused'] = dataset

                    if "record" in dataset.attrs:
                        record_info = json.loads(dataset.attrs["record"])
                        data_dict["record"] = record_info
                    else:
                        data_dict["record"] = {}

                    if "carpenterCorrection" in data_dict["record"].keys():
                        data_dict["correction_info"] = data_dict["record"]["carpenterCorrection"]
                    elif "correction_info" in dataset.attrs:
                        correction_info = json.loads(dataset.attrs["correction_info"])
                        data_dict["correction_info"] = correction_info

                    if "time_slice" in dataset.attrs:
                        data_dict["time_slice"] = dataset.attrs["time_slice"]
                    if "start_time" in dataset.attrs:
                        data_dict["start_time"] = dataset.attrs["start_time"]
                    if "end_time" in dataset.attrs:
                        data_dict["end_time"] = dataset.attrs["end_time"]
                    # if "correction_info" in dataset.attrs:
                    #     correction_info = json.loads(dataset.attrs["correction_info"])
                    #     data_dict["correction_info"] = correction_info
                    self.parent.data_list.append(data_dict)
                    self.append_data([data_dict])
                    self.loaded_ncPath.append(fn)

        except Exception as e:
            print(f'Reason: {e}')
            traceback.print_exc()  # 打印异常的堆栈跟踪

    def is_data_exist(self,data_list,name):
        for data in data_list:
            if name == data["name"]:
                return True
        return False

    def adjust_colWidth(self, col):
        # 动态调整列宽
        self.tableWidget.horizontalHeader().setSectionResizeMode(
            col, QHeaderView.ResizeToContents  # 设置目标列调整模式:ml-citation{ref="5" data="citationList"}
        )
        self.tableWidget.resizeColumnToContents(col)  # 立即触发调整:ml-citation{ref="1" data="citationList"}

    def insert_data(self, row, data):
        self.tableWidget.setItem(row, 0, QTableWidgetItem(data["name"])) # 第一列 - RunNo
        self.adjust_colWidth(0)
        self.tableWidget.setItem(row, 1, QTableWidgetItem(data["detector"])) # 第二列 - Detector
        self.adjust_colWidth(1)

        # 第三列 - 复选框
        chk_box_item = QWidget()
        layout = QHBoxLayout()
        layout.setAlignment(Qt.AlignCenter)
        checkbox = QCheckBox()
        layout.addWidget(checkbox)
        chk_box_item.setLayout(layout)
        self.tableWidget.setCellWidget(row, 2, chk_box_item)
        self.checkboxes.append((row, checkbox))  # 保存复选框的引用
        self.adjust_colWidth(2)

    def append_data(self, new_data_list):
        current_row_count = self.tableWidget.rowCount()
        new_row_count = current_row_count + len(new_data_list)
        self.tableWidget.setRowCount(new_row_count)

        for data in new_data_list:
            self.insert_data(current_row_count, data)
            current_row_count += 1

    def remove_files_by_names(self, filenames_to_remove):
        # 从元组集合中提取第一个元素作为文件名的集合
        filenames_set = {filename for filename, _ in filenames_to_remove}

        # 将不被移除的路径存放到这个新列表中
        updated_paths = []

        for path in self.loaded_ncPath:
            # 获取文件的基本名（带有扩展名）
            base_name = os.path.basename(path)

            # 分割出文件名和扩展名
            name, _ = os.path.splitext(base_name)

            # 检查文件名是否在需要移除的集合中
            if name not in filenames_set:
                updated_paths.append(path)

        self.loaded_ncPath = updated_paths


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

            self.remove_files_by_names(to_delete_set) #删除加载文件记录中对应项

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

    def delete_all_rows(self):
        try:
            rows_to_remove = []
            to_delete_set = set()  # 使用集合以避免重复记录

            # 第一次通过checkboxes记录要删除的数据的标志
            for row, checkbox in self.checkboxes:
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

            self.loaded_ncPath = []
        except Exception as e:
            print(f'Reason: {e}')
            import traceback
            traceback.print_exc()  # 打印异常的堆栈跟踪

    def check_file_paths(self):
        # 复制一份原始列表以便在迭代过程中移除不存在的文件
        valid_files = self.nc_fn[:]
        missed_files = []

        for file_path in self.nc_fn:
            if not os.path.exists(file_path):
                # 如果文件不存在，则显示弹窗提示
                missed_files.append(file_path)
                # 从有效文件列表中移除不存在的文件
                valid_files.remove(file_path)

        if missed_files:
            missing_files_str = "\n".join(missed_files)
            QMessageBox.warning(self, "Files don't exist", f"Some nc files don't exist：\n{missing_files_str}")

        self.nc_fn = valid_files

    def get_config(self):
        return {
            "loaded_ncfn": self.loaded_ncPath,
            "is_use": self.toggle_button.isChecked()
        }

    def set_config(self,config):
        """根据配置更新模块状态"""
        if self.tableWidget.rowCount() != 0:
            # 显示一个确认对话框
            reply = QMessageBox.question(self, "Confirm", "Table is not empty. Do you want to delete all rows?",
                                         QMessageBox.Yes | QMessageBox.No, QMessageBox.No)

            # 如果用户选择了 "Yes"，则执行删除操作
            if reply == QMessageBox.Yes:
                self.delete_all_rows()
        self.nc_fn = config.get("loaded_ncfn", [])
        self.check_file_paths()
        self.load()
        self.toggle_button.setChecked(config.get("is_use", False))