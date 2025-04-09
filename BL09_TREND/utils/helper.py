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

def refresh(filterbox,list_dict,change_items):
    filterbox.clear()
    for name in list_dict.keys():
        name_elements = name.split('_')
        filter_elements = filterbox.get_item_names()
        for name_element in name_elements:
            if name_element not in filter_elements:
                filterbox.add_item(name_element)
    change_items.filter_items([])

# 删除输入的列表和控件中的内容
def lineedit_clear(run_filePaths, run_text):
    run_filePaths.clear()
    run_text.setText('')

def make_ignore_func(exclude):
    def ignore_func(directory, files):
        # 返回与排除列表匹配的文件或目录列表
        ignored_files = []
        for ex in exclude:
            if '*' in ex:  # 处理包含 * 的模式
                # 使用 str.replace() 方法将 '*' 替换为对应的字符串
                clean_pattern = ex.replace('*', '')
                for f in files:
                    if ex.startswith('*') and ex.endswith('*'):
                        # 模式如 *tensorflow*，匹配包含 clean_pattern 的所有文件
                        if clean_pattern in f:
                            ignored_files.append(f)
                    elif ex.startswith('*'):
                        # 模式如 *tensorflow，匹配以 clean_pattern 结尾的文件
                        if f.endswith(clean_pattern):
                            ignored_files.append(f)
                    elif ex.endswith('*'):
                        # 模式如 tensorflow*，匹配以 clean_pattern 开头的文件
                        if f.startswith(clean_pattern):
                            ignored_files.append(f)
            else:
                ignored_files.extend([f for f in files if f == ex])
        return ignored_files
    return ignore_func

def copy_specified_items(source_dir, target_dir, items_to_copy, exclude=None):
    """
    将指定的文件和文件夹从源目录复制到目标目录，并根据排除列表排除特定目录。
    """
    # 确保目标目录存在
    os.makedirs(target_dir, exist_ok=True)

    # 使用 make_ignore_func 创建一个 ignore_func，传入排除列表
    ignore_function = make_ignore_func(exclude) if exclude else None

    for item_name in items_to_copy:
        # 构建源和目标的完整路径
        source_item = os.path.join(source_dir, item_name)
        target_item = os.path.join(target_dir, item_name)

        # 检查源路径是否存在
        if not os.path.exists(source_item):
            print(f"{item_name} does not exist in the source directory.")
            continue

        # 如果是文件夹
        if os.path.isdir(source_item):
            # 使用 copytree 进行复制，并排除指定项
            shutil.copytree(source_item, target_item, ignore=ignore_function)
            print(f"Copied folder {item_name} to {target_item}")

        # 如果是文件，直接复制
        elif os.path.isfile(source_item):
            shutil.copy2(source_item, target_item)
            print(f"Copied file {item_name} to {target_item}")