import re,os,shutil
import traceback


# (该函数用来查询文件名中是否含“_数字”。该函数用于time slice)
def extract_number(filename):
    match = re.search(r'_([0-9]+)', filename)
    if match:
        return int(match.group(1))
    return None  # 如果没有找到数字，返回 None


# 创建并显示任意窗口类的实例（弹出自定义窗口）
def pop_window(window_class, main_window):
    try:
        dialog = window_class(main_window)
        dialog.show()
        return dialog
    except Exception as e:
        print(f"An error occurred: {e}")
        traceback.print_exc()  # 打印异常的堆栈跟踪


# 删除输入的列表和控件中的内容
def lineedit_clear(run_filePaths, run_text):
    run_filePaths.clear()
    run_text.setText('')

def ignore_pycache(dir, files):
    """
    忽略 __pycache__ 目录。
    """
    return [f for f in files if f == '__pycache__']

def copy_specified_items(source_dir, target_dir, items_to_copy):
    """
    将指定的文件和文件夹从源目录复制到目标目录，忽略 __pycache__ 目录。

    :param source_dir: 源工程目录的路径
    :param target_dir: 目标目录的路径
    :param items_to_copy: 需要复制的文件和文件夹名称列表
    """
    # 确保目标目录存在
    os.makedirs(target_dir, exist_ok=True)

    for item_name in items_to_copy:
        # 构建源和目标的完整路径
        source_item = os.path.join(source_dir, item_name)
        target_item = os.path.join(target_dir, item_name)

        # 检查源路径是否存在
        if not os.path.exists(source_item):
            print(f"{item_name} does not exist in the source directory.")
            continue

        # 如果是文件夹，使用 copytree 复制，并使用 ignore 参数排除 __pycache__
        if os.path.isdir(source_item):
            shutil.copytree(source_item, target_item, ignore=ignore_pycache)
            print(f"Copied folder {item_name} to {target_item}")

        # 如果是文件，使用 copy2 复制
        elif os.path.isfile(source_item):
            shutil.copy2(source_item, target_item)
            print(f"Copied file {item_name} to {target_item}")