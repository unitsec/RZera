from PyQt5.uic import loadUi
from PyQt5 import QtWidgets,QtCore
from PyQt5.QtGui import QDoubleValidator
from PyQt5.QtCore import Qt, QEventLoop
from utils.ui.BaseUI import CollapsibleWidget
from utils.browse_dialog import UtilsSelectionDialog
from PyQt5.QtWidgets import QTableWidgetItem, QLineEdit, QCheckBox, QWidget, QHBoxLayout, QComboBox,QHeaderView,QMessageBox
from rongzai.algSvc.neutron import rebin_neutron_data
from rongzai.utils import generate_x
from rongzai.utils import get_all_from_detector
from rongzai.dataSvc import create_dataset
from scipy.interpolate import CubicSpline, PchipInterpolator
import numpy as np
import copy,traceback
from utils.browse import browse

class interpolation(CollapsibleWidget):
    def __init__(self, parent):
        super(interpolation, self).__init__("Interpolation", "utils/ui/interpolation.ui", parent)
        self.parent = parent
        self.browse_run = browse()
        self.checkboxes1 = []  # 存储复选框引用
        self.checkboxes2 = []
        self.pressureValue.setValidator(QDoubleValidator())  # 设置验证器，确保只能输入数字

        self.add_button.clicked.connect(lambda: self.add_data_interpolation([data['name'] for data in self.parent.data_list]))
        self.interplateButton.clicked.connect(self.interplate_data)

        
        self.delete_button1.clicked.connect(lambda: self.delete_selected_rows(self.checkboxes1, self.tableWidget1))
        self.delete_button2.clicked.connect(lambda: self.delete_selected_rows(self.checkboxes2, self.tableWidget2))
        if hasattr(self, "deleteAll_button1"):
            self.deleteAll_button1.clicked.connect(self.delete_all_imported_rows)
        self.tableWidget2.itemChanged.connect(self._on_table2_item_changed)

    def interplate_data(self):
        data_list_backup = copy.deepcopy(self.parent.data_list)
        try:
            
            # 1) 建立 name -> data_item 索引，后续可快速取到 detector_focused
            data_dict = {item['name']: item for item in self.parent.data_list}
            selected_rows = []

            # 2) 从 tableWidget1 读取全部导入行，并收集 name/detector/pressure/dataset
            for row in range(self.tableWidget1.rowCount()):
                name_item = self.tableWidget1.item(row, 0)
                detector_item = self.tableWidget1.item(row, 1)
                pressure_edit = self.tableWidget1.cellWidget(row, 2)

                if name_item is None or detector_item is None or pressure_edit is None:
                    continue

                name = name_item.text().strip()
                detector = detector_item.text().strip()
                pressure_text = pressure_edit.text().strip()

                # 每条输入曲线都必须有压力值，且能转为 float
                if not pressure_text:
                    QMessageBox.warning(self, "Interpolation", f"Pressure is empty for {name}.")
                    return

                try:
                    pressure = float(pressure_text)
                except ValueError:
                    QMessageBox.warning(self, "Interpolation", f"Invalid pressure value for {name}: {pressure_text}")
                    return

                if name not in data_dict:
                    QMessageBox.warning(self, "Interpolation", f"Data not found in data_list: {name}")
                    return
                if "detector_focused" not in data_dict[name]:
                    QMessageBox.warning(self, "Interpolation", f"detector_focused missing for {name}")
                    return

                selected_rows.append({
                    "name": name,
                    "detector": detector,
                    "pressure": pressure,
                    "dataset": data_dict[name]["detector_focused"]
                })

            # 至少需要 2 条导入曲线才能做压力轴插值
            if len(selected_rows) < 2:
                QMessageBox.warning(self, "Interpolation", "Please import at least two rows for interpolation.")
                return

            # 3) 约束：参与插值的数据必须来自同一探测器
            detector_set = {row["detector"] for row in selected_rows}
            if len(detector_set) != 1:
                QMessageBox.warning(self, "Interpolation", "Selected rows must belong to the same detector.")
                return
            detector = selected_rows[0]["detector"]

            # 4) 读取目标压力（self.pressureValue），该值决定要插值到哪个压力点
            target_pressure_text = self.pressureValue.text().strip()
            if not target_pressure_text:
                QMessageBox.warning(self, "Interpolation", "Please input target pressure in pressureValue.")
                return
            try:
                target_pressure = float(target_pressure_text)
            except ValueError:
                QMessageBox.warning(self, "Interpolation", f"Invalid target pressure: {target_pressure_text}")
                return

            # 按压力升序排序，保证插值器输入有序
            selected_rows.sort(key=lambda x: x["pressure"])
            pressures = np.array([row["pressure"] for row in selected_rows], dtype=float)

            p_min = float(np.min(pressures))
            p_max = float(np.max(pressures))
            span = p_max - p_min
            left_gap = float(pressures[1] - pressures[0])
            right_gap = float(pressures[-1] - pressures[-2])
            max_extrapolation = min(span * 0.05, left_gap, right_gap)

            # 允许边界外小范围外推，但需要用户确认；超出容许范围则直接拒绝
            if target_pressure < p_min or target_pressure > p_max:
                if target_pressure < p_min:
                    extrapolation_distance = p_min - target_pressure
                    boundary_text = f"below the lower bound by {extrapolation_distance:g} MPa"
                else:
                    extrapolation_distance = target_pressure - p_max
                    boundary_text = f"above the upper bound by {extrapolation_distance:g} MPa"

                if extrapolation_distance > max_extrapolation:
                    QMessageBox.warning(
                        self,
                        "Interpolation",
                        f"Target pressure {target_pressure:g} MPa is outside the allowed extrapolation range. "
                        f"Allowed extrapolation is at most {max_extrapolation:g} MPa beyond the boundary, "
                        f"but the requested value is {boundary_text}."
                    )
                    return

                reply = QMessageBox.question(
                    self,
                    "Interpolation",
                    f"Target pressure {target_pressure:g} MPa is outside [{p_min:g}, {p_max:g}] MPa, but within the allowed extrapolation range ({max_extrapolation:g} MPa).\n"
                    f"This will extrapolate the interpolated result. Continue?",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No,
                )
                if reply != QMessageBox.Yes:
                    return

            # 5) 组装插值输入矩阵：
            #    y_mat.shape  = [n_pressure, n_x]
            #    e2_mat.shape = [n_pressure, n_x]  (对误差使用方差插值更稳健)
            x_ref = np.asarray(selected_rows[0]["dataset"]["xvalue"].values[0], dtype=float)
            y_stack = []
            e2_stack = []
            
            self._run_previous_modules()  # 确保之前的模块都已运行，数据是最新的
            for row in selected_rows:
                ds = row["dataset"]
                x = np.asarray(ds["xvalue"].values[0], dtype=float)
                y = np.asarray(ds["histogram"].values[0], dtype=float)
                e = np.asarray(ds["error"].values[0], dtype=float)

                if x.shape != x_ref.shape or not np.allclose(x, x_ref, rtol=0.0, atol=1e-12):
                    QMessageBox.warning(self, "Interpolation", f"x-axis mismatch found in {row['name']}.")
                    return

                y_stack.append(y)
                e2_stack.append(np.square(e))

            y_mat = np.stack(y_stack, axis=0)
            e2_mat = np.stack(e2_stack, axis=0)

            # 6) 根据下拉框 interplateMode 选择算法（与你测试脚本一致：Cubic / PCHIP）
            mode_text = self.interplateMode.currentText()
            if "PCHIP" in mode_text.upper():
                y_interp_func = PchipInterpolator(pressures, y_mat, axis=0, extrapolate=True)
                e2_interp_func = PchipInterpolator(pressures, e2_mat, axis=0, extrapolate=True)
                mode_name = "pchip"
            else:
                y_interp_func = CubicSpline(pressures, y_mat, axis=0, bc_type="natural", extrapolate=True)
                e2_interp_func = CubicSpline(pressures, e2_mat, axis=0, bc_type="natural", extrapolate=True)
                mode_name = "cubic"
            mode_display = mode_text.strip() or mode_name

            # 7) 在目标压力点执行插值
            y_interp = np.asarray(y_interp_func(target_pressure), dtype=float)
            e2_interp = np.asarray(e2_interp_func(target_pressure), dtype=float)
            e_interp = np.sqrt(np.clip(e2_interp, a_min=0.0, a_max=None))

            self.parent.data_list = data_list_backup # 恢复 data_list 到插值前未归一化状态
            
            # create_dataset 的几何/仪器相关字段复用参考输入数据
            base_dataset = selected_rows[0]["dataset"]
            try:
                pixel = np.asarray(base_dataset["positions"].coords["pixel"].values)
                pos = np.asarray(base_dataset["positions"].values)
                l1 = float(np.asarray(base_dataset["l1"].values).reshape(-1)[0])
                module_name = base_dataset.attrs.get("name", detector)
                x_unit = base_dataset.attrs.get("x_unit", "dspacing")
            except Exception:
                QMessageBox.warning(self, "Interpolation", "Missing positions/l1 information in source dataset.")
                return

            # 8) 将插值结果封装为 rongzai 可继续规约的 dataset
            interpolated_dataset = create_dataset(
                y_interp,
                e_interp,
                x_ref,
                pixel,
                pos,
                self.parent.config['base']['pc_factor'],
                l1,
                module_name,
                unit=x_unit
            )

            # 9) 组织成 data_list 标准条目，并记录插值元信息到 record
            input_names = [row["name"] for row in selected_rows]
            category_tag = self._infer_interpolation_tag(input_names)
            name_prefix = self._compose_unique_name_prefix("interp", category_tag, detector)
            interpolated_name = f"{name_prefix}_{target_pressure:g}MPa_{mode_name}"
            # 复制输入数据的 record（按约定这些 record 应一致），并追加插值信息
            base_record = copy.deepcopy(data_dict[selected_rows[0]["name"]].get("record", {}))
            base_record["interpolation"] = {
                "mode": mode_name,
                "target_pressure_mpa": target_pressure,
                "input": [{"name": row["name"], "pressure_mpa": row["pressure"]} for row in selected_rows]
            }
            data_item = {
                "name": interpolated_name,
                "runno": "",
                "detector": detector,
                "detector_focused": interpolated_dataset,
                "record": base_record
            }

            # 同名则覆盖，避免同一类别在相同目标压力重复插值时产生多份数据
            existing_idx = next((i for i, item in enumerate(self.parent.data_list) if item.get("name") == interpolated_name), None)
            if existing_idx is None:
                self.parent.data_list.append(data_item)
            else:
                self.parent.data_list[existing_idx] = data_item

            # 10) 把结果显示到输出表
            output_table = getattr(self, "tableWidget2", None)

            if output_table is not None:
                target_row = None
                for row in range(output_table.rowCount()):
                    item = output_table.item(row, 0)
                    if item is not None and item.text() == interpolated_name:
                        target_row = row
                        break
                if target_row is None:
                    target_row = output_table.rowCount()
                    output_table.insertRow(target_row)

                name_item = QTableWidgetItem(interpolated_name)
                name_item.setData(Qt.UserRole, interpolated_name)
                output_table.setItem(target_row, 0, name_item)
                output_table.setItem(target_row, 1, QTableWidgetItem(detector))
                output_table.setItem(target_row, 2, QTableWidgetItem(f"{target_pressure:g}"))
                if output_table.columnCount() > 4:
                    output_table.setItem(target_row, 3, QTableWidgetItem(mode_display))
                checkbox_col = output_table.columnCount() - 1

                checkbox_widget = QWidget()
                checkbox_layout = QHBoxLayout()
                checkbox_layout.setContentsMargins(0, 0, 0, 0)
                check_box = QCheckBox()
                checkbox_layout.addWidget(check_box)
                checkbox_layout.setAlignment(Qt.AlignCenter)
                checkbox_widget.setLayout(checkbox_layout)
                output_table.setCellWidget(target_row, checkbox_col, checkbox_widget)

                # 刷新输出表复选框引用（供后续删除/批处理扩展使用）
                self.checkboxes2 = [(r, output_table.cellWidget(r, checkbox_col).layout().itemAt(0).widget())
                                    for r in range(output_table.rowCount())
                                    if output_table.cellWidget(r, checkbox_col) is not None]

            QMessageBox.information(self, "Interpolation", f"Interpolation finished: {interpolated_name}")
        except Exception as e:
            self.parent.data_list = data_list_backup # 恢复 data_list 到插值前未归一化状态
            QMessageBox.warning(self, "Interpolation", f"Interpolation failed: {e}")
            traceback.print_exc()

    def _on_table2_item_changed(self, item):
        """同步 tableWidget2 的 name 编辑到 data_list。"""
        if item is None or item.column() != 0:
            return

        old_name = item.data(Qt.UserRole)
        new_name = item.text().strip()

        # 首次写入表格时初始化旧名缓存，不做改名同步
        if old_name is None:
            item.setData(Qt.UserRole, new_name)
            return

        if new_name == old_name:
            return

        if not new_name:
            QMessageBox.warning(self, "Interpolation", "Name cannot be empty.")
            self.tableWidget2.blockSignals(True)
            item.setText(old_name)
            self.tableWidget2.blockSignals(False)
            return

        if any(data.get("name") == new_name for data in self.parent.data_list):
            QMessageBox.warning(self, "Interpolation", f"Name already exists: {new_name}")
            self.tableWidget2.blockSignals(True)
            item.setText(old_name)
            self.tableWidget2.blockSignals(False)
            return

        target_item = next((data for data in self.parent.data_list if data.get("name") == old_name), None)
        if target_item is None:
            QMessageBox.warning(self, "Interpolation", f"Cannot find data item: {old_name}")
            self.tableWidget2.blockSignals(True)
            item.setText(old_name)
            self.tableWidget2.blockSignals(False)
            return

        target_item["name"] = new_name
        item.setData(Qt.UserRole, new_name)

    def _run_previous_modules(self):
        """运行前置模块"""
        current_name = self.objectName()
        for i in range(self.parent.inner_layout.count()):
            module = self.parent.inner_layout.itemAt(i).widget()
            if module is None:
                continue
            if module.objectName() == current_name:
                break
            if hasattr(module, 'run'):
                if hasattr(module, 'finished'):
                    loop = QEventLoop()
                    is_finished = False

                    def on_finished():
                        nonlocal is_finished
                        is_finished = True
                        loop.quit()

                    module.finished.connect(on_finished)
                    module.run()
                    if not is_finished:
                        loop.exec_()
                else:
                    module.run()

    def _infer_interpolation_tag(self, names):
        """按 '_' 分词后提取所有输入名共享的词，并按顺序拼接。"""
        if not names:
            return ""

        token_lists = []
        for name in names:
            text = str(name).strip()
            if not text:
                continue
            tokens = [t for t in text.split('_') if t]
            if tokens:
                token_lists.append(tokens)

        if not token_lists:
            return ""

        # 用小写集合求交集，避免大小写差异导致共享词丢失。
        common_lower = {t.lower() for t in token_lists[0]}
        for tokens in token_lists[1:]:
            common_lower &= {t.lower() for t in tokens}

        if not common_lower:
            return ""

        # 按第一个输入名中的出现顺序组装共享词，保证命名稳定。
        ordered_common = []
        seen = set()
        for token in token_lists[0]:
            lower_t = token.lower()
            if lower_t in common_lower and lower_t not in seen:
                ordered_common.append(token)
                seen.add(lower_t)

        return "_".join(ordered_common)

    def _compose_unique_name_prefix(self, *parts):
        """将多个片段按 '_' 拆分并去重后拼接，避免名字里出现重复 group 词。"""
        tokens = []
        seen = set()

        for part in parts:
            text = str(part).strip()
            if not text:
                continue
            for token in text.split('_'):
                t = token.strip()
                if not t:
                    continue
                lower_t = t.lower()
                if lower_t in seen:
                    continue
                tokens.append(t)
                seen.add(lower_t)

        return "_".join(tokens)
    
    def plot_data(self):
        if self.toggle_button.isChecked():
            plot_data = []
            for data in self.parent.data_list:
                if "detector_focused" in data and data.get("record", {}).get("interpolation") is not None:
                    plot_data.append({"name": f"{data['name']}",
                                      "data": [copy.deepcopy(data["detector_focused"]["xvalue"].values[0]),
                                               copy.deepcopy(data["detector_focused"]["histogram"].values[0]),
                                               copy.deepcopy(data["detector_focused"]["error"].values[0])],
                                      "x_label": "d (Å)",
                                      "y_label": "Intensity (a.u.)"})
            return plot_data
        else:
            return []

    def add_data_interpolation(self, files, parent=None):
        """处理加载按钮点击"""
        data_dict = {item['name']: item for item in self.parent.data_list}
        detector_dialog = UtilsSelectionDialog(files, window_title="Select Files", parent=parent)
        if detector_dialog.exec_() == QtWidgets.QDialog.Accepted:
            selected_files = detector_dialog.selectedFiles()

            for file in selected_files:

                # 检查文件是否已经存在于 tableWidget 中
                file_exists = False
                for row in range(self.tableWidget1.rowCount()):
                    existing_file_item = self.tableWidget1.item(row, 0)
                    if existing_file_item and existing_file_item.text() == file:
                        file_exists = True
                        break

                # 如果文件不存在，则添加新行
                if not file_exists:
                    row_position = self.tableWidget1.rowCount()
                    self.tableWidget1.insertRow(row_position)
                    # 第1列: 文件名1
                    file_item = QTableWidgetItem(file)
                    self.tableWidget1.setItem(row_position, 0, file_item)

                    self.tableWidget1.setItem(row_position, 1, QTableWidgetItem(data_dict[file]["detector"])) # 第二列 - Detector
                    self.adjust_colWidth(self.tableWidget1, 1)

                    # 第3列: 只能输入数值的文本框
                    value_edit = QLineEdit()
                    value_validator = QDoubleValidator(value_edit)
                    value_validator.setNotation(QDoubleValidator.StandardNotation)
                    value_edit.setValidator(value_validator)
                    self.tableWidget1.setCellWidget(row_position, 2, value_edit)

                    checkbox_widget = QWidget()
                    checkbox_layout = QHBoxLayout()
                    checkbox_layout.setContentsMargins(0, 0, 0, 0)
                    check_box = QCheckBox()
                    checkbox_layout.addWidget(check_box)
                    checkbox_layout.setAlignment(Qt.AlignCenter)  # 居中对齐
                    checkbox_widget.setLayout(checkbox_layout)
                    self.tableWidget1.setCellWidget(row_position, 3, checkbox_widget)
                    self.checkboxes1.append((row_position, check_box))  # 保存复选框的引用
        

    def adjust_colWidth(self, tableWidget, col):
        # 动态调整列宽
        tableWidget.horizontalHeader().setSectionResizeMode(
            col, QHeaderView.ResizeToContents  # 设置目标列调整模式:ml-citation{ref="5" data="citationList"}
        )
        tableWidget.resizeColumnToContents(col)  # 立即触发调整:ml-citation{ref="1" data="citationList"}

    

    def delete_selected_rows(self, checkboxes, tableWidget):
        try:
            rows_to_remove = []
            checkbox_col = tableWidget.columnCount() - 1

            # 第一次通过checkboxes记录要删除的数据的标志
            for row, checkbox in checkboxes:
                if checkbox.isChecked():
                    # 将将要删除的数据标记放入集合中
                    rows_to_remove.append(row)

            # 按降序排序以避免删除行时影响其他待删除行的索引
            rows_to_remove.sort(reverse=True)

            # 如果是插值数据，需要从 data_list 中删除对应的数据项
            if tableWidget == self.tableWidget2:
                self.parent.data_list = [item for item in self.parent.data_list if item["name"] not in 
                                         {tableWidget.item(r, 0).text() for r in rows_to_remove if tableWidget.item(r, 0) is not None}]
            
            # 删除表格行
            for row in rows_to_remove:
                tableWidget.removeRow(row)

            # 更新复选框引用，重建剩余复选框的列表
            new_checkboxes = []
            for row in range(tableWidget.rowCount()):
                checkbox_widget = tableWidget.cellWidget(row, checkbox_col)
                if checkbox_widget is None or checkbox_widget.layout() is None:
                    continue
                checkbox = checkbox_widget.layout().itemAt(0).widget()
                new_checkboxes.append((row, checkbox))
            if tableWidget == self.tableWidget1:
                self.checkboxes1 = new_checkboxes
            elif tableWidget == self.tableWidget2:
                self.checkboxes2 = new_checkboxes
        
        except Exception as e:
            print(f'Reason: {e}')
            import traceback
            traceback.print_exc()  # 打印异常的堆栈跟踪

    def delete_all_imported_rows(self):
        """清空插值输入表（导入栏）的全部数据。"""
        try:
            self.tableWidget1.setRowCount(0)
            self.checkboxes1 = []
        except Exception as e:
            print(f'Reason: {e}')
            traceback.print_exc()

    def get_config(self):
        return {
            "is_use": self.toggle_button.isChecked(),
            "plot": self.plot.isChecked(),
            "target_pressure": self.pressureValue.text().strip(),
            "interpolation_mode": self.interplateMode.currentText(),
            "input_info": self._save_table_data(self.tableWidget1),
        }

    def set_config(self,config):
        """根据配置更新模块状态"""
        self.pressureValue.setText(config.get("target_pressure", ""))

        mode_text = config.get("interpolation_mode", "")
        if mode_text:
            idx = self.interplateMode.findText(mode_text)
            if idx >= 0:
                self.interplateMode.setCurrentIndex(idx)

        # 新键优先，旧键 rebin_info 作为兼容回退
        input_info = config.get("input_info", config.get("rebin_info", []))
        result_info = config.get("result_info", [])

        self._load_table_data(self.tableWidget1, input_info)

        self.plot.setChecked(config.get("plot", False))
        self.toggle_button.setChecked(config.get("is_use", False))

    def _save_table_data(self, tableWidget):
        """保存任意 QTableWidget 内容，支持 item/line_edit/combobox/checkbox。"""
        table_data = []
        for row in range(tableWidget.rowCount()):
            row_data = []
            for col in range(tableWidget.columnCount()):
                widget = tableWidget.cellWidget(row, col)
                item = tableWidget.item(row, col)

                if isinstance(widget, QLineEdit):
                    row_data.append({"type": "line_edit", "value": widget.text()})
                elif isinstance(widget, QComboBox):
                    row_data.append({
                        "type": "combobox",
                        "value": widget.currentText(),
                        "options": [widget.itemText(i) for i in range(widget.count())]
                    })
                elif isinstance(widget, QWidget):
                    checkbox = widget.findChild(QCheckBox)
                    if checkbox is not None:
                        row_data.append({"type": "checkbox", "value": checkbox.isChecked()})
                    else:
                        row_data.append({"type": "item", "value": item.text() if item is not None else ""})
                else:
                    row_data.append({
                        "type": "item",
                        "value": item.text() if item is not None else "",
                        "user_role": item.data(Qt.UserRole) if item is not None else None
                    })
            table_data.append(row_data)
        return table_data

    def _load_table_data(self, tableWidget, table_data, set_name_user_role=False):
        """恢复 QTableWidget 内容，并重建复选框引用。"""
        if not isinstance(table_data, list):
            table_data = []

        block_name_signal = (tableWidget == self.tableWidget2)
        if block_name_signal:
            tableWidget.blockSignals(True)

        try:
            tableWidget.setRowCount(0)
            for row_idx, row_data in enumerate(table_data):
                tableWidget.insertRow(row_idx)
                for col_idx, cell_data in enumerate(row_data):
                    cell_type = cell_data.get("type", "item") if isinstance(cell_data, dict) else "item"
                    value = cell_data.get("value", "") if isinstance(cell_data, dict) else ""

                    if cell_type == "line_edit":
                        value_edit = QLineEdit()
                        value_validator = QDoubleValidator(value_edit)
                        value_validator.setNotation(QDoubleValidator.StandardNotation)
                        value_edit.setValidator(value_validator)
                        value_edit.setText(str(value))
                        tableWidget.setCellWidget(row_idx, col_idx, value_edit)

                    elif cell_type == "combobox":
                        combo = QComboBox()
                        options = cell_data.get("options", []) if isinstance(cell_data, dict) else []
                        if not options:
                            options = [str(value)] if value != "" else []
                        for option in options:
                            combo.addItem(option)
                        target_idx = combo.findText(str(value))
                        if target_idx >= 0:
                            combo.setCurrentIndex(target_idx)
                        tableWidget.setCellWidget(row_idx, col_idx, combo)

                    elif cell_type == "checkbox":
                        checkbox_widget = QWidget()
                        checkbox_layout = QHBoxLayout()
                        checkbox_layout.setContentsMargins(0, 0, 0, 0)
                        check_box = QCheckBox()
                        check_box.setChecked(bool(value))
                        checkbox_layout.addWidget(check_box)
                        checkbox_layout.setAlignment(Qt.AlignCenter)
                        checkbox_widget.setLayout(checkbox_layout)
                        tableWidget.setCellWidget(row_idx, col_idx, checkbox_widget)

                    else:
                        item = QTableWidgetItem(str(value))
                        if isinstance(cell_data, dict) and "user_role" in cell_data:
                            item.setData(Qt.UserRole, cell_data.get("user_role"))
                        elif set_name_user_role and col_idx == 0:
                            item.setData(Qt.UserRole, str(value))
                        tableWidget.setItem(row_idx, col_idx, item)

            self._refresh_checkboxes(tableWidget)
        finally:
            if block_name_signal:
                tableWidget.blockSignals(False)

    def _refresh_checkboxes(self, tableWidget):
        """按行重建复选框缓存，兼容不同表格列数。"""
        checkboxes = []
        checkbox_col = tableWidget.columnCount() - 1
        for row in range(tableWidget.rowCount()):
            checkbox_widget = tableWidget.cellWidget(row, checkbox_col)
            if checkbox_widget is None or checkbox_widget.layout() is None:
                continue
            checkbox = checkbox_widget.layout().itemAt(0).widget()
            if checkbox is not None:
                checkboxes.append((row, checkbox))

        if tableWidget == self.tableWidget1:
            self.checkboxes1 = checkboxes
        elif tableWidget == self.tableWidget2:
            self.checkboxes2 = checkboxes