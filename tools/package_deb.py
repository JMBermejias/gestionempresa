#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Medicion Obra - Generador de paquete Linux (.deb)
# Copyright (C) 2026 JMBernabeu - GPL-3.0-or-later
#
# Uso (en Linux con Python 3.8+ y dpkg-deb):
#   pip install pyinstaller
#   python tools/build_windows.py   # genera dist/MedicionObra
#   python tools/package_deb.py      # genera dist/medicion-obra.deb
#
import os
import re
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIST_DIR = os.path.join(ROOT, 'dist')
STAGE = os.path.join(ROOT, 'build', 'deb')
BINARY = os.path.join(DIST_DIR, 'MedicionObra')
ICON = os.path.join(ROOT, 'icon-512.png')
DEB_NAME = 'medicion-obra.deb'


def app_version():
    with open(os.path.join(ROOT, 'mediotec.html'), 'r', encoding='utf-8') as f:
        m = re.search(r"APP_VERSION='(\d+)'", f.read())
    return m.group(1) if m else '1'


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

    shutil.copy2(BINARY, os.path.join(bin_dir, 'medicion-obra'))
    if os.path.exists(ICON):
        shutil.copy2(ICON, os.path.join(icon_dir, 'medicion-obra.png'))
        shutil.copy2(ICON, os.path.join(icon_scalable, 'medicion-obra.png'))
    else:
        print('  AVISO: falta icon-512.png, el icono no se incluira')

    with open(os.path.join(app_dir, 'medicion-obra.desktop'), 'w', encoding='utf-8') as f:
        f.write(
            '[Desktop Entry]\n'
            'Type=Application\n'
            'Version=1.0\n'
            'Name=Medicion Obra\n'
            'GenericName=Sistema de Medicion de Obra\n'
            'Comment=Sistema de medicion de obra (servidor local + navegador)\n'
            'Exec=medicion-obra\n'
            'Icon=medicion-obra\n'
            'Terminal=false\n'
            'Categories=Office;\n'
            'Keywords=obra;medicion;\n'
        )

    control = (
        'Package: medicion-obra\n'
        'Version: %s\n'
        'Section: utils\n'
        'Priority: optional\n'
        'Architecture: amd64\n'
        'Depends: libc6 (>= 2.17)\n'
        'Maintainer: JMBernabeu <jmbernabeu@users.noreply.github.com>\n'
        'Description: Medicion Obra - Sistema de medicion de obras\n'
        ' Aplicacion que sirve en http://127.0.0.1:8080 el sistema de\n'
        ' medicion de obras (escritorio y movil con la misma autenticacion).\n'
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