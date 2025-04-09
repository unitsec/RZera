import sys
import numpy as np
import time,re
import os
#import json
import threading
import datetime
from PyQt5.QtCore import QThread,pyqtSignal
from PyQt5.QtWidgets import QApplication

from .redisHelper import getRedisHelper
from .redisHelper_oldThree import getRedisHelper_oldThree
import logging
from .logConfig import setup_logging
import traceback
import csv
from datetime import datetime, timedelta
import pandas as pd
import json
import subprocess

setup_logging(console=False)


# def check_value(z):
#     # 将 NaN 替换为 0.0
#     z = np.nan_to_num(z, nan=0.0)
#
#     # 获取有限值
#     finite_values = z[np.isfinite(z)]
#
#     # 检查是否有有限值
#     if finite_values.size > 0:
#         min_finite_value = np.min(finite_values)
#         max_finite_value = np.max(finite_values)
#
#         # 将负无穷大替换为最小的有限值
#         z[np.isneginf(z)] = min_finite_value
#
#         # 将正无穷大替换为最大的有限值
#         z[np.isposinf(z)] = max_finite_value
#     else:
#         # 处理没有有限值的情况，设为 0
#         z[np.isneginf(z)] = 0
#         z[np.isposinf(z)] = 0
#
#     return z


def check_value(z):
    z = np.nan_to_num(z,nan=0.0)
    z[np.isneginf(z)] = np.min(z[np.isfinite(z)])
    z[np.isposinf(z)] = np.max(z[np.isfinite(z)])
    return z

