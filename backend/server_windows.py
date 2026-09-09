#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Medicion Obra - Servidor Windows (.exe)
# Autenticacion + Actualizaciones automaticas desde GitHub Releases
# Copyright (C) 2026 JMBernabeu - GPL-3.0-or-later
import base64
import hashlib
import hmac
import json
import os
import re
import sqlite3
import sys
import threading
import time
import urllib.error
import urllib.request
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

import auth

if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
    ASSETS_DIR = os.path.join(sys._MEIPASS, 'assets')
else:
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ASSETS_DIR = os.path.join(BASE_DIR)

WEB_DIR = ASSETS_DIR


def appdata_dir():
    if sys.platform.startswith('linux'):
        home = os.path.expanduser('~')
        if os.path.isdir(home):
            xdg = os.environ.get('XDG_DATA_HOME') or os.path.join(home, '.local', 'share')
            return os.path.join(xdg, 'MedicionObra')
    return os.path.join(os.environ.get('APPDATA', BASE_DIR), 'MedicionObra')


APPDATA = appdata_dir()
DB_PATH = os.path.join(APPDATA, 'medicion.db')
AUTH_FILE = os.path.join(APPDATA, 'auth.json')
UPDATES_DIR = os.path.join(APPDATA, 'updates')
HOST = '0.0.0.0'
PORT = 8080
GITHUB_REPO = 'JMBermejias/medicion-obra'
GITHUB_API = 'https://api.github.com/repos/%s/releases/latest' % GITHUB_REPO
if sys.platform.startswith('linux'):
    EXE_NAME = 'medicion-obra.deb'
else:
    EXE_NAME = 'MedicionObra.exe'
COLLECTIONS = ['materials', 'mediciones', 'empresas', 'obras', 'zonas', 'subcontratas']
FB_API_KEY = 'AIzaSyC5ykdqo7sP1of01Lm3wFYf6SuJdvbB62Y'
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


def get_app_version():
    try:
        html = os.path.join(WEB_DIR, 'mediotec.html')
        with open(html, 'r', encoding='utf-8') as f:
            m = re.search(r"APP_VERSION='(\d+)'", f.read())
            if m:
                return m.group(1)
    except OSError:
        pass
    return '0'


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
    if not hmac.compare_digest(expected, actual):
        return None
    return auth.new_token(cfg.get('secret', ''), user)


def fba_email(user):
    norm = re.sub(r'[^a-z0-9._-]', '', str(user).strip().lower())
    return norm + '@medicionobra.local'


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


def check_request_token(handler, param=None):
    token = None
    auth_header = handler.headers.get('Authorization', '')
    if auth_header.lower().startswith('bearer '):
        token = auth_header[7:].strip()
    if param and handler.path:
        qs = urlparse(handler.path).query
        for pair in qs.split('&'):
            if pair.startswith('token='):
                token = urllib.parse.unquote(pair[6:])
    if not token:
        return None
    secret = auth.get_secret(AUTH_FILE)
    return auth.check_token(secret, token)


def fetch_github_release():
    req = urllib.request.Request(
        GITHUB_API, headers={'User-Agent': 'MedicionObra', 'Accept': 'application/vnd.github+json'})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode('utf-8'))


