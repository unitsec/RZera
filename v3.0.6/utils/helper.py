import re,os,shutil,sys
import traceback
import xarray as xr
from pymatgen.core import Structure,Lattice
from pymatgen.analysis.diffraction.xrd import XRDCalculator
from pymatgen.symmetry.analyzer import SpacegroupAnalyzer
from typing import List, Tuple, Optional, Dict,Union
import math
import subprocess
import numpy as np
from rongzai.dataSvc import create_dataset

def get_resource_path(relative_path):
    """
    获取资源文件的绝对路径。
    在打包后，资源文件会被放在 `_internal` 目录中，因此需要动态调整路径。
    """
    if hasattr(sys, '_MEIPASS'):
        # 打包后的路径
        base_path = sys._MEIPASS
    else:
        # 开发时的路径
        base_path = os.path.dirname(os.path.dirname(__file__))
    return os.path.join(base_path, relative_path)


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


def calculate_dspacing_peaks(
        cif_path: str,
        d_range: Tuple[float, float] = (0.1, 50.0),  # 放宽默认范围
        lattice_mod: Optional[Dict[str, float]] = None,
        wavelength: Union[str, float] = 0.7,
        two_theta_range: Tuple[float, float] = (0, 180),
        verbose: bool = False  # 调试模式
) -> List[Tuple[float, float, List[Tuple[List[int], int]], float]]:
    """
    改进版本：处理晶胞参数修改后的衍射峰计算，支持自适应空间群
    """
    struct = Structure.from_file(cif_path)
    if lattice_mod:
        orig_lattice = struct.lattice
        new_params = {
            'a': lattice_mod.get('a', orig_lattice.a),
            'b': lattice_mod.get('b', orig_lattice.b),
            'c': lattice_mod.get('c', orig_lattice.c),
            'alpha': lattice_mod.get('alpha', orig_lattice.alpha),
            'beta': lattice_mod.get('beta', orig_lattice.beta),
            'gamma': lattice_mod.get('gamma', orig_lattice.gamma)
        }
        # 尝试创建新的晶格，如果参数非法会抛出异常
        try:
            new_lattice = Lattice.from_parameters(**new_params)
        except Exception as e:
            raise ValueError(f"Invalid lattice parameters: {new_params}. Error: {str(e)}")

        # 更新结构
        struct = Structure(
            lattice=new_lattice,
            species=struct.species,
            coords=struct.frac_coords,
            coords_are_cartesian=False
        )

        # 自动分析空间群
        analyzer = SpacegroupAnalyzer(struct)
        spacegroup = analyzer.get_space_group_symbol()
        if verbose:
            print(f"Detected space group: {spacegroup}")

        # 使用新的空间群更新结构
        struct = analyzer.get_conventional_standard_structure()

    # 计算 XRD 图谱
    xrd_calc = XRDCalculator(wavelength=wavelength)
    xrd_pattern = xrd_calc.get_pattern(struct, two_theta_range=two_theta_range)
    lambda_ = xrd_calc.wavelength

    if verbose:
        print(f"Wavelength: {lambda_} Å")
        print(f"Lattice after modification: {struct.lattice.parameters}")
        print(f"Space group: {analyzer.get_space_group_symbol()}")
        print(f"2θ values calculated: {xrd_pattern.x}")

    # 过滤 d-spacing 范围内的峰
    filtered_peaks = []
    for theta_deg, intensity, hkls in zip(xrd_pattern.x, xrd_pattern.y, xrd_pattern.hkls):
        theta_rad = math.radians(theta_deg / 2)
        try:
            d = lambda_ / (2 * math.sin(theta_rad))
        except ZeroDivisionError:
            continue
        if d_range[0] <= d <= d_range[1]:
            hkl_list = [(hkl["hkl"], hkl["multiplicity"]) for hkl in hkls]
            filtered_peaks.append((
                round(theta_deg, 4),
                round(intensity, 4),
                hkl_list,
                round(d, 4)
            ))

    if verbose and not filtered_peaks:
        print("Warning: No peaks found in d-range. Suggestions:")
        print(f"- Check if d-range {d_range} is appropriate")
        print(f"- Verify wavelength {lambda_} Å and structure validity")
        print(f"- Ensure space group {analyzer.get_space_group_symbol()} is correct")

    return sorted(filtered_peaks, key=lambda x: x[0])

