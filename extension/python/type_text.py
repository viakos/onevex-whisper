#!/usr/bin/env python3
from __future__ import annotations

import argparse
import logging
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path


DEFAULT_TEXT = "This is my text"
DEFAULT_DELAY_SECONDS = 0.65
DEFAULT_KEY_DELAY_MS = 12
YDOTOOL_SOCKET = "/run/onevex-whisper/ydotool_socket"
LOG_FILE = Path.home() / ".local" / "state" / "onevex-whisper" / "text-injector.log"

# Linux input-event key codes for modifier keys and Space. Releasing them before
# typing prevents the trigger shortcut from turning text into Ctrl-based actions.
KEY_UP_EVENTS = [
    "29:0",   # KEY_LEFTCTRL
    "97:0",   # KEY_RIGHTCTRL
    "42:0",   # KEY_LEFTSHIFT
    "54:0",   # KEY_RIGHTSHIFT
    "56:0",   # KEY_LEFTALT
    "100:0",  # KEY_RIGHTALT
    "125:0",  # KEY_LEFTMETA
    "126:0",  # KEY_RIGHTMETA
    "57:0",   # KEY_SPACE
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Type text into the currently focused application on Wayland."
    )
    parser.add_argument("--text", default=DEFAULT_TEXT, help="Text to type.")
    parser.add_argument(
        "--delay-seconds",
        type=float,
        default=DEFAULT_DELAY_SECONDS,
        help="Delay before typing so the hotkey modifiers can be released.",
    )
    parser.add_argument(
        "--key-delay-ms",
        type=int,
        default=DEFAULT_KEY_DELAY_MS,
        help="Delay between generated key events passed to ydotool.",
    )
    return parser.parse_args()


def configure_logging() -> None:
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        filename=LOG_FILE,
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )


def run_ydotool(args: list[str]) -> None:
    ydotool_path = shutil.which("ydotool")
    if not ydotool_path:
        raise RuntimeError("ydotool is not installed or is not available in PATH")

    env = {**os.environ, "YDOTOOL_SOCKET": YDOTOOL_SOCKET}

    result = subprocess.run(
        [ydotool_path, *args],
        check=False,
        capture_output=True,
        env=env,
        text=True,
    )

    if result.returncode != 0:
        output = (result.stderr or result.stdout).strip()
        message = f"ydotool failed with exit code {result.returncode}"
        if output:
            message = f"{message}: {output}"
        raise RuntimeError(message)


def type_text(text: str, key_delay_ms: int) -> None:
    run_ydotool(["key", *KEY_UP_EVENTS])
    run_ydotool(["type", "--key-delay", str(key_delay_ms), "--", text])


def main() -> int:
    args = parse_args()
    configure_logging()

    if args.delay_seconds > 0:
        time.sleep(args.delay_seconds)

    try:
        type_text(args.text, args.key_delay_ms)
    except Exception:
        logging.exception("Failed to type text")
        return 1

    logging.info("Typed %d characters", len(args.text))
    return 0


if __name__ == "__main__":
    sys.exit(main())
