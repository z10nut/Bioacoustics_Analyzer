import os
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
    '--collect-all=tensorflow',
    f'--add-data=gui/styles/main_styles.qss{sep}gui/styles',
    '--noconfirm'
]

PyInstaller.__main__.run(args)