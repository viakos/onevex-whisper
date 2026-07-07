#!/usr/bin/env bash
set -euo pipefail

readonly SERVICE_NAME="onevex-whisper-ydotoold.service"
readonly SERVICE_PATH="/etc/systemd/system/${SERVICE_NAME}"
readonly SOCKET_PATH="/run/onevex-whisper/ydotool_socket"
readonly USER_SERVICE_NAME="onevex-whisper-ydotoold.service"
readonly USER_SERVICE_PATH="${XDG_CONFIG_HOME:-${HOME}/.config}/systemd/user/${USER_SERVICE_NAME}"

if ! command -v ydotoold >/dev/null 2>&1; then
    printf 'Missing ydotoold. Install it with: sudo dnf install ydotool\n' >&2
    exit 1
fi

if systemctl --user list-unit-files "${USER_SERVICE_NAME}" >/dev/null 2>&1; then
    systemctl --user disable --now "${USER_SERVICE_NAME}" >/dev/null 2>&1 || true
fi

if [ -f "${USER_SERVICE_PATH}" ]; then
    rm "${USER_SERVICE_PATH}"
    systemctl --user daemon-reload
fi

service_content="[Unit]
Description=OneVex Whisper ydotool daemon
Documentation=man:ydotoold(8)

[Service]
Type=simple
RuntimeDirectory=onevex-whisper
RuntimeDirectoryMode=0755
ExecStart=$(command -v ydotoold) --socket-path=${SOCKET_PATH} --socket-perm=0600 --socket-own=$(id -u):$(id -g)
Restart=on-failure

[Install]
WantedBy=multi-user.target
"

printf '%s' "${service_content}" | sudo tee "${SERVICE_PATH}" >/dev/null
sudo systemctl daemon-reload
sudo systemctl enable --now "${SERVICE_NAME}"

if ! systemctl is-active --quiet "${SERVICE_NAME}"; then
    printf 'Failed to start %s. Check logs with:\n' "${SERVICE_NAME}" >&2
    printf '  sudo journalctl -u %s --no-pager\n' "${SERVICE_NAME}" >&2
    exit 1
fi

printf 'Started %s.\n' "${SERVICE_NAME}"
printf 'Socket: %s\n' "${SOCKET_PATH}"
