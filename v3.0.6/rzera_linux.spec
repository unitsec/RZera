# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import copy_metadata
from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs, collect_submodules
from PyInstaller.building.build_main import TOC, Analysis, PYZ, EXE, COLLECT  # [FIX] 需要过滤/追加二进制
import os, sys, glob
from importlib import util

# 检测当前 Conda 环境的路径
conda_env_path = os.environ.get('CONDA_PREFIX', os.path.dirname(sys.executable))
if not conda_env_path:
    raise RuntimeError("Could not determine the conda environment path")
print(f"Detected conda environment path: {conda_env_path}")

# 通过在sys.path中找到site-packages
try:
    site_packages_path = next(p for p in sys.path if 'site-packages' in p)
except StopIteration:
    site_packages_path = os.path.join(conda_env_path, 'lib', f'python{sys.version_info.major}.{sys.version_info.minor}', 'site-packages')
print(f"Site-packages path: {site_packages_path}")

# 动态获取rongzai包路径
spec = util.find_spec('rongzai')
print(spec.origin)
if not spec or not spec.origin:
    raise RuntimeError("Package 'rongzai' is not found")
rongzai_path = os.path.dirname(spec.origin)

def collect_all_files_with_structure(src_folder, dest_folder):
    file_list = []
    for root, dirs, files in os.walk(src_folder):
        for file in files:
            abs_src_path = os.path.join(root, file)
            rel_path = os.path.relpath(abs_src_path, src_folder)
            target_path = os.path.join(dest_folder, rel_path)
            file_list.append((abs_src_path, os.path.dirname(target_path)))
    return file_list

datas = [
    ('./utils/conf_redis.json', '.'),
    ('./CSNS_Alg/configure/*', './CSNS_Alg/configure'),
    ('./param_data/model_weights/*', './param_data/model_weights'),
    ('./param_data/BL05/instrumentFiles/*', './param_data/BL05/instrumentFiles'),
    ('./param_data/BL09/instrumentFiles/*', './param_data/BL09/instrumentFiles'),
    ('./param_data/BL15/instrumentFiles_small/*', './param_data/BL15/instrumentFiles_small'),
    ('./param_data/BL15/instrumentFiles_big/*', './param_data/BL15/instrumentFiles_big'),
    ('./param_data/BL16/instrumentFiles/*', './param_data/BL16/instrumentFiles'),
    ('./BL16_MPI/ui/*.ui', './BL16_MPI/ui'),
    ('./BL15_HPND/ui/*.ui', './BL15_HPND/ui'),
    ('./BL09_TREND/ui/*.ui', './BL09_TREND/ui'),
    ('./utils/ui/*.ui', './utils/ui'),
    ('./logo/logo.qrc', './logo'),
    ('./logo/resized_rzera_logo.png', './logo'),
    ('./utils/User_Manual.pdf', './utils'),
    (os.path.join(conda_env_path, 'share', 'cctbx', 'libtbx_env'), './share/cctbx'),
    # [FIX] 移除 cudnn 收集，避免把 GPU 运行库打进来导致 ABI 冲突
    # (os.path.join(site_packages_path, 'nvidia', 'cudnn', 'lib', '*'), '.'),
]
datas += copy_metadata('numpy')

# 添加BL01和BL14的所有文件夹
def add_directory_tree(src_dir, dest_dir):
    datas = []
    for root, dirs, files in os.walk(src_dir):
        for file in files:
            src_path = os.path.join(root, file)
            rel_path = os.path.relpath(root, src_dir)
            # 目标目录
            dest_path = os.path.join(dest_dir, rel_path)
            datas.append((src_path, dest_path))
    return datas
datas += add_directory_tree('./BL01_SANS', 'BL01_SANS')
datas += add_directory_tree('./BL14_VSANS', 'BL14_VSANS')

# datas: 非二进制数据文件（pymatgen/openpyxl 的数据文件）
datas += collect_data_files('pymatgen', include_py_files=True)
datas += collect_data_files('openpyxl', include_py_files=True)
datas += collect_all_files_with_structure('./BL01_SANS', 'BL01_SANS')
datas += collect_all_files_with_structure('./BL14_VSANS', 'BL14_VSANS')

# binaries: 动态库 (.so) 等运行时二进制
binaries = []
# 收集常见 GUI / 数值库 的动态库
binaries += collect_dynamic_libs('PyQt5')
try:
    binaries += collect_dynamic_libs('PyQt5.Qsci')
except Exception:
    # Qsci 可能不存在，继续打包其他内容
    pass
binaries += collect_dynamic_libs('numpy')
binaries += collect_dynamic_libs('scipy')
binaries += collect_dynamic_libs('sklearn')
binaries += collect_dynamic_libs('torch')

# 保留项目自带的 libs 目录
binaries += [(os.path.join(rongzai_path, 'libs', '*'), './libs')]

a = Analysis(
    ['rzera2.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=[
        'PyQt5.QtXml',
        'boost_python_meta_ext',
        'cctbx_asymmetric_map_ext',
        'utils.custom_components',
        # 包含 sklearn 的 array_api_compat 兼容层子模块，确保像
        # "sklearn.externals.array_api_compat.numpy.fft" 这样的路径能被打包
        'sklearn.externals.array_api_compat.numpy.fft',
    ] + collect_submodules('sklearn.externals.array_api_compat') + collect_submodules('sklearn'),
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['torchvision'],
    noarchive=False,
    optimize=0,
)

# ---------------- [FIX] 从这里开始是修复 Security-Alert + 缺库 的关键 ----------------

# 统一/去重 C++ 运行时，避免混入系统旧库
a.binaries = TOC([
    (dest, src, typ)
    for (dest, src, typ) in a.binaries
    if os.path.basename(dest) not in ('libstdc++.so.6', 'libgcc_s.so.1')
       and os.path.basename(src)  not in ('libstdc++.so.6', 'libgcc_s.so.1')
])

# [FIX] 追加库时，按 TOC 正确顺序 (dest_name, src_path, 'BINARY')，dest 要相对路径
def add_bin(src_path, rel_dir='.'):
    name = os.path.join(rel_dir, os.path.basename(src_path))  # 放到 dist 根或子目录
    a.binaries.append((name, src_path, 'BINARY'))

# 使用 conda 环境中的 libstdc++/libgcc，避免 GLIBCXX 不匹配
add_bin(os.path.join(conda_env_path, 'lib', 'libstdc++.so.6'), '.')
add_bin(os.path.join(conda_env_path, 'lib', 'libgcc_s.so.1'), '.')

# 补齐 SciPy 所需 BLAS/LAPACK/Fortran 运行库（防止 libcblas/lapack not found）
for pat in ('libcblas.so*', 'liblapack.so*', 'libopenblas*.so*', 'libgfortran.so*', 'libquadmath.so*'):
    for p in glob.glob(os.path.join(conda_env_path, 'lib', pat)):
        add_bin(p, '.')

# ---------------- [FIX] 结束 ----------------

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='rzera2',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,  # [FIX] 先关 UPX，避免压缩 .so 带来不确定性
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['logo/resized_rzera_logo.ico'],
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,  # [FIX] 同上
    upx_exclude=[],
    name='rzera_3.0',
)
