#!/usr/bin/env bash
set -euo pipefail

readonly SERVICE_NAME="onevex-whisper-ydotoold.service"
readonly USER_SYSTEMD_DIR="${XDG_CONFIG_HOME:-${HOME}/.config}/systemd/user"
readonly SERVICE_PATH="${USER_SYSTEMD_DIR}/${SERVICE_NAME}"
readonly SOCKET_PATH="%t/.ydotool_socket"

if ! command -v ydotoold >/dev/null 2>&1; then
    printf 'Missing ydotoold. Install it with: sudo dnf install ydotool\n' >&2
    exit 1
fi

mkdir -p "${USER_SYSTEMD_DIR}"

cat >"${SERVICE_PATH}" <<SERVICE
[Unit]
Description=OneVex Whisper ydotool daemon
Documentation=man:ydotoold(8)

[Service]
ExecStart=$(command -v ydotoold) --socket-path=${SOCKET_PATH} --socket-perm=0600
Restart=on-failure

[Install]
WantedBy=default.target
SERVICE

systemctl --user daemon-reload
systemctl --user enable --now "${SERVICE_NAME}"

if ! systemctl --user is-active --quiet "${SERVICE_NAME}"; then
    printf 'Failed to start %s. Check logs with:\n' "${SERVICE_NAME}" >&2
    printf '  journalctl --user -u %s --no-pager\n' "${SERVICE_NAME}" >&2
    printf '\n' >&2
    printf 'ydotoold usually needs access to /dev/uinput. If permission is denied, configure uinput access for your user or run ydotoold as a system service.\n' >&2
    exit 1
fi

printf 'Started %s.\n' "${SERVICE_NAME}"
printf 'Socket: /run/user/%s/.ydotool_socket\n' "$(id -u)"
