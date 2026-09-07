#!/bin/sh
# Medicion Obra - Lanzador Linux
# Copyright (C) 2026 JMBernabeu - GPL-3.0-or-later
# Arranca el servidor Medicion Obra en segundo plano y abre el navegador.
set -e

PORT="${MEDICION_PORT:-8080}"
URL="http://127.0.0.1:${PORT}"

is_up() {
    # Comprueba si el servidor responde usando /dev/tcp (sin herramientas externas).
    if (exec 3<>"/dev/tcp/127.0.0.1/${PORT}") 2>/dev/null; then
        exec 3>&- 3<&- 2>/dev/null || true
        return 0
    fi
    return 1
}

# Si el servidor ya esta corriendo, solo abrir el navegador.
if is_up; then
    xdg-open "${URL}" >/dev/null 2>&1 || true
    exit 0
fi

# Arrancar el servidor en segundo plano (el wrapper abre el navegador).
MEDICION_NO_BROWSER=1 nohup /usr/bin/medicion-obra-bin >/dev/null 2>&1 &
PID=$!

# Esperar a que el servidor este listo (max 15s).
i=0
while [ $i -lt 15 ]; do
    if is_up; then
        break
    fi
    if ! kill -0 "$PID" 2>/dev/null && ! is_up; then
        break
    fi
    sleep 1
    i=$((i + 1))
done

# Abrir el navegador.
xdg-open "${URL}" >/dev/null 2>&1 || true

exit 0
