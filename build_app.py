import os
import shutil
import sklearn
import PyInstaller.__main__

sep = ';' if os.name == 'nt' else ':'
args = [
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
    f'--add-data=gui/styles/main_styles.qss{sep}gui/styles',
    '--noconfirm'
]

PyInstaller.__main__.run(args)

if os.name == 'nt':
    sklearn_dir = os.path.dirname(sklearn.__file__)
    sklearn_libs_src = os.path.join(sklearn_dir, '.libs')
    
    dest_dir = os.path.join('dist', 'BioacousticsAnalyzer', '_internal', 'sklearn', '.libs')
    
    if os.path.exists(sklearn_libs_src):
        if os.path.exists(dest_dir):
            shutil.rmtree(dest_dir)
            
        shutil.copytree(sklearn_libs_src, dest_dir)
