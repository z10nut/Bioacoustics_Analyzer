import os
import shutil
import sklearn
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

print("PyInstaller finished. Applying manual patch for scikit-learn DLLs...")

if os.name == 'nt':
    sklearn_dir = os.path.dirname(sklearn.__file__)
    sklearn_libs_src = os.path.join(sklearn_dir, '.libs')
    dest_dir = os.path.join('dist', 'BioacousticsAnalyzer', '_internal', 'sklearn', '.libs')
    
    if os.path.exists(sklearn_libs_src):
        if os.path.exists(dest_dir):
            shutil.rmtree(dest_dir)
            
        shutil.copytree(sklearn_libs_src, dest_dir)
        print(f"SUCCESS: Copied content from {sklearn_libs_src} to {dest_dir}")
    else:
        print(f"WARNING: Source folder {sklearn_libs_src} not found on this system!")