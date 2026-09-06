#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Medicion Obra - Generador de instalable Windows
# Copyright (C) 2026 JMBernabeu - GPL-3.0-or-later
#
# Uso (en Windows con Python 3.8+):
#   pip install pyinstaller
#   python build_windows.py
#
import os, subprocess, sys, shutil

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS = ['mediotec.html', 'sw.js', 'manifest.json', 'icon-192.png', 'icon-512.png']
ASSETS_DIR_NAME = 'assets'
DIST_DIR = os.path.join(ROOT, 'dist')
BUILD_DIR = os.path.join(ROOT, 'build', 'windows')
SERVER = os.path.join(ROOT, 'backend', 'server_windows.py')
ENTRY = os.path.join(ROOT, 'backend', 'entry_windows.py')
ICON = os.path.join(ROOT, 'icon-512.png')


def ensure_entry():
    code = (
        'import sys, os\n'
        'sys.path.insert(0, os.path.join(os.path.dirname(__file__)))\n'
        'from server_windows import main\n'
        'main()\n'
    )
    with open(ENTRY, 'w', encoding='utf-8') as f:
        f.write(code)
    print('  entry_windows.py creado')


def build():
    os.makedirs(DIST_DIR, exist_ok=True)
    os.makedirs(BUILD_DIR, exist_ok=True)

    ensure_entry()

    add_data = []
    for a in ASSETS:
        src = os.path.join(ROOT, a)
        if not os.path.exists(src):
            print('  AVISO: falta %s' % a)
            continue
        if sys.platform == 'win32':
            add_data.append('%s;%s' % (src, ASSETS_DIR_NAME))
        else:
            add_data.append('%s:%s' % (src, ASSETS_DIR_NAME))

    cmd = [
        sys.executable, '-m', 'PyInstaller',
        '--onefile',
        '--name', 'MedicionObra',
        '--distpath', DIST_DIR,
        '--workpath', BUILD_DIR,
        '--specpath', BUILD_DIR,
    ]

    if sys.platform == 'win32':
        cmd += ['--noconsole']

    for d in add_data:
        cmd += ['--add-data', d]

    if sys.platform == 'win32' and os.path.exists(ICON):
        ico_path = os.path.join(BUILD_DIR, 'icon.ico')
        try:
            from PIL import Image
            img = Image.open(ICON)
            img.save(ico_path, format='ICO', sizes=[(16,16),(32,32),(48,48),(64,64),(128,128),(256,256)])
            cmd += ['--icon', ico_path]
        except ImportError:
            print('  AVISO: Pillow no instalado, se omite icono. pip install Pillow')

    cmd.append(ENTRY)

    print('Ejecutando PyInstaller ...')
    print('  CMD: %s' % ' '.join(cmd))
    result = subprocess.run(cmd, cwd=ROOT)
    if result.returncode != 0:
        print('ERROR: PyInstaller fallo con codigo %d' % result.returncode)
        sys.exit(1)

    binary = os.path.join(DIST_DIR, 'MedicionObra.exe' if sys.platform == 'win32' else 'MedicionObra')
    if os.path.exists(binary):
        size_kb = os.path.getsize(binary) // 1024
        print('Generado: %s (%d KB)' % (binary, size_kb))
    else:
        print('Generado en: %s' % DIST_DIR)

    if os.path.exists(ENTRY):
        os.remove(ENTRY)


if __name__ == '__main__':
    build()