class redisThread(QThread):
    data_ready = pyqtSignal(dict)
    bank_1d = pyqtSignal(np.ndarray,np.ndarray,str)
    proton_charge = pyqtSignal(np.ndarray, np.ndarray, str)
    # bank_2d = pyqtSignal(np.ndarray, str)
    bank_2d = pyqtSignal(dict)
    module_1d = pyqtSignal(np.ndarray,np.ndarray)
    monitor_1d = pyqtSignal(np.ndarray,np.ndarray)
    logger = logging.getLogger(__name__)
    def __init__(
        self,
        parent,
        redisConf,
        allPath,
        bl = None
        ):
        super().__init__()
        #super(self.__class__, self).__init__()
        self.parent = parent
        if bl == "BL01":
            self.rds = getRedisHelper_oldThree(redisConf)
        else:
            self.rds = getRedisHelper(redisConf)
        self.test= False
        self.allPath= allPath

        self._lock = threading.Lock()
        self.working = True

        self.logger.info("start redis thread!")

        self.proton_charge_record = []

        self.last_save_time = datetime.now()

    def __del__(self):
        self.working = False

    def stop(self):
        self.working = False
        with self._lock:
            self._do_before_done()

    def _do_before_done(self):
        print('Good-Bye')
        self.sleep(1)
        print('World!!!')
        self.sleep(1)

    def get_bank_1d(self,bank):
        try:
            unit = self.parent.get_bank_unit()
            key = bank+"_"+unit+"_raw"
            path1 = self.allPath[key]
            key = bank+"_"+unit+"_counts_raw"
            path2=self.allPath[key]
            x = self.rds.readNumpyArray(path1)
            y = self.rds.readNumpyArray(path2)
            if x.size > 0 and x.size == y.size:
                if unit == "tof":
                    x = x/1000
                return x,y
            else:
                x = np.array([])
                y = np.array([])
                return x, y
        except:
            traceback.print_exc()
            x = np.array([])
            y = np.array([])
            return x, y

    def get_module_1d(self):
        try:
            unit = self.parent.get_module_unit()
            name = self.parent.get_module_name()
            key = name+"_"+unit
            path1 = self.allPath[key]
            key = name+"_"+unit+"_counts"
            path2 = self.allPath[key]
            x = self.rds.readNumpyArray(path1)
            y = self.rds.readNumpyArray(path2)
            if unit == "tof":
                x = x/1000
            return x,y
        except:
            x = np.array([])
            y = np.array([])
            return x, y

    def get_monitor_1d(self):
        unit = self.parent.get_monitor_unit()
        name = self.parent.get_monitor_name()
        key = name+"_"+unit
        path1 = self.allPath[key]
        key = name+"_"+unit+"_counts"
        path2 = self.allPath[key]
        x = self.rds.readNumpyArray(path1)
        y = self.rds.readNumpyArray(path2)
        if unit == "tof":
            x = x/1000
        return x,y

    def save_proton_charge_record(self):
        if not os.path.exists('./logs'):
            os.makedirs('./logs')

        if self.proton_charge_record:
            start_time = self.proton_charge_record[0][0].replace(":", "_")
            end_time = self.proton_charge_record[-1][0].replace(":", "_")
            filename = f"./logs/proton_charge_{start_time}_to_{end_time}.csv"

            with open(filename, mode='w', newline='') as file:
                writer = csv.writer(file)
                writer.writerow(["Time", "Proton Charge"])
                for record in self.proton_charge_record:
                    writer.writerow(record)

            print(f"Saved proton charge record to {filename}")

    def get_experiment_proton_charge(self):
        path = self.allPath["proton_charge_hist"]
        y = self.rds.readNumpyArray(path)
        x = np.arange(0, y.size)
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if y is None or y.size == 0:
            self.proton_charge_record.append((current_time, np.NaN))
        else:
            self.proton_charge_record.append((current_time, y[-1]))

        while self.proton_charge_record:
            record_time_str = self.proton_charge_record[0][0]
            record_time = datetime.strptime(record_time_str, "%Y-%m-%d %H:%M:%S")
            if datetime.now() - record_time >= timedelta(hours=24):
                self.proton_charge_record.pop(0)
            else:
                break

        # 保存记录每 12 小时
        current_datetime = datetime.now()
        if current_datetime - self.last_save_time >= timedelta(hours=12):
            self.save_proton_charge_record()
            self.last_save_time = current_datetime

        mode = self.parent.get_proton_charge_mode()

        if mode == 'short time series':
            return x, y
        elif mode == '24h (initial: RZera start)':
            times, values = zip(*self.proton_charge_record)
            times = [datetime.strptime(t, "%Y-%m-%d %H:%M:%S") for t in times]
            return np.array(times), np.array(values)

    def get_experiment_detector_counts(self):
        name = self.parent.get_module_name_experiment()
        key = name+"_counts_hist"
        path = self.allPath[key]
        y = self.rds.readNumpyArray(path)
        x = np.arange(0,y.size)
        return x,y

    def get_2d(self,name,mode='real'):
        #name = self.parent.get_module_name()
        #key = name+"_xy_image_x"
        #path1 = self.allPath[key]
        #key = name+"_xy_image_y"
        #path2=self.allPath[key]
        if name[-3:] == "qxy":
            key = name+"_value"
        else:
            key = name+"_xy_image_value"
        try:
            if mode == 'real':
                path=self.allPath[key]
                #x = self.rds.readNumpyArray(path1)
                #y = self.rds.readNumpyArray(path2)
                z = self.rds.readNumpyArray(path)
                z = check_value(z)
            else:
                upper_limit = np.random.randint(100)
                if name == 'bank2' or name == 'bank5':
                    z = np.random.randint(0, upper_limit, size=(5600, 50))
                else:
                    z = np.random.randint(0, upper_limit, size=(4800, 50))
            return z
        except:
            z = np.array([])
            return z

    def get_module_2d(self):
        #name = self.parent.get_module_name()
        #key = name+"_xy_image_x"
        #path1 = self.allPath[key]
        #key = name+"_xy_image_y"
        #path2=self.allPath[key]
        for name1 in range(1, 7):
            if name1 == '2' or name1 == '4':
                for name2 in range(1, 15):
                    name = 'module1' + str(name1).zfill(2) + str(name2).zfill(2)
                    key = name + "_xy_image_value"
                    try:
                        path = self.allPath[key]
                        # x = self.rds.readNumpyArray(path1)
                        # y = self.rds.readNumpyArray(path2)
                        z = self.rds.readNumpyArray(path)
                        z = check_value(z)
                        # 转换为 Pandas DataFrame
                        df = pd.DataFrame(z)
                        # 保存为 .csv 文件
                        df.to_csv(f'./{name}_xy_image_value.csv', index=False)
                    except Exception as e:
                        traceback.print_exc()  # 打印异常的堆栈跟踪
            else:
                for name2 in range(1, 13):
                    name = 'module1' + str(name1).zfill(2) + str(name2).zfill(2)
                    key = name + "_xy_image_value"
                    try:
                        path = self.allPath[key]
                        # x = self.rds.readNumpyArray(path1)
                        # y = self.rds.readNumpyArray(path2)
                        z = self.rds.readNumpyArray(path)
                        z = check_value(z)
                        # 转换为 Pandas DataFrame
                        df = pd.DataFrame(z)
                        # 保存为 .csv 文件
                        df.to_csv(f'./{name}_xy_image_value.csv', index=False)
                    except Exception as e:
                        traceback.print_exc()  # 打印异常的堆栈跟踪

    # 读取信息，保存到本地，然后发送到微信
    def set_wechat(self, BL_name, tab_name, wechat_map, detectorList):
        runno = self.rds.readStr(self.allPath["runno"])  # 获取runno
        runno = "RUN" + str(runno).zfill(7)
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) # 获取项目的根目录, __file__ 是当前脚本的路径
        history_folder = os.path.join(project_root, BL_name, "online", 'history') # 组织 history 文件夹的路径
        file_Path = os.path.join(history_folder, runno)  # 根据 runno 组织文件路径
        self.check_dir(file_Path)  # 检查文件路径是否存在
        self.writeWechatInfo(file_Path)
        for detector in detectorList:
            self.writeWechatData(file_Path, detector, wechat_map)
        if tab_name != 'Reduction':
            filename = file_Path + "/" + wechat_map[tab_name] + ".jpg"
            self.save_current_window_snapshot(filename)
        time.sleep(1)
        _cmd = 'scp -r ' + file_Path + ' tangm@202.38.129.18:/home/tangm/instrument/' + BL_name[:4]
        subprocess.Popen(_cmd, shell=True)


    # 查看路径是否存在，不存在就创建
    def check_dir(self, path):
        if os.path.exists(path):
            pass
        else:
            # os.mkdir(path)#create single folder
            os.makedirs(path)  # create path

    def writeWechatInfo(self, filePath):
        infoList = ["userID", "proposalID", "start_time", "end_time"]  # 设置一个包含元数据名称的列表
        confFile = filePath + "/summary.properties"  # 根据文件路径设置元数据路径
        context = ""
        with open(confFile, "w") as f:  # 打开元数据路径
            for i, name in enumerate(infoList):  # 开始遍历元数据名称
                value = self.rds.readStr(self.allPath[name])  # 根据元数据名称获取redis中的元数据路径并读取对应元数据？
                context += name + " = " + value  # 设置一个context,格式是“名称=路径”

                # 判断是否需要加换行符
                if i < len(infoList) - 1:
                    context += '\n'

            f.write(context)  # 写入元数据路径

    def writeWechatData(self, filePath, bank, wechat_map):
        try:
            x = self.rds.readNumpyArray(self.allPath[bank + "_d_raw"])
            y = self.rds.readNumpyArray(self.allPath[bank + "_d_counts_raw"])
            num = int(len(x) / 2000)
            if num > 1:
                x = x[::num]
                y = y[::num]
            #保留两位小数
            x = np.round(x, 2)
            y = np.round(y, 2)
            x, y = self.crop_zero_data(x, y)
            x, y = x.tolist(), y.tolist()
            data = []
            for i in range(len(x)):
                data.append([x[i], y[i]])
            conf = {}
            conf["title"] = {"text":""}
            #conf["xAxis"] = {"title": {"text": "dSpacing"}}
            conf["yAxis"] = {"title": {"text": "counts"}}
            conf["series"] = [{"data": data, "tooltip": {"headerFormat":"", "pointFormat": "d:{point.x}, I(d):{point.y}"}}]

            confFile = filePath + "/" + wechat_map[bank] + ".json"
            with open(confFile, "w") as jf:
                json.dump(conf, jf)
        except:
            traceback.print_exc()  # 打印异常的堆栈跟踪

    # def save_primary_screen_snapshot(self, filename):
    #     # filename = filePath+"/"+runno+"_"+tabNo+".jpg"
    #     # 获取主屏幕
    #     screen = QApplication.primaryScreen()
    #     # 捕获屏幕并转换为QPixmap
    #     pixmap = screen.grabWindow(0)
    #     # 保存图片
    #     pixmap.save(filename, quality=100)

    def save_current_window_snapshot(self, filename):
        QApplication.processEvents()
        pixmap = self.parent.grab() # 获取当前窗口的QPixmap
        # 保存图片
        if pixmap.save(filename, quality=100):
            pass
            # print(f"窗口快照已保存至 {filename}")
        else:
            print("保存图片时出错。")

    # def save_current_window_snapshot(self, filename):
    #     start_time = time.time()
    #     print(f"Snapshot started at {start_time}")
    #
    #     pixmap = self.parent.grab()  # 获取当前窗口的QPixmap
    #     snapshot_time = time.time()
    #     print(f"Pixmap grabbed at {snapshot_time}, elapsed: {snapshot_time - start_time}s")
    #
    #     # 保存图片
    #     if pixmap.save(filename, quality=100):
    #         print(f"Snapshot saved at {time.time()}, elapsed: {time.time() - snapshot_time}s")
    #     else:
    #         print("保存图片时出错。")
    #
    #     end_time = time.time()
    #     print(f"Snapshot process finished at {end_time}, total elapsed: {end_time - start_time}s")

    def set_user(self,infoList):
        data = {}
        for name in infoList:
            data[name]=self.rds.readStr(self.allPath[name])
            # print(data)
        #data["test"] = self.rds.readStr("/emd/control/run_control")
        #print(data)
        self.data_ready.emit(data)
        # self.parent.set_user(data)

    def set_bank_1d(self,bankList):
        try:
            # merged_bank ={'bank1to6': [], 'bank7_14': [], 'bank8_13': [], 'bank9_12': [], 'bank10_11': []}
            for bank in bankList:
                x,y = self.get_bank_1d(bank)
                # print(f'{bank} data:',np.shape(x),np.shape(y))
                x,y = self.crop_zero_data(x,y)
                self.bank_1d.emit(x, y, bank)
                    # self.parent.set_bank_1d(x, y, bank)
        except Exception as e:
            traceback.print_exc()  # 打印异常的堆栈跟踪

    def set_experiment_1d(self):
        try:
            x,y = self.get_experiment_proton_charge()
            if x.size>0 and x.size==y.size:
                self.proton_charge.emit(x, y, 'proton_charge')
                # self.parent.set_experiment_1d(x,y,"proton_charge")
            # x,y = self.get_experiment_detector_counts()
            # if x.size>0 and x.size==y.size:
            #     self.parent.set_experiment_1d(x,y,"detector_counts")
        except Exception as e:
            traceback.print_exc()  # 打印异常的堆栈跟踪


    def set_module_1d(self):
        try:
            x,y = self.get_module_1d()
            x, y = self.crop_zero_data(x, y)
            # if x.size>0 and x.size==y.size:
            self.module_1d.emit(x,y)
            # self.parent.set_module_1d(x,y)
        except:
            return


    def set_monitor_1d(self):
        try:
            x,y = self.get_monitor_1d()
            x, y = self.crop_zero_data(x, y)
            # if x.size>0 and x.size==y.size:
            self.monitor_1d.emit(x, y)
            # self.parent.set_monitor_1d(x,y)
        except Exception as e:
            logging.error("An error occurred", exc_info=True)

    def set_bank_2d(self,bankList):
        try:
            # self.get_module_2d()
            self.parent.global_vmin = None
            self.parent.global_vman = None
            z_dict = {}
            for bank in bankList:
                z = self.get_2d(bank,mode='real')
                z_dict[bank] = z
            self.bank_2d.emit(z_dict)
                # self.parent.set_bank_2d(z,bank)
        except Exception as e:
            traceback.print_exc()  # 打印异常的堆栈跟踪

    def set_module_2d(self):
        name = self.parent.get_module_name()
        z = self.get_2d(name)
        self.parent.set_module_2d(z)

    def set_instrument_2d(self):
        z = self.get_2d("module10101")
        self.parent.set_instrument_2d(z)

