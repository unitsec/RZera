# 事件数据传输密码配置
# 按照不同的 beamline 设置不同的密码

TRANSFER_PASSWORDS = {
    "BL01": "********",
    "BL05": "********",
    "BL09": "********",
    "BL13": "********",
    "BL14": "********",
    "BL15_small": "********",
    "BL16": "********",
    "BL18": "********",
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
