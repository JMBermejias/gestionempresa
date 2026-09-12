#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Gestion Empresa - API local (SQLite)
# Copyright (C) 2026 JMBernabeu
# License: GNU General Public License v3.0 or later (see LICENSE)
import json
import os
import sqlite3
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

DB_PATH = os.environ.get('MEDICION_DB', '/var/lib/gestion-empresa/medicion.db')
HOST = os.environ.get('MEDICION_HOST', '127.0.0.1')
PORT = int(os.environ.get('MEDICION_PORT', '8000'))
COLLECTIONS = ['materials', 'mediciones', 'empresas', 'obras', 'zonas', 'subcontratas', 'presupuestos', 'facturas', 'clientes', 'proveedores', 'empleados', 'compras', 'ventas', 'almacen', 'partes', 'categorias', 'almacenes']

SCHEMA = (
    'CREATE TABLE IF NOT EXISTS appdata ('
    'collection TEXT PRIMARY KEY,'
    'data TEXT NOT NULL,'
    'updated_at TEXT NOT NULL DEFAULT (datetime(\'now\'))'
    ')'
)


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute(SCHEMA)
    conn.commit()
    return conn


def load_data():
    conn = get_conn()
    rows = conn.execute('SELECT collection, data FROM appdata').fetchall()
    conn.close()
    data = {}
    for r in rows:
        try:
            data[r['collection']] = json.loads(r['data'])
        except (ValueError, TypeError):
            data[r['collection']] = []
    return data


def save_data(payload):
    conn = get_conn()
    try:
        for c in COLLECTIONS:
            if c in payload:
                value = json.dumps(payload[c], ensure_ascii=False)
                conn.execute(
                    'INSERT INTO appdata (collection, data) VALUES (?, ?) '
                    'ON CONFLICT(collection) DO UPDATE SET '
                    'data=excluded.data, updated_at=datetime(\'now\')',
                    (c, value),
                )
        conn.commit()
    finally:
        conn.close()


class Handler(BaseHTTPRequestHandler):

    def _send(self, code, body):
        data = body if isinstance(body, bytes) else json.dumps(
            body, ensure_ascii=False).encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(data)

    def _read_json(self):
        length = int(self.headers.get('Content-Length', 0))
        if length <= 0:
            return {}
        return json.loads(self.rfile.read(length).decode('utf-8'))

    def do_GET(self):
        if self.path.startswith('/api/data'):
            try:
                data = load_data()
                self._send(200, {c: data.get(c, []) for c in COLLECTIONS})
            except Exception as e:  # noqa: BLE001
                self._send(500, {'error': str(e)})
        elif self.path.startswith('/api/health'):
            self._send(200, {'ok': True, 'db': DB_PATH})
        else:
            self._send(404, {'error': 'not found'})

    def do_POST(self):
        if self.path.startswith('/api/data'):
            try:
                payload = self._read_json()
                save_data(payload)
                self._send(200, {'ok': True})
            except Exception as e:  # noqa: BLE001
                self._send(500, {'error': str(e)})
        else:
            self._send(404, {'error': 'not found'})

    def log_message(self, fmt, *args):
        sys.stderr.write('%s - %s\n' % (self.address_string(), fmt % args))


def main():
    try:
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    except OSError:
        pass
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    sys.stderr.write(
        'Gestion Empresa API en http://%s:%d (db: %s)\n' % (HOST, PORT, DB_PATH))
    server.serve_forever()


if __name__ == '__main__':
    main()