#################################################set the logic of showing history data########################################
    history_1d = pyqtSignal(np.ndarray, np.ndarray, str)
    history_runno_list = pyqtSignal(list)
    #The outline function
    def set_history(self, beamline, history_runno, groupList):
        try:
            # merged_bank ={'bank1to6': [], 'bank7_14': [], 'bank8_13': [], 'bank9_12': [], 'bank10_11': []}
            for group in groupList:
                x, y = self.get_history_1d(beamline, group, history_runno)
                x, y = self.crop_zero_data(x, y)
                self.history_1d.emit(x, y, group)
                    # self.parent.set_bank_1d(x, y, bank)
            runno_list = self.get_runno("**/rongzai/group*/*/d")
            self.history_runno_list.emit(runno_list)
        except Exception as e:
            traceback.print_exc()  # 打印异常的堆栈跟踪

    def get_runno(self, pattern):
        start_time = time.time()  # 记录开始时间
        try:
            keys = self.rds.scan_keys(pattern=pattern, count=1000) # SCAN the keys
            number_set = set()
            for key in keys:
                match = re.search(r'/RUN(\d+)/', key.decode('utf-8'))
                if match:
                    number_set.add(int(match.group(1)))  # 将匹配到的数字转换为整数并添加到集合中
        except Exception as e:
            print(f"Error occurred in get_runno: {str(e)}")
            return []
        finally:
            end_time = time.time()  # 记录结束时间
            elapsed_time = end_time - start_time  # 计算经过的时间
            print(f"get_runno executed in {elapsed_time:.4f} seconds")  # 输出所需时间
        # 将数字转为整数并排序
        sorted_numbers = sorted(number_set)  # 默认按整数值排序
        return sorted_numbers  # 返回排序后的列表

    def get_history_1d(self, beamline, group, runno):
        try:
            path1 = f"/{beamline}/rongzai/{group}/RUN{runno}/d"
            path2 = f"/{beamline}/rongzai/{group}/RUN{runno}/d_counts"
            x = self.rds.readNumpyArray(path1)
            y = self.rds.readNumpyArray(path2)
            if x.size > 0 and x.size == y.size:
                return x,y
            else:
                x = np.array([])
                y = np.array([])
                return x, y
        except:
            traceback.print_exc()
            x = np.array([])
            y = np.array([])
            return x, y
#############################################################################################################

    def crop_zero_data(self, x, y):
        # 检查输入是否为空
        if len(x) == 0 or len(y) == 0:
            return np.array([]), np.array([])

        non_zero_indices = np.where(y != 0)[0]

        if non_zero_indices.size > 0:
            start_index = non_zero_indices[0]
            end_index = non_zero_indices[-1]

            # 利用这些索引切片 x 和 y
            x_filtered = x[start_index:end_index + 1]
            y_filtered = y[start_index:end_index + 1]
        else:
            x_filtered = x  # 如果没有非零元素，不进行任何操作
            y_filtered = y

        return x_filtered, y_filtered