def _norm_version(v):
    m = re.search(r'(\d+)', v or '')
    return int(m.group(1)) if m else 0


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
            self.end_headers()
            self.wfile.write(content)
        except FileNotFoundError:
            self._serve_index()

    def _serve_index(self):
        index = os.path.join(WEB_DIR, 'mediotec.html')
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

    def _require_auth(self):
        return check_request_token(self)

    def _handle_api_auth(self, path, post_data=None):
        if path == '/api/auth/status':
            self._send_json(200, {
                'configured': auth_is_configured(),
                'version': get_app_version(),
            })
            return True
        if path == '/api/auth/login':
            body = post_data if post_data is not None else self._read_json()
            user = (body.get('user') or '').strip()
            password = body.get('password') or ''
            token, fberr = login_any(user, password)
            if token:
                resp = {'ok': True, 'token': token, 'user': user, 'fb_in_sync': fberr is None}
                if fberr:
                    resp['fb_warning'] = fberr
                self._send_json(200, resp)
            else:
                self._send_json(401, {'error': 'Usuario o contrasena incorrectos'})
            return True
        return False

    def _handle_api_update(self, path, authed_user):
        if not path.startswith('/api/update'):
            return False
        if not authed_user:
            self._send_json(401, {'error': 'Autenticacion requerida'})
            return True
        if path == '/api/update/check':
            try:
                rel = fetch_github_release()
                tag = rel.get('tag_name', '')
                latest = _norm_version(tag)
                current = _norm_version(get_app_version())
                assets = rel.get('assets', [])
                exe_url = ''
                for a in assets:
                    if a.get('name') == EXE_NAME:
                        exe_url = a.get('browser_download_url', '')
                        break
                self._send_json(200, {
                    'current': get_app_version(),
                    'latest_tag': tag,
                    'latest_version': str(latest),
                    'needs_update': latest > current,
                    'download_url': exe_url,
                    'published_at': rel.get('published_at', ''),
                    'release_notes': (rel.get('body') or '')[:4000],
                    'name': rel.get('name', ''),
                })
            except Exception as e:
                self._send_json(500, {'error': str(e), 'offline': True})
            return True
        if path == '/api/update/download':
            try:
                rel = fetch_github_release()
                exe_url = ''
                for a in rel.get('assets', []):
                    if a.get('name') == EXE_NAME:
                        exe_url = a.get('browser_download_url', '')
                        break
                if not exe_url:
                    self._send_json(404, {'error': 'No hay EXE en la release'})
                    return True
                os.makedirs(UPDATES_DIR, exist_ok=True)
                dest = os.path.join(UPDATES_DIR, EXE_NAME)
                req = urllib.request.Request(exe_url, headers={'User-Agent': 'MedicionObra'})
                with urllib.request.urlopen(req, timeout=600) as resp, open(dest, 'wb') as f:
                    size = 0
                    while True:
                        chunk = resp.read(65536)
                        if not chunk:
                            break
                        f.write(chunk)
                        size += len(chunk)
                self._send_json(200, {'ok': True, 'size': size})
            except Exception as e:
                self._send_json(500, {'error': str(e)})
            return True
        if path == '/api/update/apply':
            if not getattr(sys, 'frozen', False):
                self._send_json(200, {'ok': True, 'message': 'Modo desarrollo: nueva version lista. Reinicia manualmente.'})
                return True
            new = os.path.join(UPDATES_DIR, EXE_NAME)
            if not os.path.exists(new):
                self._send_json(400, {'error': 'Primero descarga la actualizacion'})
                return True
            target = os.path.join(BASE_DIR, EXE_NAME)
            if os.path.abspath(new) == os.path.abspath(target):
                self._send_json(200, {'ok': True, 'message': 'La aplicacion ya esta actualizada.'})
                return True
            bat = os.path.join(UPDATES_DIR, 'apply_update.bat')
            script = (
                '@echo off\r\n'
                ':wait\r\n'
                'tasklist /FI "IMAGENAME eq %s" 2>NUL | find /I "%s" >NUL\r\n'
                'if not errorlevel 1 ( timeout /t 2 /nobreak >NUL & goto wait )\r\n'
                'copy /Y "%s" "%s" >NUL\r\n'
                'start "" "%s"\r\n'
                'del /Q "%s"\r\n'
                'exit\r\n'
            ) % (EXE_NAME, EXE_NAME, new, target, target, bat)
            try:
                with open(bat, 'w') as f:
                    f.write(script)
                os.startfile(bat)
            except Exception as e:
                self._send_json(500, {'error': 'No se pudo lanzar el actualizador: %s' % e})
                return True
            threading.Timer(2.0, lambda: os._exit(0)).start()
            self._send_json(200, {
                'ok': True,
                'message': 'Actualizacion aplicada. La aplicacion se cerrara y se volvera a abrir sola con la nueva version.',
            })
            return True
        if path == '/api/update/progress':
            new = os.path.join(UPDATES_DIR, EXE_NAME)
            self._send_json(200, {'downloaded': os.path.exists(new)})
            return True
        return False

    def _handle_api_app(self, path, authed):
        if not path.startswith('/api/app'):
            return False
        if not authed:
            self._send_json(401, {'error': 'Autenticacion requerida'})
            return True
        if path == '/api/app/quit':
            self._send_json(200, {'ok': True, 'message': 'Cerrando la aplicacion...'})
            threading.Timer(1.0, lambda: os._exit(0)).start()
            return True
        return False

    def do_GET(self):
        path = urlparse(self.path).path
        if path.startswith('/api/'):
            if self._handle_api_auth(path):
                return
            authed = self._require_auth()
            if self._handle_api_app(path, authed):
                return
            if self._handle_api_update(path, authed):
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
            if path.startswith('/api/health'):
                self._send_json(200, {
                    'ok': True, 'db': DB_PATH,
                    'version': get_app_version(),
                    'configured': auth_is_configured(),
                })
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
        if path.startswith('/api/'):
            if self._handle_api_auth(path, post_data):
                return
            authed = self._require_auth()
            if self._handle_api_app(path, authed):
                return
            if self._handle_api_update(path, authed):
                return
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
            return
        self._serve_index()

    def log_message(self, fmt, *args):
        pass


def open_browser():
    if os.environ.get('MEDICION_NO_BROWSER') == '1':
        return
    time.sleep(1.0)
    webbrowser.open('http://127.0.0.1:%d' % PORT)


def main():
    os.makedirs(APPDATA, exist_ok=True)
    os.makedirs(UPDATES_DIR, exist_ok=True)
    auth.get_secret(AUTH_FILE)
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    threading.Thread(target=open_browser, daemon=True).start()
    print('===========================================')
    print('  Medicion Obra - Control de Medicion')
    print('  Version app: v%s' % get_app_version())
    print('===========================================')
    print('  Servidor:  http://127.0.0.1:%d' % PORT)
    print('  Base datos: %s' % DB_PATH)
    print('  Web:       %s' % WEB_DIR)
    print('===========================================')
    if not auth_is_configured():
        print('  PRIMER ACCESO: entra a http://127.0.0.1:%d' % PORT)
        print('  y crea tu usuario y contrasena.')
    print('===========================================')
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\nServidor detenido.')
        server.server_close()


if __name__ == '__main__':
    main()