def open_pdf(filename="User_Manual.pdf"):
    """打开帮助文档（安全地处理布尔/空值和不存在的文件）。

    如果传入 `False`，函数将直接返回（用于某些调用处以条件控制）。
    """
    # 防护：如果调用者传入 False（布尔），表示不打开任何文档，直接返回
    if filename is False:
        print("open_pdf: filename is False, skip opening PDF")
        return

    if not filename:
        filename = "User_Manual.pdf"

    # 构建资源路径并验证文件存在性
    pdf_path = get_resource_path(os.path.join("utils", filename))
    if not os.path.isfile(pdf_path):
        print(f"Failed to open PDF: file not found: {pdf_path}")
        return

    try:
        if sys.platform == 'linux' or sys.platform.startswith('linux'):
            # PyInstaller 打包后会修改 LD_LIBRARY_PATH 并将原始值备份到 LD_LIBRARY_PATH_ORIG。
            # 启动外部进程（如 evince）时必须恢复原始值，否则外部进程会加载打包内部的
            # 不兼容库（如 libsystemd.so.0），导致崩溃。
            env = os.environ.copy()
            orig = env.pop('LD_LIBRARY_PATH_ORIG', None)
            if orig is not None:
                env['LD_LIBRARY_PATH'] = orig
            else:
                env.pop('LD_LIBRARY_PATH', None)

            try:
                subprocess.Popen(['/usr/bin/evince', pdf_path], env=env)
            except Exception as e:
                print(f"Failed to open PDF: {e}")
        elif sys.platform == 'win32':
            os.startfile(pdf_path)
        elif sys.platform == 'darwin':
            os.system(f"open \"{pdf_path}\"")
        else:
            print("Unsupported OS")
    except Exception as e:
        print(f"Failed to open PDF: {str(e)}")

def load_dat_data(fn):
    try:
        x, y, e = np.loadtxt(fn, unpack=True)
        dataset = create_dataset(y, e, x, np.array([1]), np.array([0, 0, 0, 0, 0, 0, 0, 0]), 0.0, 0.0, extract_info_from_datfn(fn,"detector"),
                                 unit="dspacing")
        return dataset
    except Exception as e:
        print(f'Reason: {e}')
        traceback.print_exc()  # 打印异常的堆栈跟踪


def extract_info_from_datfn(datfn,info):
    if info == "runno":
        # 提取 RUN*******
        run_pattern = re.compile(r'RUN\d+')  # 匹配 RUN 后跟数字的部分
        runs = run_pattern.findall(datfn) # 返回列表，如 ['RUN12', 'RUN34']
        # 用 _ 间隔组成字符串
        run_string = '_'.join(runs)
        return run_string
    if info == "detector":
        group_pattern = re.compile(r'(?<![A-Za-z])group[A-Za-z]+(?![A-Za-z])', re.IGNORECASE)
        bank_pattern = re.compile(r'(?<=)bank[A-Za-z0-9]+(?=)', re.IGNORECASE)
        module_pattern = re.compile(r'(?<=)module[A-Za-z0-9]+(?=)', re.IGNORECASE)
        groups = group_pattern.findall(datfn)
        banks = bank_pattern.findall(datfn)
        modules = module_pattern.findall(datfn)
        if groups:
            group_string = '_'.join(groups)
            return group_string
        if banks:
            bank_string = '_'.join(banks)
            return bank_string
        if modules:
            module_string = '_'.join(modules)
            return module_string
    return ""

def float_or_nan(text: str):
    try:
        s = text.strip() if text is not None else ""
        return float(s) if s else math.nan
    except (ValueError, TypeError):
        return math.nan


