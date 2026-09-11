#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Gestion Empresa - Generador de paquete Linux (.deb)
# Copyright (C) 2026 JMBernabeu - GPL-3.0-or-later
#
# Uso (en Linux con Python 3.8+ y dpkg-deb):
#   pip install pyinstaller
#   python tools/build_windows.py   # genera dist/GestionEmpresa
#   python tools/package_deb.py      # genera dist/gestion-empresa.deb
#
import os
import re
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIST_DIR = os.path.join(ROOT, 'dist')
STAGE = os.path.join(ROOT, 'build', 'deb')
BINARY = os.path.join(DIST_DIR, 'GestionEmpresa')
ICON = os.path.join(ROOT, 'icon-512.png')
DEB_NAME = 'gestion-empresa.deb'


def app_version():
    with open(os.path.join(ROOT, 'gestion-empresa.html'), 'r', encoding='utf-8') as f:
        m = re.search(r"APP_VERSION='v?([0-9]+\.[0-9]+\.[0-9]+)'", f.read())
    return m.group(1) if m else '1.0.0'


def main():
    if not os.path.exists(BINARY):
        print('ERROR: no existe %s. Primero ejecuta tools/build_windows.py' % BINARY)
        sys.exit(1)
    if shutil.which('dpkg-deb') is None:
        print('ERROR: no se encontro dpkg-deb')
        sys.exit(1)

    ver = app_version()
    if os.path.exists(STAGE):
        shutil.rmtree(STAGE)

    bin_dir = os.path.join(STAGE, 'usr', 'bin')
    app_dir = os.path.join(STAGE, 'usr', 'share', 'applications')
    icon_dir = os.path.join(STAGE, 'usr', 'share', 'icons', 'hicolor', '512x512', 'apps')
    icon_scalable = os.path.join(STAGE, 'usr', 'share', 'icons', 'hicolor', '256x256', 'apps')
    debian = os.path.join(STAGE, 'DEBIAN')
    for d in (bin_dir, app_dir, icon_dir, icon_scalable, debian):
        os.makedirs(d, exist_ok=True)

    shutil.copy2(BINARY, os.path.join(bin_dir, 'gestion-empresa-bin'))
    os.chmod(os.path.join(bin_dir, 'gestion-empresa-bin'), 0o755)

    # Script lanzador: arranca el servidor en segundo plano y abre el navegador
    launcher = os.path.join(ROOT, 'tools', 'gestion-empresa-launcher.sh')
    shutil.copy2(launcher, os.path.join(bin_dir, 'gestion-empresa'))
    os.chmod(os.path.join(bin_dir, 'gestion-empresa'), 0o755)
    if os.path.exists(ICON):
        shutil.copy2(ICON, os.path.join(icon_dir, 'gestion-empresa.png'))
        shutil.copy2(ICON, os.path.join(icon_scalable, 'gestion-empresa.png'))
    else:
        print('  AVISO: falta icon-512.png, el icono no se incluira')

    with open(os.path.join(app_dir, 'gestion-empresa.desktop'), 'w', encoding='utf-8') as f:
        f.write(
            '[Desktop Entry]\n'
            'Type=Application\n'
            'Version=1.0\n'
            'Name=Gestion Empresa\n'
            'GenericName=Sistema de Gestion de Empresa\n'
            'Comment=Sistema de gestion de empresa (servidor local + navegador)\n'
            'Exec=gestion-empresa\n'
            'Icon=gestion-empresa\n'
            'Terminal=false\n'
            'Categories=Office;\n'
            'Keywords=empresa;gestion;\n'
        )

    control = (
        'Package: gestion-empresa\n'
        'Version: %s\n'
        'Section: utils\n'
        'Priority: optional\n'
        'Architecture: amd64\n'
        'Depends: libc6 (>= 2.17)\n'
        'Maintainer: JMBernabeu <jmbernabeu@users.noreply.github.com>\n'
        'Description: Gestion Empresa - Sistema de gestion de empresa\n'
        ' Aplicacion que sirve en http://127.0.0.1:8081 el sistema de\n'
        ' gestion de empresa (escritorio y movil con la misma autenticacion).\n'
    ) % ver
    with open(os.path.join(debian, 'control'), 'w', encoding='utf-8') as f:
        f.write(control)

    deb = os.path.join(DIST_DIR, DEB_NAME)
    if os.path.exists(deb):
        os.remove(deb)
    result = subprocess.run(['dpkg-deb', '--build', '--root-owner-group', STAGE, deb], cwd=ROOT)
    if result.returncode != 0:
        print('ERROR: dpkg-deb fallo con codigo %d' % result.returncode)
        sys.exit(1)
    size_kb = os.path.getsize(deb) // 1024
    print('Generado: %s (v%s, %d KB)' % (deb, ver, size_kb))


if __name__ == '__main__':
    main()