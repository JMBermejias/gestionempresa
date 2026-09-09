# GestionEmpresa - Estado y proximos pasos

## Estado actual

- Repo remoto: `https://github.com/JMBermejias/gestionempresa.git` (usuario GitHub: JMBernabeu).
- Rama `main` subida (commit `62eef43`, incluye merge con el README inicial del repo).
- Identidad git local configurada: `jmbernabeu <jmbernabeu@users.noreply.github.com>`.
- Clon base: proyecto medicion-obra (rama main, v55). Firebase CLI instalada global (v15.x).

## Proyecto Firebase "GestionEmpresa" (CREADO)

- Proyecto: `gestionempresa-2026` (display name: GestionEmpresa).
- Web app creada con la config SDK.
- Console: https://console.firebase.google.com/project/gestionempresa-2026/overview

### Seguir estos pasos en la consola (manual, no CLI)

1. Habilitar el proveedor **Email/Password**: Authentication > Sign-in method > Email/Password > Habilitar.
2. **Crear la Realtime Database**: Build > Realtime Database > Create database (elegir region, p.ej. europe-west1).
   - Anotar la `databaseURL` que resulte y actualizarla en `mediotec.html` (constante `FB_CONFIG`) si difiere de la URL base actual.

## Config Firebase (YA SUSTITUIDA, del proyecto gestionempresa-2026)

La config actual pertenece al proyecto nuevo `gestionempresa-2026`, sustituida en:
- `mediotec.html`: constante `FB_CONFIG` (apiKey/authDomain/databaseURL/projectId/storageBucket/messagingSenderId/appId).
- `backend/server_windows.py` y `backend/server.py`: `FB_API_KEY`.

Nota: la URL de RTDB en `FB_CONFIG` es la base generica (`gestionempresa-2026-default-rtdb.firebaseio.com`); ajustar segun la region elegida al crear la DB.

## Renombrado de la app (HECHO)

La aplicacion se ha renombrado de "Medicion Obra" a **"Gestion Empresa"** y el
versionado a **semver v1.0.0**. Afecta a:
- `mediotec.html`: titulos, `FB_CONFIG`, `APP_VERSION='v1.0.0'`.
- `manifest.json`, `sw.js` (caché `gestion-empresa-v1.0.0`).
- `backend/*`: comentarios, rutas (`/var/www/gestion-empresa`, `/var/lib/gestion-empresa`), `FB_API_KEY`, versionado semver en auto-update.
- `tools/*`: generadores (exe `GestionEmpresa.exe`, deb `gestion-empresa.deb`, launcher), migracion (la URL de Firebase origen se mantiene apuntando a `medicion-obra`).
- `packaging/*`: paquete `gestion-empresa`, systemd, nginx, desktop, icons, control.
- `android-app/`: `appName` "Gestion Empresa", `appId` `com.gestionempresa.app`.
- `.github/workflows/build-windows.yml`: versionado semver y nombres de artefactos.
- `tools/migrate_firebase_to_local.py`: ruta local `gestion-empresa` (URL origen de Firebase sigue siendo la de `medicion-obra`).

Pendiente de verificar: que `.github/workflows/build-windows.yml` publique releases en este repo nuevo con tags `v1.0.x`.

## Aviso de seguridad

Los tokens de GitHub usados en el chat quedaron expuestos (token de medicion-obra y token de gestionempresa): **revocar ambos**.