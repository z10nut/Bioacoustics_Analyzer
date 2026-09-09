import os
import shutil
import subprocess
import sys

sep = ';' if os.name == 'nt' else ':'

args = [
    sys.executable, '-m', 'PyInstaller',
    'main.py',
    '--name=BioacousticsAnalyzer',
    '--windowed',
    '--onedir',
    '--hidden-import=sklearn',
    '--hidden-import=librosa',
    '--hidden-import=tensorflow',
    '--collect-all=sklearn',
    '--collect-all=librosa',
    '--collect-all=scipy',
    '--collect-all=tensorflow',
    f'--add-data=gui/styles/main_styles.qss{sep}gui/styles',
    '--noconfirm'
]

print("Running PyInstaller...")
subprocess.run(args, check=True)

print("PyInstaller finished. Applying patch for scikit-learn DLLs...")

if os.name == 'nt':
    internal_dir = os.path.join('dist', 'BioacousticsAnalyzer', '_internal')
    sklearn_libs_dest = os.path.join(internal_dir, 'sklearn', '.libs')
    
    os.makedirs(sklearn_libs_dest, exist_ok=True)
    
    msvcp_src = os.path.join(internal_dir, 'msvcp140.dll')
    msvcp140_1_src = os.path.join(internal_dir, 'msvcp140_1.dll')
    
    if os.path.exists(msvcp_src):
        shutil.copy(msvcp_src, sklearn_libs_dest)
        print("SUCCESS: Copied msvcp140.dll to sklearn/.libs")
        
    if os.path.exists(msvcp140_1_src):
        shutil.copy(msvcp140_1_src, sklearn_libs_dest)
        print("SUCCESS: Copied msvcp140_1.dll to sklearn/.libs")