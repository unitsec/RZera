# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import (
    copy_metadata,
    collect_data_files,
    collect_dynamic_libs,
    collect_submodules,
)
from PyInstaller.building.build_main import TOC
import os, sys, glob
from importlib import util

# 当前 conda 环境路径
conda_env_path = os.environ.get('CONDA_PREFIX', os.path.dirname(sys.executable))
if not conda_env_path:
    raise RuntimeError("Could not determine the conda environment path")
print(f"Detected conda environment path: {conda_env_path}")

# 数据文件（保留你的）
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
    (os.path.join(conda_env_path, 'Library', 'share', 'cctbx', 'libtbx_env'), './Library/share/cctbx'),
]
datas += copy_metadata('numpy')
# 先去掉 datas 中关于 BL01_SANS/BL14_VSANS 的 ('./BL01_SANS/*', ...)，再加：
datas += add_directory_tree('./BL01_SANS', 'BL01_SANS')
datas += add_directory_tree('./BL14_VSANS', 'BL14_VSANS')

# 动态获取 rongzai 包路径
spec = util.find_spec('rongzai')
if not spec or not spec.origin:
    raise RuntimeError("Package 'rongzai' is not found")
rongzai_path = os.path.dirname(spec.origin)
print("rongzai_path:", rongzai_path)

# 收集动态库（重要：对 sklearn / torch 用 collect_dynamic_libs）
binaries = []
binaries += collect_dynamic_libs('PyQt5')
# Python 编辑器所需：QScintilla 动态库
try:
    binaries += collect_dynamic_libs('PyQt5.Qsci')
except Exception as e:
    print(f"Warning: Could not collect PyQt5.Qsci binaries: {e}")
binaries += collect_dynamic_libs('numpy')
binaries += collect_dynamic_libs('scipy')
binaries += collect_dynamic_libs('sklearn')   # 修正：收集 sklearn 的 .pyd/.dll
binaries += collect_dynamic_libs('torch')     # 修正：收集 torch 的 .pyd/.dll（GPU 版必须）

# 你的本地 libs
binaries += [(os.path.join(rongzai_path, 'libs', '*'), './libs')]

# 可选：sklearn/pymatgen 的数据文件（非 DLL）
datas += collect_data_files('sklearn', include_py_files=True)
datas += collect_data_files('pymatgen', include_py_files=True)
datas += collect_data_files('openpyxl', include_py_files=True)

a = Analysis(
    ['rzera2.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=[
        'PyQt5.QtXml',
        # Python 编辑器所需：QScintilla 模块
        'PyQt5.Qsci',
        # 原有的隐藏导入
        'boost_python_meta_ext',
        'cctbx_asymmetric_map_ext',
        'utils.custom_components',
        *collect_submodules('sklearn'),  # 修正：收集 sklearn 子模块，避免延迟导入遗漏
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['torchvision'],
    noarchive=False,
    optimize=1,
)

# 从 conda 的 Library\bin 和 torch\lib 补齐运行时 DLL（BLAS/MKL/Fortran/OpenMP + CUDA/cuDNN）
libbin = os.path.join(conda_env_path, 'Library', 'bin')
torchlib = os.path.join(conda_env_path, 'Lib', 'site-packages', 'torch', 'lib')

def add_bin(src_path, rel_dir='.'):
    if os.path.isfile(src_path):
        dest = os.path.join(rel_dir, os.path.basename(src_path))
        a.binaries.append((dest, src_path, 'BINARY'))

# 注意：
# - OpenBLAS 与 MKL 二选一，但通配两套也可（只会拷贝存在的）
# - cuDNN 9 建议使用广泛通配，覆盖 graph/cnn/ops 的 infer/train 变体
patterns = [
    # conda-forge（OpenBLAS 栈）
    'libopenblas*.dll', 'libgfortran-*.dll', 'libquadmath-0.dll',
    'libwinpthread-1.dll', 'libgcc_s_seh-1.dll', 'libgomp-1.dll',
    # defaults（MKL 栈）
    'mkl_rt*.dll', 'mkl_*.dll', 'libiomp5md*.dll',
    # 兼容 MSVC OpenMP
    'vcomp140*.dll',
    # cuDNN 9（尽量全量）
    'cudnn64_9*.dll', 'cudnn_graph64_9*.dll',
    'cudnn_cnn_infer64_9*.dll', 'cudnn_cnn_train64_9*.dll',
    'cudnn_ops_infer64_9*.dll', 'cudnn_ops_train64_9*.dll',
    'cudnn_engines_precompiled64_9*.dll',
    # CUDA 12 常见依赖
    'cublas64_*.dll', 'cublasLt64_*.dll', 'cudart64_*.dll',
    'cusolver64_*.dll', 'cusparse64_*.dll', 'curand64_*.dll', 'cufft64_*.dll',
    'nvrtc64_*.dll', 'nvJitLink64_*.dll', 'nvToolsExt64_1.dll',
]
for d in (libbin, torchlib):
    if os.path.isdir(d):
        for pat in patterns:
            for p in glob.glob(os.path.join(d, pat)):
                add_bin(p, '.')

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
    upx=False,   # Windows 上建议关闭 UPX，避免 DLL 被压缩后异常
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
    upx=False,
    upx_exclude=[],
    name='rzera2',
)
