#!/usr/bin/env python
# -*- coding: UTF-8 -*-
'''
@Project        ：BL14_VSANS 
@File           ：pack.py
@Author         ：zhongjiajun@ihep.ac.cn
@Date           ：2025/7/3 10:33 
@Desctiption    :
'''
import os
import sys


# 获取当前运行目录
def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        # base_path = sys._MEIPASS
        base_path = os.path.dirname(sys._MEIPASS)
    except AttributeError:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)