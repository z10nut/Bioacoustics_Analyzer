import os
import sklearn
import PyInstaller.__main__

sklearn_dir = os.path.dirname(sklearn.__file__)
sklearn_libs = os.path.join(sklearn_dir, '.libs')

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

if os.path.exists(sklearn_libs):
    args.append(f'--add-binary={sklearn_libs}/*{sep}sklearn/.libs')

PyInstaller.__main__.run(args)