DESIRED_COORDS = ['x','y','z','l2','two_theta','azimuthal','polar_width','azimuthal_width']
def upgrade_positions_to_8cols(ds: xr.Dataset,
                               var='positions',
                               pixel_dim='pixel',
                               coord_dim='coordinate',
                               verbose=False) -> xr.Dataset:
    if var not in ds:
        raise KeyError(f'{var} not in dataset')

    pos = ds[var]
    # 1) 包装成 DataArray + 规范维度名/顺序
    if not isinstance(pos, xr.DataArray):
        arr = np.asarray(pos)
        if arr.ndim != 2:
            raise ValueError(f'{var} must be 2-D, got {arr.shape}')
        nrow, ncol = arr.shape
        labels = ['x','y','z'] if ncol == 3 else [f'c{i}' for i in range(ncol)]
        pos = xr.DataArray(
            arr, dims=(pixel_dim, coord_dim),
            coords={pixel_dim: np.arange(nrow), coord_dim: (coord_dim, labels)},
            name=var,
        )

    if pos.ndim != 2:
        raise ValueError(f'{var} must be 2-D, got dims {pos.dims} shape {pos.shape}')

    dims = list(pos.dims)
    # 找到坐标维、像素维并统一命名
    if coord_dim in dims:
        cdim = coord_dim
        pdim = dims[0] if dims[1] == coord_dim else dims[1]
    else:
        if pos.sizes[dims[0]] <= 8 and pos.sizes[dims[1]] > 8:
            cdim, pdim = dims[0], dims[1]
        elif pos.sizes[dims[1]] <= 8 and pos.sizes[dims[0]] > 8:
            cdim, pdim = dims[1], dims[0]
        else:
            cdim, pdim = dims[1], dims[0]
        rename_map = {}
        if cdim != coord_dim: rename_map[cdim] = coord_dim
        if pdim != pixel_dim: rename_map[pdim] = pixel_dim
        if rename_map:
            pos = pos.rename(rename_map)
    # 维度顺序规范为 (pixel, coordinate)
    if pos.dims != (pixel_dim, coord_dim):
        pos = pos.transpose(pixel_dim, coord_dim)

    # 2) 补齐 coordinate 标签（当前列数）
    if coord_dim not in pos.coords or len(pos.coords[coord_dim]) != pos.sizes[coord_dim]:
        k = pos.sizes[coord_dim]
        labels = ['x','y','z'] if k == 3 else ([f'c{i}' for i in range(k)])
        pos = pos.assign_coords({coord_dim: (coord_dim, labels)})

    # 3) 先把“整个 Dataset”的 coordinate 维改到 8：这是关键！
    # 如果 Dataset 中已经有 coordinate 维（长度 3），通过 reindex 扩到 8；
    # 其他共享该维的变量会一起被扩展，缺失填 0（或 NaN，下面设置为 0）
    if coord_dim in ds.sizes and ds.sizes[coord_dim] != len(DESIRED_COORDS):
        ds = ds.reindex({coord_dim: DESIRED_COORDS}, fill_value=0.0)

    # 4) 再把 positions 本身在 coordinate 维上补齐到 8（缺的填 0）
    pos8 = pos.reindex({coord_dim: DESIRED_COORDS}, fill_value=0.0)
    pos8.attrs.update(pos.attrs)
    pos8.attrs['units'] = 'meter'

    if verbose:
        print('[upgrade] before:', list(pos.dims), tuple(pos.sizes[d] for d in pos.dims))
        print('[upgrade] after :', pos8.dims, pos8.shape)
        print('[upgrade] coord :', list(pos8.coords[coord_dim].values))

    # 5) 赋回 Dataset（此时 ds 的 coordinate 维已是 8，不会再被截成 3）
    return ds.assign({var: pos8})


def upgrade_runno(dataset, filename):
    """
    如果dataset没有runno属性，则从文件名中提取runno并赋值
    
    Args:
        dataset: 数据集对象
        filename: 文件路径或文件名
        
    Returns:
        dataset: 更新了runno属性的dataset
    """
    # 检查dataset是否已有runno属性且不为空
    try:
        if hasattr(dataset, 'runno') and getattr(dataset, 'runno', None) not in [None, ""]:
            # 如果已有runno且不为空，直接返回
            return dataset
    except:
        pass
    
    # 从文件名中提取runno
    runno_str = extract_info_from_datfn(filename, "runno")
    
    if not runno_str:
        # 如果没有提取到，使用文件名（去除扩展名）作为备选
        basename = os.path.basename(filename)
        name_without_ext = os.path.splitext(basename)[0]
        runno_str = name_without_ext
    
    # 尝试不同的方式设置runno属性
    try:
        # 方法1: 直接设置属性
        object.__setattr__(dataset, 'runno', runno_str)
    except:
        try:
            # 方法2: 使用 attrs 字典
            if hasattr(dataset, 'attrs'):
                dataset.attrs['runno'] = runno_str
        except:
            try:
                # 方法3: 使用 __dict__ 
                if hasattr(dataset, '__dict__'):
                    dataset.__dict__['runno'] = runno_str
            except:
                # 如果所有方法都失败，打印警告但不抛出异常
                print(f"Warning: Cannot set runno attribute for dataset from file: {filename}")

    return dataset

