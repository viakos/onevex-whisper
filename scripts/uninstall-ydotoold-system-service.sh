#!/usr/bin/env bash
set -euo pipefail

readonly SERVICE_NAME="onevex-whisper-ydotoold.service"
readonly SERVICE_PATH="/etc/systemd/system/${SERVICE_NAME}"

if systemctl list-unit-files "${SERVICE_NAME}" >/dev/null 2>&1; then
    sudo systemctl disable --now "${SERVICE_NAME}" >/dev/null 2>&1 || true
fi

if [ -f "${SERVICE_PATH}" ]; then
    sudo rm "${SERVICE_PATH}"
    sudo systemctl daemon-reload
    printf 'Removed %s.\n' "${SERVICE_PATH}"
else
    printf 'System service file is not installed: %s\n' "${SERVICE_PATH}"
fi
