from PyQt5.QtCore import Qt
import traceback
from workers.ui_mapping import pdf_mapping
from drneutron.python.algSvc.instrument.CSNS_PDF import CSNS_PDF
import os, sys, json


class data_plot:
    def plot_data(self,plot_list,plot_list_dict,canvas,ax,xlabel,ylabel,clear_axis=True):
        if clear_axis:
            ax.clear()
        for index in range(1, plot_list.count()):
            item = plot_list.item(index)
            if item.checkState() == Qt.Checked:
                [x, y, *_] = plot_list_dict[item.text()]
                self.draw_plot(x, y, item.text(), xlabel, ylabel, ax)

        self.finalize_figure(ax,canvas)

    def plot_sq_data(self,sam_list,other_list,plot_list_dict,canvas,ax,qlabel,dlabel,ylabel):
        for index in range(1, sam_list.count()):
            item = sam_list.item(index)
            if item.checkState() == Qt.Checked:
                self.plot_data(sam_list,plot_list_dict['sam_list'],canvas,ax,qlabel,ylabel)
                return
        self.plot_data(other_list,plot_list_dict['other_list'],canvas,ax,dlabel,ylabel)



    def plot_pdf_data(self, window, pdf_config, plot_list, plot_list_dict, canvas, ax, xlabel, ylabel):
        try:
            if getattr(sys, 'frozen', False):
                temp_dir = getattr(sys, '_MEIPASS', os.path.abspath(os.path.dirname(sys.executable)))
                bl16_config = os.path.join(temp_dir, 'bl16_config.json')
            else:
                temp_dir = os.path.abspath(os.path.dirname(__file__))
                bl16_config = os.path.join(os.path.dirname(temp_dir), 'utils_ui', 'bl16_config.json')

            with open(bl16_config, 'r', encoding='utf-8') as json_file:
                bl16_configure = json.load(json_file)
            pdf_config = pdf_mapping(window, pdf_config)
            configure = {**pdf_config, **bl16_configure}
            CSNS_PDF_instance = CSNS_PDF(configure, 'bank5')
            ax.clear()
            for index in range(1, plot_list.count()):  # 从 1 开始，跳过 "ALL" 条目
                item = plot_list.item(index)
                if item.checkState() == Qt.Checked:
                    [q, sq, sq_e, _] = plot_list_dict[item.text()]
                    r, data = CSNS_PDF_instance.PDF(q, sq, sq_e)
                    self.draw_plot(r, data, 'PDF_' + item.text()[:-3], xlabel, ylabel, ax)  # 绘制数据
                    self.finalize_figure(ax, canvas)

            self.finalize_figure(ax, canvas)
        except Exception as e:
            print(f'Failed to plot. Reason: {e}')
            traceback.print_exc()

    def draw_plot(self, x, y, label, xlabel, ylabel, ax):
        ax.plot(x, y, 'o-',label=label,markersize=3, linewidth=1)
        ax.set_xlabel(xlabel, fontdict={'fontsize': 12})
        ax.set_ylabel(ylabel, fontdict={'fontsize': 12})
        fig = ax.get_figure()
        fig.tight_layout()

    def finalize_figure(self,ax,canvas):
        handles, labels = ax.get_legend_handles_labels()
        if handles:
            ax.legend(handles, labels, fontsize=7,ncol=2)
        else:
            print("No artists with labels found.")
        canvas.draw()
