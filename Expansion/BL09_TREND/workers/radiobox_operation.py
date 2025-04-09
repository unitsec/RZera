from PyQt5.QtWidgets import QRadioButton


def select_d_peaks(checked):
    # 获取发出信号的 QRadioButton
    radio_button = QRadioButton.sender()
    print(radio_button)

    if checked:
        print(f"{radio_button.text()} is selected")
