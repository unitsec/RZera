import re


def extract_number(filename):
    match = re.search(r'_([0-9]+)', filename)
    if match:
        return int(match.group(1))
    return None  # 如果没有找到数字，返回 None


def lineedit_clear(run_filePaths, run_text):
    run_filePaths.clear()
    run_text.setText('')