# 事件数据传输密码配置
# 按照不同的 beamline 设置不同的密码

TRANSFER_PASSWORDS = {
    "BL01": "BL01@SANS#2024!xK9",
    "BL05": "BL05$HD_Secure$5pM8",
    "BL09": "BL09@TREND%Pwd2024#kL",
    "BL13": "BL13&ERNI$Safe@Pass9T",
    "BL14": "BL14#VSANS@Secure2024qX",
    "BL15_small": "BL15$HPND%Pwd#Safe8vD",
    "BL16": "BL16@MPI&Lock2024$fN",
    "BL18": "BL18#GPPD@Secure%Pass7jM",
}


def get_password_for_beamline(beamline: str) -> str:
    """根据 beamline 名称获取对应的密码"""
    return TRANSFER_PASSWORDS.get(beamline, "")


def verify_password(beamline: str, input_password: str) -> bool:
    """验证输入的密码是否与 beamline 对应的密码匹配"""
    correct_password = get_password_for_beamline(beamline)
    if not correct_password:
        return False
    return input_password == correct_password
