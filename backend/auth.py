#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Medicion Obra - Autenticacion (compartida desktop + movil)
# Copyright (C) 2026 JMBernabeu - GPL-3.0-or-later
import hashlib
import hmac
import json
import os
import secrets
import time

ITERATIONS = 100000
TOKEN_DAYS = 30


def hash_password(password, salt):
    return hashlib.pbkdf2_hmac(
        'sha256', password.encode('utf-8'), salt.encode('utf-8'),
        ITERATIONS).hex()


def gen_salt():
    return secrets.token_hex(16)


def new_token(secret, user, days=TOKEN_DAYS):
    exp = int(time.time()) + days * 86400
    payload = ('%s\n%d' % (user, exp)).encode('utf-8')
    sig = hmac.new(secret.encode('utf-8'), payload, hashlib.sha256).hexdigest()
    return '%s.%d.%s' % (user, exp, sig)


def check_token(secret, token):
    if not token:
        return None
    parts = token.split('.')
    if len(parts) != 3:
        return None
    user, exp_s, sig = parts
    try:
        exp = int(exp_s)
    except ValueError:
        return None
    payload = ('%s\n%d' % (user, exp)).encode('utf-8')
    expected = hmac.new(secret.encode('utf-8'), payload,
                        hashlib.sha256).hexdigest()
    if not hmac.compare_digest(sig, expected):
        return None
    if exp < time.time():
        return None
    return user


def get_secret(auth_file):
    if os.path.exists(auth_file):
        try:
            with open(auth_file, 'r', encoding='utf-8') as f:
                cfg = json.load(f)
                if isinstance(cfg, dict) and cfg.get('secret'):
                    return cfg['secret']
        except (ValueError, OSError):
            pass
    secret = secrets.token_urlsafe(32)
    try:
        directory = os.path.dirname(auth_file)
        if directory:
            os.makedirs(directory, exist_ok=True)
        with open(auth_file, 'w', encoding='utf-8') as f:
            json.dump({'secret': secret}, f, ensure_ascii=False)
    except OSError:
        pass
    return secret


def load_config(auth_file):
    try:
        with open(auth_file, 'r', encoding='utf-8') as f:
            cfg = json.load(f)
        if isinstance(cfg, dict):
            return cfg
    except (ValueError, OSError):
        pass
    return {}


def save_config(auth_file, cfg):
    try:
        directory = os.path.dirname(auth_file)
        if directory:
            os.makedirs(directory, exist_ok=True)
        with open(auth_file, 'w', encoding='utf-8') as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
    except OSError:
        pass