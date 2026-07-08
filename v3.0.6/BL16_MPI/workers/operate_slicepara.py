from PyQt5.QtWidgets import QHBoxLayout,QVBoxLayout, QLineEdit
from PyQt5.QtGui import QDoubleValidator, QIntValidator
import re
import json

class operate_slicepara():
    def __init__(self, parent):
        self.parent = parent
        self.rows = []  # 用于存储行控件的引用
        # 确保 scrollAreaWidgetContents 有一个 QVBoxLayout
        if not self.parent.scrollAreaWidgetContents.layout():
            self.parent.scrollAreaWidgetContents.setLayout(QVBoxLayout())

        # 添加拉伸项，以确保控件靠近顶部
        self.parent.scrollAreaWidgetContents.layout().addStretch()

        self.add_row() # 初始化时添加一行

    def add_row(self):
        # 创建一个新的行布局
        row_layout = QHBoxLayout()

        # 起始值输入框
        start_value = QLineEdit()
        start_value.setPlaceholderText("Start Time")
        start_value.setValidator(QDoubleValidator())  # 只允许输入浮点数

        # 结束值输入框
        end_value = QLineEdit()
        end_value.setPlaceholderText("End Time")
        start_value.setValidator(QDoubleValidator())  # 只允许输入浮点数

        # 切割数量输入框
        num_splits = QLineEdit()
        num_splits.setPlaceholderText("Slice Number")
        num_splits.setValidator(QIntValidator())  # 只允许输入整数

        # 为每个控件设置唯一的名字
        row_index = len(self.rows)
        start_value.setObjectName(f"slice_start_{row_index}")
        end_value.setObjectName(f"slice_end_{row_index}")
        num_splits.setObjectName(f"slice_number_{row_index}")

        # 将输入框添加到行布局中
        row_layout.addWidget(start_value)
        row_layout.addWidget(end_value)
        row_layout.addWidget(num_splits)

        # 获取布局，并在拉伸项之前插入新行
        layout = self.parent.scrollAreaWidgetContents.layout()
        layout.insertLayout(layout.count() - 1, row_layout)  # 插入到倒数第二个位置

        # 将控件引用存储在列表中
        self.rows.append({
            'start_value': start_value,
            'end_value': end_value,
            'num_splits': num_splits,
            'layout': row_layout
        })

    def remove_row(self):
        # 移除参数设置区域中的最后一行
        layout = self.parent.scrollAreaWidgetContents.layout()
        if layout.count() > 1:  # 至少保留拉伸项
            last_row = layout.takeAt(layout.count() - 2)  # 移除倒数第二个项
            if last_row:
                # 删除行布局中的所有子控件
                while last_row.count():
                    item = last_row.takeAt(0)
                    widget = item.widget()
                    if widget:
                        widget.deleteLater()
                last_row.deleteLater()
            # 从 self.rows 列表中删除最后一个元素
            if self.rows:
                self.rows.pop()

def read_exptime(parent):
    sam_path = parent.sample_run_text.text()
    try:
        runno = re.findall(r'RUN\d+', sam_path)[-1]
        expinfo_path = sam_path + '/' + runno
        with open(expinfo_path, 'r', encoding='utf-8') as json_file:
            expinfo = json.load(json_file)
        start_sec = expinfo['startTimeSecond']
        end_sec = expinfo['endTimeSecond']
        exp_sec = int(end_sec) - int(start_sec)
        exp_minute = exp_sec / 60
        exp_minute_formatted = "{:.2f}".format(exp_minute)
        parent.exp_time.setText(exp_minute_formatted)
    except:
        parent.exp_time.setText('None')

def read_start_pulseID(parent):
    sam_path = parent.sample_run_text.text()
    try:
        runno = re.findall(r'RUN\d+', sam_path)[-1]
        expinfo_path = sam_path + '/' + runno
        with open(expinfo_path, 'r', encoding='utf-8') as json_file:
            expinfo = json.load(json_file)
        start_pilseID = expinfo['startPulseId']
        return start_pilseID
    except:
        return ''