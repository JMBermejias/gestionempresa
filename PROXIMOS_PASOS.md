# GestionEmpresa - Proximos pasos

Base: clon de medicion-obra (rama main, v55) renombrado.

## Crear proyecto Firebase "GestionEmpresa"

1. En una terminal: `firebase login` (abre navegador, autorizar con la cuenta Google de jmber).
2. `firebase projects:create <id-unico> --display-name GestionEmpresa` (el ID en minusculas; si "gestionempresa" esta ocupado, usa otro como gestionempresa-2026).
3. `firebase use gestionempresa`
4. Activar el proveedor Email/Password: consola > Authentication > Sign-in method > Email/Password > Habilitar.
5. Obtener la web API key: consola > Project settings > General > Web API key (la nueva, NO la de medicion-obra).

## Sustituir la config Firebase (la actual es del proyecto medicion-obra)

- `mediotec.html`: constante `FB_CONFIG` (apiKey/authDomain/databaseURL/projectId/storageBucket/messagingSenderId/appId).
- `backend/server_windows.py` y `backend/server.py`: `FB_API_KEY`.
- Opcional: databaseURL en `sw.js`/buscadores si hay URLs hardcodeadas a `medicion-obra-default-rtdb`.

## Repositorio nuevo

- Remote: `origin` apuntando a `https://github.com/JMBermejias/gestionempresa.git` (usuario GitHub: JMBernabeu).

## Para hacer de esto un proyecto nuevo

- Renombrar la app: titulos "Medicion Obra" en `mediotec.html`, `EXE_NAME`, `APP_VERSION`, `manifest.json`, nombre de paquete en `android-app/`, versiones en CI.

## Aviso de seguridad

Los tokens de GitHub usados en el chat quedaron expuestos (token de medicion-obra y token de gestionempresa): **revocar ambos**.