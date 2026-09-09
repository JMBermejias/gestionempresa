#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Gestion Empresa - Generador de instalable Windows
# Copyright (C) 2026 JMBernabeu - GPL-3.0-or-later
#
# Uso (en Windows con Python 3.8+):
#   pip install pyinstaller
#   python build_windows.py
#
import os, subprocess, sys, shutil, re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS = ['mediotec.html', 'sw.js', 'manifest.json', 'icon-192.png', 'icon-512.png', 'favicon.ico']
ASSETS_DIR_NAME = 'assets'
DIST_DIR = os.path.join(ROOT, 'dist')
BUILD_DIR = os.path.join(ROOT, 'build', 'windows')
SERVER = os.path.join(ROOT, 'backend', 'server_windows.py')
ENTRY = os.path.join(ROOT, 'backend', 'entry_windows.py')
ICON = os.path.join(ROOT, 'icon-512.png')
FAVICON = os.path.join(ROOT, 'favicon.ico')


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


def ensure_favicon():
    if os.path.exists(FAVICON):
        print('  favicon.ico ya existe')
        return
    try:
        from PIL import Image
        img = Image.open(ICON)
        img.save(FAVICON, format='ICO', sizes=[(16,16),(32,32),(48,48),(64,64),(128,128),(256,256)])
        print('  favicon.ico generado desde icon-512.png')
    except ImportError:
        print('  AVISO: Pillow no instalado, no se puede generar favicon.ico')


def app_version():
    with open(os.path.join(ROOT, 'mediotec.html'), encoding='utf-8') as f:
        m = re.search(r"APP_VERSION='v?([0-9]+\.[0-9]+\.[0-9]+)'", f.read())
    return m.group(1) if m else '1.0.0'


def ensure_version_file():
    ver = app_version()
    parts = [int(x) for x in ver.split('.')]
    while len(parts) < 3:
        parts.append(0)
    major, minor, patch = parts[0], parts[1], parts[2]
    verfile = os.path.join(BUILD_DIR, 'version_info.txt')
    content = (
        "# UTF-8\n"
        "VSVersionInfo(\n"
        "  ffi=FixedFileInfo(\n"
        "    filevers=(%d, %d, %d, 0),\n"
        "    prodvers=(%d, %d, %d, 0),\n"
        "    mask=0x3f,\n"
        "    flags=0x0,\n"
        "    OS=0x40004,\n"
        "    fileType=0x1,\n"
        "    subtype=0x0,\n"
        "    date=(0, 0)\n"
        "  ),\n"
        "  kids=[\n"
        "    StringFileInfo([\n"
        "      StringTable(\n"
        "        r'040904B0',\n"
        "        [\n"
        "          StringStruct(r'CompanyName', u'JMBernabeu'),\n"
        "          StringStruct(r'FileDescription', u'Gestion Empresa'),\n"
        "          StringStruct(r'FileVersion', u'%s'),\n"
        "          StringStruct(r'InternalName', u'GestionEmpresa'),\n"
        "          StringStruct(r'OriginalFilename', u'GestionEmpresa.exe'),\n"
        "          StringStruct(r'ProductName', u'Gestion Empresa'),\n"
        "          StringStruct(r'ProductVersion', u'%s')\n"
        "        ]\n"
        "      )\n"
        "    ]),\n"
        "    VarFileInfo([VarStruct(r'Translation', [1033, 1200])])\n"
        "  ]\n"
        ")\n"
    ) % (major, minor, patch, major, minor, patch, ver, ver)
    with open(verfile, 'w', encoding='utf-8') as f:
        f.write(content)
    print('  version_info.txt generado (v%s)' % ver)
    return verfile


def build():
    os.makedirs(DIST_DIR, exist_ok=True)
    os.makedirs(BUILD_DIR, exist_ok=True)

    ensure_entry()
    ensure_favicon()
    version_file = None
    if sys.platform == 'win32':
        version_file = ensure_version_file()

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
        '--name', 'GestionEmpresa',
        '--distpath', DIST_DIR,
        '--workpath', BUILD_DIR,
        '--specpath', BUILD_DIR,
        '--noupx',
    ]

    if sys.platform == 'win32' and version_file:
        cmd += ['--version-file', version_file]

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

    binary = os.path.join(DIST_DIR, 'GestionEmpresa.exe' if sys.platform == 'win32' else 'GestionEmpresa')
    if os.path.exists(binary):
        size_kb = os.path.getsize(binary) // 1024
        print('Generado: %s (%d KB)' % (binary, size_kb))
    else:
        print('Generado en: %s' % DIST_DIR)

    if os.path.exists(ENTRY):
        os.remove(ENTRY)


if __name__ == '__main__':
    build()
