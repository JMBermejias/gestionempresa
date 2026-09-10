#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Gestion Empresa - Servidor integrado (estaticos + API SQLite + Autenticacion)
# Copyright (C) 2026 JMBernabeu - GPL-3.0-or-later
import json
import os
import re
import sqlite3
import sys
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, unquote

try:
    import auth
except ImportError:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import auth

WEB_DIR = os.environ.get('WEB_DIR', '/var/www/gestion-empresa')
DB_PATH = os.environ.get('DB_PATH', '/var/lib/gestion-empresa/medicion.db')
AUTH_FILE = os.environ.get('AUTH_FILE', '/var/lib/gestion-empresa/auth.json')
HOST = os.environ.get('HOST', '0.0.0.0')
PORT = int(os.environ.get('PORT', '80'))
COLLECTIONS = ['materials', 'mediciones', 'empresas', 'obras', 'zonas', 'subcontratas', 'presupuestos', 'facturas', 'clientes', 'proveedores', 'compras', 'ventas', 'almacen']
FB_API_KEY = 'AIzaSyDl3R6815pBX8fc4bbcvCum4T5usHa737k'
FB_IDP = 'https://identitytoolkit.googleapis.com/v1/accounts:%s?key=' + FB_API_KEY

SCHEMA = (
    'CREATE TABLE IF NOT EXISTS appdata ('
    'collection TEXT PRIMARY KEY,'
    'data TEXT NOT NULL,'
    'updated_at TEXT NOT NULL DEFAULT (datetime(\'now\'))'
    ')'
)

MIME_TYPES = {
    '.html': 'text/html; charset=utf-8',
    '.js': 'application/javascript; charset=utf-8',
    '.css': 'text/css; charset=utf-8',
    '.json': 'application/json; charset=utf-8',
    '.png': 'image/png',
    '.jpg': 'image/jpeg',
    '.ico': 'image/x-icon',
    '.svg': 'image/svg+xml',
    '.woff': 'font/woff',
    '.woff2': 'font/woff2',
    '.txt': 'text/plain; charset=utf-8',
    '.pdf': 'application/pdf',
}


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


def auth_is_configured():
    cfg = auth.load_config(AUTH_FILE)
    return bool(cfg.get('user') and cfg.get('salt') and cfg.get('hash'))


def verify_login(user, password):
    cfg = auth.load_config(AUTH_FILE)
    if not cfg.get('user') or not cfg.get('salt') or not cfg.get('hash'):
        return None
    if user != cfg.get('user'):
        return None
    expected = cfg['hash']
    actual = auth.hash_password(password, cfg['salt'])
    import hmac as _hmac
    if not _hmac.compare_digest(expected, actual):
        return None
    return auth.new_token(cfg.get('secret', ''), user)


def fba_email(user):
    norm = re.sub(r'[^a-z0-9._-]', '', str(user).strip().lower())
    return norm + '@gestionempresa.local'


def firebase_idp(action, payload):
    url = FB_IDP % action
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode('utf-8'),
        headers={'Content-Type': 'application/json'},
        method='POST')
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode('utf-8')), resp.status
    except urllib.error.HTTPError as e:
        try:
            return json.loads(e.read().decode('utf-8')), e.code
        except Exception:
            return {}, e.code
    except Exception:
        return {}, 0


def firebase_sign_in(user, password):
    data, status = firebase_idp('signInWithPassword', {
        'email': fba_email(user),
        'password': password,
        'returnSecureToken': True,
    })
    if status == 200 and data.get('registered'):
        return True
    return data.get('error', {}).get('message') if status != 200 else None


def firebase_create_user(user, password):
    data, status = firebase_idp('signUp', {
        'email': fba_email(user),
        'password': password,
        'returnSecureToken': True,
    })
    if status == 200 and data.get('localId'):
        return True
    msg = data.get('error', {}).get('message', '')
    return None if status == 200 or 'EMAIL_EXISTS' in msg else msg


def login_any(user, password):
    token = verify_login(user, password)
    if token:
        warning = firebase_create_user(user, password)
        return token, (warning if isinstance(warning, str) else None)
    fberr = firebase_sign_in(user, password)
    if fberr is True:
        return auth.new_token(auth.get_secret(AUTH_FILE), user), None
    return None, fberr


def check_request_token(handler):
    token = None
    auth_header = handler.headers.get('Authorization', '')
    if auth_header.lower().startswith('bearer '):
        token = auth_header[7:].strip()
    if token:
        secret = auth.get_secret(AUTH_FILE)
        return auth.check_token(secret, token)
    return None


