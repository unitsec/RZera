# 自定义的限制输入格式的类，限制输入只能为非零整数

from PyQt5 import QtGui

class NonZeroIntValidator(QtGui.QIntValidator):
    def __init__(self, bottom, top, parent=None):
        super().__init__(bottom, top, parent)

    def validate(self, input_str, pos):
        if input_str == "0":
            return QtGui.QValidator.Invalid, input_str, pos
        return super().validate(input_str, pos)