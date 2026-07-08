from PyQt5.QtCore import Qt
import traceback
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
