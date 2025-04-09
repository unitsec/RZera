from PyQt5.QtCore import Qt
import traceback
from BL09_TREND.workers.ui_mapping import pdf_mapping
# from rongzai.algSvc.instrument.CSNS_PDF import CSNS_PDF
import os, sys, json
# from rongzai.algSvc.base import (interpolate,cal_PDF,merge_all_curves,rebin,
                        # generate_x,strip_peaks,smooth)


class data_plot:
    def plot_data(self,plot_list,plot_list_dict,canvas,ax,xlabel,ylabel,clear_axis=True):
        try:
            if clear_axis:
                ax.clear()  # 根据 clear_axis 参数决定是否清除坐标轴上的图形和图例
            for index in range(1, plot_list.count()):  # 从 1 开始，跳过 "ALL" 条目
                item = plot_list.item(index)
                # 如果 "ALL" 被勾选，或者当前条目被勾选，则绘制数据
                if item.checkState() == Qt.Checked:
                    [x, y, *_] = plot_list_dict[item.text()]
                    self.draw_plot(x, y, item.text(), xlabel, ylabel, ax)  # 绘制数据

            self.finalize_figure(ax,canvas)  # Finalize the drawing and display
        except Exception as e:
            print(f'Failed to plot. Reason: {e}')
            traceback.print_exc()  # 打印异常的堆栈跟踪

    def plot_sq_data(self,sam_list,other_list,plot_list_dict,canvas,ax,qlabel,dlabel,ylabel):
        try:
            # 从第二项开始遍历每个条目，索引从 1 开始
            for index in range(1, sam_list.count()):
                item = sam_list.item(index)
                # 检查条目是否被勾选
                if item.checkState() == Qt.Checked:
                    # 执行某个操作
                    self.plot_data(sam_list,plot_list_dict['sam_list'],canvas,ax,qlabel,ylabel)
                    return  # 由于至少找到了一个勾选的条目，可以结束函数运行
            self.plot_data(other_list,plot_list_dict['other_list'],canvas,ax,dlabel,ylabel)
        except Exception as e:
            print(f'Failed to plot. Reason: {e}')
            traceback.print_exc()  # 打印异常的堆栈跟踪



    def plot_pdf_data(self, window, pdf_config, plot_list, plot_list_dict, canvas, ax, xlabel, ylabel):
        try:
            # 如果是 PyInstaller 打包后的临时目录中运行
            if getattr(sys, 'frozen', False):
                # 获取 PyInstaller 打包后的临时目录路径
                temp_dir = getattr(sys, '_MEIPASS', os.path.abspath(os.path.dirname(sys.executable)))
                BL09_config = os.path.join(temp_dir, 'BL09_config.json')
            else:
                # 如果是在源码中运行
                temp_dir = os.path.abspath(os.path.dirname(__file__))
                BL09_config = os.path.join(os.path.dirname(temp_dir), 'workers',
                                           'BL09_config.json')

            with open(BL09_config, 'r', encoding='utf-8') as json_file:
                BL09_configure = json.load(json_file)
            pdf_config = pdf_mapping(window, pdf_config)
            configure = {**pdf_config, **BL09_configure}
            CSNS_PDF_instance = CSNS_PDF(configure, 'bank2')
            ax.clear()  # 清除坐标轴上的图形和图例
            for index in range(1, plot_list.count()):  # 从 1 开始，跳过 "ALL" 条目
                item = plot_list.item(index)
                if item.checkState() == Qt.Checked:
                    [q, sq, sq_e, _] = plot_list_dict[item.text()]
                    r, data = CSNS_PDF_instance.PDF(q, sq, sq_e)
                    # newX = generate_x(pdf_config["q_rebin"][0],
                    #                   pdf_config["q_rebin"][1],
                    #                   pdf_config["q_rebin"][2], "uniform")
                    # newY, newE = interpolate(q, sq, sq_e, newX)
                    # r = generate_x(pdf_config["r_rebin"][0],
                    #                pdf_config["r_rebin"][1],
                    #                pdf_config["r_rebin"][2],
                    #                "uniform")
                    # data = cal_PDF(r, newX, newY, pdf_config["PDF_type"],
                    #                rho0=CSNS_PDF_instance.conf["sample_property"]["density_num"],
                    #                lorch=pdf_config["lorch"])
                    self.draw_plot(r, data, 'PDF_' + item.text()[:-3], xlabel, ylabel, ax)  # 绘制数据
                    self.finalize_figure(ax, canvas)

            self.finalize_figure(ax, canvas)  # Finalize the drawing and display
        except Exception as e:
            print(f'Failed to plot. Reason: {e}')
            traceback.print_exc()  # 打印异常的堆栈跟踪

    def draw_plot(self, x, y, label, xlabel, ylabel, ax):
        ax.plot(x, y, 'o-',label=label,markersize=3, linewidth=1)  # 在当前的坐标轴上绘制数据
        # 设置 X 轴和 Y 轴的标签名
        ax.set_xlabel(xlabel, fontdict={'fontsize': 12})
        ax.set_ylabel(ylabel, fontdict={'fontsize': 12})
        fig = ax.get_figure()
        fig.tight_layout()  # 设置为紧凑布局

    def finalize_figure(self,ax,canvas):
        handles, labels = ax.get_legend_handles_labels()
        if handles:
            ax.legend(handles, labels, fontsize=7,ncol=2)  # 如果有，添加图例
        else:
            print("No artists with labels found.")  # 如果没有，打印消息
        canvas.draw()  # 完成绘图