class Handler(BaseHTTPRequestHandler):

    def _send_json(self, code, body):
        data = body if isinstance(body, bytes) else json.dumps(
            body, ensure_ascii=False).encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.end_headers()
        self.wfile.write(data)

    def _send_file(self, filepath):
        ext = os.path.splitext(filepath)[1].lower()
        mime = MIME_TYPES.get(ext, 'application/octet-stream')
        try:
            with open(filepath, 'rb') as f:
                content = f.read()
            self.send_response(200)
            self.send_header('Content-Type', mime)
            self.send_header('Content-Length', str(len(content)))
            if ext == '.html' or filepath.endswith('sw.js'):
                self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
            else:
                self.send_header('Cache-Control', 'public, max-age=3600')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(content)
        except FileNotFoundError:
            self._serve_index()

    def _serve_index(self):
        index = os.path.join(WEB_DIR, 'gestion-empresa.html')
        self._send_file(index)

    def _read_json(self):
        length = int(self.headers.get('Content-Length', 0))
        if length <= 0:
            return {}
        return json.loads(self.rfile.read(length).decode('utf-8'))

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.send_header('Access-Control-Max-Age', '86400')
        self.end_headers()

    def do_GET(self):
        path = urlparse(self.path).path
        if path.startswith('/api/'):
            if path == '/api/auth/status':
                self._send_json(200, {
                    'configured': auth_is_configured(),
                    'version': self._get_version(),
                })
                return
            authed = check_request_token(self)
            if path == '/api/health':
                self._send_json(200, {
                    'ok': True,
                    'db': DB_PATH,
                    'version': self._get_version(),
                    'configured': auth_is_configured(),
                })
                return
            if path.startswith('/api/data'):
                if not authed:
                    self._send_json(401, {'error': 'Autenticacion requerida'})
                    return
                try:
                    data = load_data()
                    self._send_json(200, {c: data.get(c, []) for c in COLLECTIONS})
                except Exception as e:
                    self._send_json(500, {'error': str(e)})
                return
            self._send_json(404, {'error': 'not found'})
            return
        filepath = os.path.join(WEB_DIR, path.lstrip('/'))
        if os.path.isfile(filepath):
            self._send_file(filepath)
        else:
            self._serve_index()

    def do_POST(self):
        path = urlparse(self.path).path
        if not path.startswith('/api/'):
            self._serve_index()
            return
        post_data = self._read_json()
        if path == '/api/auth/setup':
            if auth_is_configured():
                self._send_json(400, {'error': 'Ya configurado'})
                return
            user = (post_data.get('user') or '').strip()
            password = post_data.get('password') or ''
            confirm = post_data.get('confirm') or ''
            if len(user) < 3:
                self._send_json(400, {'error': 'El usuario debe tener al menos 3 caracteres'})
                return
            if len(password) < 4:
                self._send_json(400, {'error': 'La contrasena debe tener al menos 4 caracteres'})
                return
            if password != confirm:
                self._send_json(400, {'error': 'Las contrasenas no coinciden'})
                return
            secret = auth.get_secret(AUTH_FILE)
            cfg = auth.load_config(AUTH_FILE)
            cfg['user'] = user
            cfg['salt'] = auth.gen_salt()
            cfg['hash'] = auth.hash_password(password, cfg['salt'])
            cfg['secret'] = secret
            auth.save_config(AUTH_FILE, cfg)
            fberr = firebase_create_user(user, password)
            if fberr and isinstance(fberr, str):
                cfg['fb_error'] = fberr
                auth.save_config(AUTH_FILE, cfg)
            token = auth.new_token(secret, user)
            resp = {'ok': True, 'token': token, 'user': user, 'fb_in_sync': not isinstance(fberr, str)}
            if isinstance(fberr, str):
                resp['fb_warning'] = fberr
            self._send_json(200, resp)
            return
        if path == '/api/auth/login':
            user = (post_data.get('user') or '').strip()
            password = post_data.get('password') or ''
            token, fberr = login_any(user, password)
            if token:
                resp = {'ok': True, 'token': token, 'user': user, 'fb_in_sync': fberr is None}
                if fberr:
                    resp['fb_warning'] = fberr
                self._send_json(200, resp)
            else:
                self._send_json(401, {'error': 'Usuario o contrasena incorrectos'})
            return
        authed = check_request_token(self)
        if path.startswith('/api/data'):
            if not authed:
                self._send_json(401, {'error': 'Autenticacion requerida'})
                return
            try:
                save_data(post_data)
                self._send_json(200, {'ok': True})
            except Exception as e:
                self._send_json(500, {'error': str(e)})
            return
        self._send_json(404, {'error': 'not found'})

    def _get_version(self):
        import re
        try:
            html = os.path.join(WEB_DIR, 'gestion-empresa.html')
            with open(html, 'r', encoding='utf-8') as f:
                m = re.search(r"APP_VERSION='([^']+)'", f.read())
                if m:
                    return m.group(1).lstrip('v')
        except OSError:
            pass
        return '0.0.0'

    def log_message(self, fmt, *args):
        sys.stderr.write('%s - %s\n' % (self.address_string(), fmt % args))


def main():
    try:
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    except OSError:
        pass
    auth_dir = os.path.dirname(AUTH_FILE)
    if auth_dir:
        try:
            os.makedirs(auth_dir, exist_ok=True)
        except OSError:
            pass
    auth.get_secret(AUTH_FILE)
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    sys.stderr.write(
        'Gestion Empresa en http://%s:%d (web: %s, db: %s)\n'
        % (HOST, PORT, WEB_DIR, DB_PATH))
    if not auth_is_configured():
        sys.stderr.write('PRIMER ACCESO: abre http://%s:%d y crea tu usuario.\n' % (HOST, PORT))
    server.serve_forever()


if __name__ == '__main__':
    main()
