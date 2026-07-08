import traceback
import copy
from PyQt5.QtGui import QDoubleValidator, QIntValidator
from rongzai.algSvc.instrument.pdf import calculate_PDF_from_sq
from rongzai.utils import generate_x
from utils.ui.BaseUI import CollapsibleWidget
from rongzai.algSvc.base import get_sample_properties

class sq2pdf(CollapsibleWidget):
    def __init__(self, parent):
        super(sq2pdf, self).__init__("Get PDF", "utils/ui/sq2pdf.ui", parent)
        self.parent = parent

        self.double_validator = QDoubleValidator()
        self.start.setValidator(self.double_validator)
        self.end.setValidator(self.double_validator)
        self.self_term.setValidator(self.double_validator)
        self.int_validator = QIntValidator()
        self.number.setValidator(self.int_validator)

    def run(self):
        try:
            if self.toggle_button.isChecked():
                r = generate_x(float(self.start.text()), float(self.end.text()), int(self.number.text()))
                data_list = []
                data_dict = {item['name']: item for item in self.parent.data_list}
                for data in self.parent.data_list:
                    if "sq_data" in data:
                        data_list.append(data['name'])
                if self.pdf_type.currentText() == "G(r)":
                    pdf_type = "G_r"
                elif self.pdf_type.currentText() == "g(r)":
                    pdf_type = "g_r"
                elif self.pdf_type.currentText() == "RDF":
                    pdf_type = "RDF"
                for data in data_list:
                    if "density_num" not in data_dict[data]["correction_info"]:
                        info_cal = get_sample_properties(data_dict[data]["correction_info"])
                        data_dict[data]["correction_info"]["density_num"] = info_cal["density_num"]
                    dr = calculate_PDF_from_sq(data_dict[data]['sq_data'][0],data_dict[data]['sq_data'][1],r,{"data_type":"s(q)",
                                                                                                         "self_term":float(self.self_term.text()),
                                                                                                         "lorch":self.lorch.isChecked(),
                                                                                                         "rho0":data_dict[data]["correction_info"]["density_num"] * data_dict[data]["correction_info"]["scale"],
                                                                                                         "PDF_type":pdf_type})
                    data_dict[data]["pdf_data"] = [r,dr]
                    data_dict[data]["pdf_type"] = pdf_type
        except Exception as e:
            print(f'Reason: {e}')
            traceback.print_exc()  # 打印异常的堆栈跟踪

    def plot_data(self):
        if self.toggle_button.isChecked():
            plot_data = []
            for data in self.parent.data_list:
                if "pdf_data" in data:
                    plot_data.append({"name":f"{data['name']}_qRange({data['sq_data'][0][0]:.2f}-{data['sq_data'][0][-1]:.2f})_rRange({data['pdf_data'][0][0]:.2f}-{data['pdf_data'][0][-1]:.2f})",
                                      "data":copy.deepcopy(data["pdf_data"]),
                                      "x_label": 'r (Å)',
                                      "y_label": "Intensity (a.u.)"
                                      })
            return plot_data
        else:
            return []

    def get_config(self):
        return {
            "is_use": self.toggle_button.isChecked(),
            "plot": self.plot.isChecked(),
            "start": self.start.text(),
            "end": self.end.text(),
            "number": self.number.text(),
            "lorch": self.lorch.isChecked(),
            "self_term": self.self_term.text(),
            "pdf_type": self.pdf_type.currentText()
        }

    def set_config(self,config):
        """根据配置更新模块状态"""
        self.toggle_button.setChecked(config.get("is_use", False))
        self.plot.setChecked(config.get("plot", False))
        self.start.setText(config.get("start", ""))
        self.end.setText(config.get("end", ""))
        self.number.setText(config.get("number", ""))
        self.lorch.setChecked(config.get("lorch", False))
        self.self_term.setText(config.get("self_term", ""))
        self.pdf_type.setCurrentText(config.get("pdf_type", "D(r)/G(r)"))

