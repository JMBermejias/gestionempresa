#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Genera el paquete .deb de Medicion Obra (formato ar compatible con dpkg).
# Copyright (C) 2026 JMBernabeu - GPL-3.0-or-later
import gzip
import hashlib
import io
import os
import sys
import tarfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PKG = os.path.join(ROOT, 'packaging')
DEBIAN = os.path.join(PKG, 'DEBIAN')
OUT_DIR = os.path.join(ROOT, 'dist')
OUT_NAME = 'medicion-obra_1.0.0_all.deb'

# (fuente, destino en el paquete, modo, enlazar-a-root)
# Directorios que deben crearse con su propietario y permisos correctos
# antes de desempaquetar los ficheros (imprescindible si no existe /var/www).
DATA_DIRS = [
    ('var/www', 0o755),
    ('var/www/medicion-obra', 0o755),
    ('var/lib/medicion-obra', 0o755),
    ('usr/lib/medicion-obra', 0o755),
    ('usr/share/doc/medicion-obra', 0o755),
    ('usr/share/applications', 0o755),
    ('usr/share/icons/hicolor/512x512/apps', 0o755),
    ('usr/share/icons/hicolor/256x256/apps', 0o755),
    ('usr/share/icons/hicolor/192x192/apps', 0o755),
    ('etc/medicion-obra', 0o755),
]

DATA_FILES = [
    (os.path.join(ROOT, 'mediotec.html'), 'var/www/medicion-obra/mediotec.html', 0o644),
    (os.path.join(ROOT, 'sw.js'), 'var/www/medicion-obra/sw.js', 0o644),
    (os.path.join(ROOT, 'manifest.json'), 'var/www/medicion-obra/manifest.json', 0o644),
    (os.path.join(ROOT, 'icon-192.png'), 'var/www/medicion-obra/icon-192.png', 0o644),
    (os.path.join(ROOT, 'icon-512.png'), 'var/www/medicion-obra/icon-512.png', 0o644),
    (os.path.join(ROOT, 'LICENSE'), 'var/www/medicion-obra/LICENSE', 0o644),
    (os.path.join(ROOT, 'backend', 'auth.py'),
     'usr/lib/medicion-obra/auth.py', 0o644),
    (os.path.join(ROOT, 'backend', 'server.py'),
     'usr/lib/medicion-obra/server.py', 0o755),
    (os.path.join(ROOT, 'backend', 'medicion_server.py'),
     'usr/lib/medicion-obra/medicion_server.py', 0o755),
    (os.path.join(ROOT, 'tools', 'migrate_firebase_to_local.py'),
     'usr/lib/medicion-obra/migrate_firebase_to_local.py', 0o755),
    (os.path.join(PKG, 'lib', 'systemd', 'system', 'medicion-obra.service'),
     'lib/systemd/system/medicion-obra.service', 0o644),
    (os.path.join(PKG, 'usr', 'share', 'applications', 'medicion-obra.desktop'),
     'usr/share/applications/medicion-obra.desktop', 0o644),
    (os.path.join(PKG, 'usr', 'share', 'icons', 'hicolor', '512x512', 'apps', 'medicion-obra.png'),
     'usr/share/icons/hicolor/512x512/apps/medicion-obra.png', 0o644),
    (os.path.join(PKG, 'usr', 'share', 'icons', 'hicolor', '256x256', 'apps', 'medicion-obra.png'),
     'usr/share/icons/hicolor/256x256/apps/medicion-obra.png', 0o644),
    (os.path.join(PKG, 'usr', 'share', 'icons', 'hicolor', '192x192', 'apps', 'medicion-obra.png'),
     'usr/share/icons/hicolor/192x192/apps/medicion-obra.png', 0o644),
    (os.path.join(PKG, 'usr', 'share', 'doc', 'medicion-obra', 'copyright'),
     'usr/share/doc/medicion-obra/copyright', 0o644),
    (os.path.join(ROOT, 'LICENSE'),
     'usr/share/doc/medicion-obra/LICENSE', 0o644),
]

CONTROL_SCRIPTS = ['preinst', 'postinst', 'prerm', 'postrm']
CONTROL_FILES = ['control', 'conffiles', 'md5sums'] + CONTROL_SCRIPTS

MTIME = 0  # reproducible


def file_size_kib(path):
    size = os.path.getsize(path)
    # dpkg interpreta Installed-Size como KiB (1 KiB = 1024), redondeado al alza
    return (size + 1023) // 1024


