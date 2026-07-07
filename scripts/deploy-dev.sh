#!/usr/bin/env bash
set -euo pipefail

readonly EXTENSION_UUID="onevex-whisper@local"
readonly SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
readonly PROJECT_DIR="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
readonly EXTENSION_DIR="${PROJECT_DIR}/extension"
readonly EXTENSIONS_HOME="${XDG_DATA_HOME:-${HOME}/.local/share}/gnome-shell/extensions"
readonly TARGET_DIR="${EXTENSIONS_HOME}/${EXTENSION_UUID}"

usage() {
    printf 'Usage: %s [install|uninstall|status]\n' "${0##*/}"
    printf '\n'
    printf 'Commands:\n'
    printf '  install    Compile schemas and symlink the extension into GNOME Shell extensions.\n'
    printf '  uninstall  Disable the extension and remove the development symlink.\n'
    printf '  status     Print source and target paths.\n'
}

require_command() {
    if ! command -v "$1" >/dev/null 2>&1; then
        printf 'Missing required command: %s\n' "$1" >&2
        exit 1
    fi
}

compile_schemas() {
    require_command glib-compile-schemas
    glib-compile-schemas "${EXTENSION_DIR}/schemas"
}

install_extension() {
    compile_schemas
    mkdir -p "${EXTENSIONS_HOME}"

    if [ -L "${TARGET_DIR}" ]; then
        local current_target
        current_target="$(readlink -- "${TARGET_DIR}")"

        if [ "${current_target}" != "${EXTENSION_DIR}" ]; then
            printf 'Refusing to replace existing symlink: %s -> %s\n' "${TARGET_DIR}" "${current_target}" >&2
            exit 1
        fi
    elif [ -e "${TARGET_DIR}" ]; then
        printf 'Refusing to replace existing extension directory: %s\n' "${TARGET_DIR}" >&2
        exit 1
    else
        ln -s "${EXTENSION_DIR}" "${TARGET_DIR}"
    fi

    if command -v gnome-extensions >/dev/null 2>&1; then
        gnome-extensions enable "${EXTENSION_UUID}" >/dev/null 2>&1 || true
    fi

    printf 'Installed development symlink:\n  %s -> %s\n' "${TARGET_DIR}" "${EXTENSION_DIR}"
    printf 'If GNOME Shell has not seen this extension before, log out and log back in.\n'
}

uninstall_extension() {
    if command -v gnome-extensions >/dev/null 2>&1; then
        gnome-extensions disable "${EXTENSION_UUID}" >/dev/null 2>&1 || true
    fi

    if [ -L "${TARGET_DIR}" ] && [ "$(readlink -- "${TARGET_DIR}")" = "${EXTENSION_DIR}" ]; then
        rm "${TARGET_DIR}"
        printf 'Removed development symlink: %s\n' "${TARGET_DIR}"
    elif [ -e "${TARGET_DIR}" ]; then
        printf 'Not removing non-development target: %s\n' "${TARGET_DIR}" >&2
        exit 1
    else
        printf 'Extension is not installed as a development symlink.\n'
    fi
}

print_status() {
    printf 'Extension UUID: %s\n' "${EXTENSION_UUID}"
    printf 'Source:         %s\n' "${EXTENSION_DIR}"
    printf 'Target:         %s\n' "${TARGET_DIR}"
}

case "${1:-install}" in
    install)
        install_extension
        ;;
    uninstall)
        uninstall_extension
        ;;
    status)
        print_status
        ;;
    -h|--help|help)
        usage
        ;;
    *)
        usage >&2
        exit 1
        ;;
esac
