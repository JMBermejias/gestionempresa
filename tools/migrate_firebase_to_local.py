#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Migra los datos de Firebase Realtime Database a la base SQLite local.
# Copyright (C) 2026 JMBernabeu - GPL-3.0-or-later
import argparse
import json
import os
import sqlite3
import sys
import urllib.request

DEFAULT_URL = ('https://medicion-obra-default-rtdb.europe-west1.'
               'firebasedatabase.app/appdata.json')
DEFAULT_DB = '/var/lib/gestion-empresa/medicion.db'
COLLECTIONS = ['materials', 'mediciones', 'empresas', 'obras', 'zonas', 'subcontratas']

SCHEMA = (
    'CREATE TABLE IF NOT EXISTS appdata ('
    'collection TEXT PRIMARY KEY,'
    'data TEXT NOT NULL,'
    'updated_at TEXT NOT NULL DEFAULT (datetime(\'now\'))'
    ')'
)


def fetch_firebase(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'gestion-empresa-migrate'})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode('utf-8'))


def ensure_series(mediciones):
    max_serie = 0
    for m in mediciones:
        if isinstance(m.get('serie'), int) and m['serie'] > max_serie:
            max_serie = m['serie']
    counter = max_serie
    for m in mediciones:
        if not isinstance(m.get('serie'), int):
            counter += 1
            m['serie'] = counter
    return mediciones


def read_db(db_path):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute(SCHEMA)
    rows = conn.execute('SELECT collection, data FROM appdata').fetchall()
    conn.close()
    return {r['collection']: json.loads(r['data']) for r in rows}


def write_db(db_path, payload):
    conn = sqlite3.connect(db_path)
    conn.execute(SCHEMA)
    try:
        for c in COLLECTIONS:
            if c in payload:
                value = json.dumps(payload[c], ensure_ascii=False)
                conn.execute(
                    'INSERT INTO appdata (collection, data) VALUES (?, ?) '
                    'ON CONFLICT(collection) DO UPDATE SET '
                    'data=excluded.data, updated_at=datetime(\'now\')',
                    (c, value))
        conn.commit()
    finally:
        conn.close()


def merge_by_id(existing, incoming):
    by_id = {}
    for item in existing:
        if isinstance(item, dict) and item.get('id'):
            by_id[item['id']] = item
    for item in incoming:
        if isinstance(item, dict) and item.get('id'):
            by_id[item['id']] = item
    return list(by_id.values())


def main():
    ap = argparse.ArgumentParser(
        description='Migra los datos de Firebase Realtime Database a la '
                    'base SQLite local de Gestion Empresa.')
    ap.add_argument('--url', default=DEFAULT_URL,
                    help='URL del nodo appdata en Firebase (por defecto: '
                         '%(default)s)')
    ap.add_argument('--db', default=DEFAULT_DB,
                    help='Ruta a la base SQLite local (por defecto: '
                         '%(default)s)')
    ap.add_argument('--output', default=None,
                    help='Guardar una copia del JSON exportado en esta ruta')
    ap.add_argument('--merge', action='store_true',
                    help='Fusionar con los datos locales existentes (por id) '
                         'en lugar de sobrescribirlos')
    ap.add_argument('--dry-run', action='store_true',
                    help='Solo mostrar el resumen, sin escribir nada')
    args = ap.parse_args()

    print('Leyendo datos desde Firebase:')
    print('  ', args.url)
    remote = fetch_firebase(args.url)
    if not isinstance(remote, dict):
        sys.exit('ERROR: el nodo Firebase no devolvio un objeto JSON valido')

    data = {c: remote.get(c) or [] for c in COLLECTIONS}
    data['mediciones'] = ensure_series(data['mediciones'])
    for c in COLLECTIONS:
        if not isinstance(data[c], list):
            sys.exit('ERROR: la coleccion %s no es una lista' % c)

    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print('Copia del JSON guardada en:', args.output)

    print('Datos desde Firebase: ' +
          ', '.join('%s=%d' % (c, len(data[c])) for c in COLLECTIONS))

    if args.dry_run:
        print('Modo dry-run: no se escribio nada.')
        return 0

    if args.merge and os.path.exists(args.db):
        local = read_db(args.db)
        for c in COLLECTIONS:
            data[c] = merge_by_id(local.get(c, []), data[c])
        print('Modo merge: fusionados con los datos locales existentes.')

    write_db(args.db, data)
    print('Importados en la base local:', args.db)
    for c in COLLECTIONS:
        print('  %s: %d registros' % (c, len(data[c])))
    return 0


if __name__ == '__main__':
    sys.exit(main())
