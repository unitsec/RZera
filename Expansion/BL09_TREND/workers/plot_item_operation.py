from PyQt5.QtCore import Qt
from PyQt5 import QtWidgets
import os
import traceback


class change_item:
    def __init__(self, plot_list, plot_list_dict):
        self.plot_list = plot_list
        self.plot_list_dict = plot_list_dict

    def delete_item(self, plot_list_dict):
        # 逆向遍历列表
        for index in range(self.plot_list.count() - 1, 0, -1):  # 从最后一个条目开始，跳过 "ALL" 条目
            item = self.plot_list.item(index)
            if item.checkState() == Qt.Checked:
                item_text = item.text()  # 获取条目文本
                item_to_remove = self.plot_list.takeItem(index)  # 移除条目并获取条目对象
                if item_text in plot_list_dict:
                    del plot_list_dict[item_text]  # 删除字典中的条目
                del item_to_remove  # 删除条目对象
        all_item = self.plot_list.item(0)
        self.plot_list.blockSignals(True)
        all_item.setCheckState(Qt.Unchecked)
        self.plot_list.blockSignals(False)

    def handle_item_changed(self, item):
        # 当任何条目的状态改变时，调用此方法
        if item.text() == "ALL":
            # 如果是 "ALL" 条目，更新其他所有条目的状态
            new_state = item.checkState()
            self.plot_list.blockSignals(True)
            for index in range(1, self.plot_list.count()):
                other_item = self.plot_list.item(index)
                other_item.setCheckState(new_state)
                print(f"Item: {other_item.text()}, State: {other_item.checkState()}")  # 调试打印
            self.plot_list.blockSignals(False)
        else:
            # 如果是其他条目，检查是否需要更新 "ALL" 条目的状态
            self.update_all_checkbox_state()

    def update_all_checkbox_state(self):
        # 检查除了 "ALL" 之外的所有条目是否都被勾选
        all_checked = True
        for index in range(1, self.plot_list.count()):
            if self.plot_list.item(index).checkState() != Qt.Checked:
                all_checked = False
                break
        all_item = self.plot_list.item(0)
        self.plot_list.blockSignals(True)
        all_item.setCheckState(Qt.Checked if all_checked else Qt.Unchecked)
        self.plot_list.blockSignals(False)

    # def setup_plot_list(self, plot_list, plot_list_dict):
    #     for name in plot_list_dict:
    #         # 使用 findItems 查找是否已存在同名条目，第二个参数设置为精确匹配
    #         existing_items = plot_list.findItems(name, Qt.MatchExactly)
    #         if existing_items:
    #             continue  # 如果已经存在，跳过添加
    #         else:
    #             item = QtWidgets.QListWidgetItem(name)
    #             item.setFlags(item.flags() | Qt.ItemIsUserCheckable)  # 设置为可勾选
    #             item.setCheckState(Qt.Unchecked)  # 默认设置为未勾选状态
    #             plot_list.addItem(item)  # 添加到 QListWidget

    def setup_plot_list(self, plot_list, plot_list_dict, filter=None):
        # 记录除了第一项以外的现有项目的文本和勾选状态
        existing_items_status = {}
        for index in range(1, plot_list.count()):  # 从第二项开始
            item = plot_list.item(index)
            existing_items_status[item.text()] = item.checkState()

        # 保存第一项 "ALL" 的引用，并从列表中移除其他所有项
        all_item = plot_list.takeItem(0)
        plot_list.clear()

        # 将 "ALL" 项添加回列表的第一项
        plot_list.insertItem(0, all_item)

        if plot_list.objectName() == 'sam_list' or plot_list.objectName() == 'pdf_sam_list':
            sorted_names = list(plot_list_dict.keys())
        else:
            # sorted(plot_list_dict.keys()) 创建一个包含 plot_list_dict 所有键（项目名称）的列表，并且按字母顺序排序
            sorted_names = sorted(plot_list_dict.keys())

        # 遍历这个排序后的列表，按顺序添加项目到 QListWidget
        for name in sorted_names:
            item = QtWidgets.QListWidgetItem(name)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)

            # 根据之前记录的状态设置勾选状态
            if name in existing_items_status:
                item.setCheckState(existing_items_status[name])
            else:
                item.setCheckState(Qt.Unchecked)

            plot_list.addItem(item)

        if filter is not None:
            self.filter_items(filter)

        self.update_all_checkbox_state()


    def find_d_files(self, directory):
        d_files = []
        for root, dirs, files in os.walk(directory):
            for file in files:
                # 分离文件名和后缀名
                filename, file_extension = os.path.splitext(file)
                # 检查文件名是否以 '_d' 结尾
                if filename.endswith('_d'):
                    # 将文件的完整路径添加到列表中
                    d_files.append(os.path.join(root, file))
        return d_files

    def find_sq_files(self, directory):
        sq_files = []
        for root, dirs, files in os.walk(directory):
            for file in files:
                # 分离文件名和后缀名
                filename, file_extension = os.path.splitext(file)
                # 检查文件名是否以 '_d' 结尾
                if filename.endswith('_sq'):
                    # 将文件的完整路径添加到列表中
                    sq_files.append(os.path.join(root, file))
        return sq_files

    def filter_items(self, data):
        try:
            # 记录除了第一项以外的现有项目的文本和勾选状态
            existing_items_status = {}
            for index in range(1, self.plot_list.count()):  # 从第二项开始
                item = self.plot_list.item(index)
                existing_items_status[item.text()] = item.checkState()

            if not data:
                # 保存第一项 "ALL" 的引用，并从列表中移除其他所有项
                all_item = self.plot_list.takeItem(0)
                self.plot_list.clear()

                # 将 "ALL" 项添加回列表的第一项
                self.plot_list.insertItem(0, all_item)

                sorted_names = sorted(self.plot_list_dict.keys())

                # 遍历这个排序后的列表，按顺序添加项目到 QListWidget
                for name in sorted_names:
                    item = QtWidgets.QListWidgetItem(name)
                    item.setFlags(item.flags() | Qt.ItemIsUserCheckable)

                    # 根据之前记录的状态设置勾选状态
                    if name in existing_items_status:
                        item.setCheckState(existing_items_status[name])
                    else:
                        item.setCheckState(Qt.Unchecked)

                    self.plot_list.addItem(item)

                self.update_all_checkbox_state()
                return

            filter_list = []
            for key, value in self.plot_list_dict.items():  # 从第二项开始
                item = key.split('_')
                # 检查 data 中的所有元素是否都在 item 中
                if all(elem in item for elem in data):
                    filter_list.append(key)

            sorted_filter_list = sorted(filter_list)

            # 保存第一项 "ALL" 的引用，并从列表中移除其他所有项
            all_item = self.plot_list.takeItem(0)
            self.plot_list.clear()

            # 将 "ALL" 项添加回列表的第一项
            self.plot_list.insertItem(0, all_item)

            # 遍历这个排序后的列表，按顺序添加项目到 QListWidget
            for name in sorted_filter_list:
                item = QtWidgets.QListWidgetItem(name)
                item.setFlags(item.flags() | Qt.ItemIsUserCheckable)

                # 根据之前记录的状态设置勾选状态
                if name in existing_items_status:
                    item.setCheckState(existing_items_status[name])
                else:
                    item.setCheckState(Qt.Unchecked)

                self.plot_list.addItem(item)

            self.update_all_checkbox_state()
        except Exception as e:
            print(f"An error occurred: {e}")
            traceback.print_exc()  # 打印异常的堆栈跟踪