def control_content():
    installed = sum(file_size_kib(src) for src, _d, _m in DATA_FILES)
    with open(os.path.join(DEBIAN, 'control'), 'r', encoding='utf-8') as f:
        data = f.read()
    if 'Installed-Size' not in data:
        data = 'Installed-Size: %d\n' % installed + data
    return data


def md5sums_content():
    lines = []
    for src, dest, _mode in DATA_FILES:
        with open(src, 'rb') as f:
            digest = hashlib.md5(f.read()).hexdigest()
        lines.append('%s  %s' % (digest, dest))
    return '\n'.join(lines) + '\n'


def make_control_tar():
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode='w:gz', format=tarfile.GNU_FORMAT) as tar:
        add_bytes(tar, 'control', control_content().encode('utf-8'), 0o644)
        add_bytes(tar, 'conffiles', open(os.path.join(DEBIAN, 'conffiles'), 'rb').read(), 0o644)
        add_bytes(tar, 'md5sums', md5sums_content().encode('utf-8'), 0o644)
        for script in CONTROL_SCRIPTS:
            with open(os.path.join(DEBIAN, script), 'rb') as f:
                add_bytes(tar, script, f.read(), 0o755)
    return buf.getvalue()


def make_data_tar():
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode='w:gz', format=tarfile.GNU_FORMAT) as tar:
        for name, mode in DATA_DIRS:
            add_dir(tar, name, mode)
        for src, dest, mode in DATA_FILES:
            if not os.path.exists(src):
                raise SystemExit('Falta el fichero fuente: %s' % src)
            with open(src, 'rb') as f:
                add_bytes(tar, './' + dest, f.read(), mode)
    return buf.getvalue()


def add_bytes(tar, name, data, mode):
    info = tarfile.TarInfo(name)
    info.size = len(data)
    info.mode = mode
    info.uid = 0
    info.gid = 0
    info.mtime = MTIME
    tar.addfile(info, io.BytesIO(data))


def add_dir(tar, name, mode):
    info = tarfile.TarInfo(name + '/')
    info.type = tarfile.DIRTYPE
    info.mode = mode
    info.uid = 0
    info.gid = 0
    info.mtime = MTIME
    tar.addfile(info)


def ar_header(name, size, mode=0o100644):
    def field(value, length):
        s = str(value)[:length]
        return s.ljust(length)

    header = (
        field(name, 16)
        + field(0, 12)
        + field(0, 6)
        + field(0, 6)
        + field(format(mode, 'o'), 8)
        + field(size, 10)
        + '`\n'
    )
    return header.encode('ascii')


def build_ar(members):
    out = b'!<arch>\n'
    for name, data in members:
        out += ar_header(name, len(data))
        out += data
        if len(data) % 2 == 1:
            out += b'\n'
    return out


def verify_deb(path):
    with open(path, 'rb') as f:
        raw = f.read()
    assert raw[:8] == b'!<arch>\n', 'Cabecera ar invalida'
    pos = 8
    names = []
    while pos < len(raw):
        header = raw[pos:pos + 60]
        name = header[0:16].decode('ascii').strip()
        size = int(header[48:58].decode('ascii').strip())
        names.append(name)
        pos += 60
        data = raw[pos:pos + size]
        assert gzip.decompress(data) if name.endswith('.gz') else True
        pos += size
        if size % 2 == 1:
            pos += 1
    expected = ['debian-binary', 'control.tar.gz', 'data.tar.gz']
    assert names[:3] == expected, 'Miembros ar incorrectos: %r' % names
    print('  .deb verificado: ar valido con miembros %s' % names)


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    debian_binary = b'2.0\n'
    print('Generando control.tar.gz ...')
    control_tar = make_control_tar()
    print('Generando data.tar.gz ...')
    data_tar = make_data_tar()
    print('Generando %s ...' % OUT_NAME)
    deb = build_ar([
        ('debian-binary', debian_binary),
        ('control.tar.gz', control_tar),
        ('data.tar.gz', data_tar),
    ])
    out_path = os.path.join(OUT_DIR, OUT_NAME)
    with open(out_path, 'wb') as f:
        f.write(deb)
    print('Paquete: %s (%d bytes)' % (out_path, len(deb)))
    verify_deb(out_path)
    return 0


if __name__ == '__main__':
    sys.exit(main())
