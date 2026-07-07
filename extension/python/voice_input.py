#!/usr/bin/env python3
from __future__ import annotations

import argparse
import logging
import os
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

from type_text import type_text


APP_NAME = "onevex-whisper"
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MODEL_PATH = PROJECT_ROOT / "models" / "ggml-small.bin"
STATE_DIR = Path.home() / ".local" / "state" / APP_NAME
LOG_FILE = STATE_DIR / "voice-input.log"
RECORDER_LOG_FILE = STATE_DIR / "recorder.log"
AUDIO_FILE = STATE_DIR / "recording.wav"
PID_FILE = STATE_DIR / "recording.pid"
TRANSCRIPT_BASE = STATE_DIR / "transcript"
TRANSCRIPT_FILE = TRANSCRIPT_BASE.with_suffix(".txt")
STOP_TIMEOUT_SECONDS = 5.0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Record speech, transcribe it with whisper.cpp, and type it."
    )
    parser.add_argument(
        "command",
        choices=["start", "stop-transcribe-type", "cancel"],
        help="Recording lifecycle command.",
    )
    parser.add_argument(
        "--model",
        default=os.environ.get("ONEVEX_WHISPER_MODEL", str(DEFAULT_MODEL_PATH)),
        help="Path to the whisper.cpp ggml model.",
    )
    parser.add_argument(
        "--whisper-cli",
        default=os.environ.get("ONEVEX_WHISPER_CLI"),
        help="Path to whisper.cpp CLI. Defaults to searching common locations.",
    )
    return parser.parse_args()


def configure_logging() -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        filename=LOG_FILE,
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )


def is_process_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def read_recorder_pid() -> int | None:
    try:
        pid = int(PID_FILE.read_text(encoding="utf-8").strip())
    except (FileNotFoundError, ValueError):
        return None

    if is_process_alive(pid):
        return pid

    PID_FILE.unlink(missing_ok=True)
    return None


def remove_previous_outputs() -> None:
    for path in [AUDIO_FILE, TRANSCRIPT_FILE]:
        path.unlink(missing_ok=True)


def start_recording() -> None:
    if read_recorder_pid() is not None:
        logging.info("Recording is already active")
        return

    recorder_path = shutil.which("pw-record")
    if not recorder_path:
        raise RuntimeError("pw-record is not installed or is not available in PATH")

    remove_previous_outputs()

    with RECORDER_LOG_FILE.open("ab") as recorder_log:
        process = subprocess.Popen(
            [
                recorder_path,
                "--rate",
                "16000",
                "--channels",
                "1",
                "--format",
                "s16",
                str(AUDIO_FILE),
            ],
            stdout=recorder_log,
            stderr=recorder_log,
            start_new_session=True,
        )

    PID_FILE.write_text(f"{process.pid}\n", encoding="utf-8")
    logging.info("Started recording with PID %d", process.pid)


def stop_recording() -> bool:
    pid = read_recorder_pid()
    if pid is None:
        logging.info("No active recording to stop")
        return False

    try:
        os.killpg(pid, signal.SIGINT)
    except ProcessLookupError:
        PID_FILE.unlink(missing_ok=True)
        return False

    deadline = time.monotonic() + STOP_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        if not is_process_alive(pid):
            break
        time.sleep(0.05)
    else:
        logging.warning("Recorder did not stop after SIGINT; sending SIGTERM")
        try:
            os.killpg(pid, signal.SIGTERM)
        except ProcessLookupError:
            pass

    PID_FILE.unlink(missing_ok=True)
    logging.info("Stopped recording with PID %d", pid)
    return AUDIO_FILE.exists() and AUDIO_FILE.stat().st_size > 0


def find_whisper_cli(explicit_path: str | None) -> str:
    if explicit_path:
        expanded = Path(explicit_path).expanduser()
        if expanded.is_file():
            return str(expanded)
        raise RuntimeError(f"Configured whisper.cpp CLI does not exist: {expanded}")

    for executable in ["whisper-cli", "whisper-cpp"]:
        path = shutil.which(executable)
        if path:
            return path

    home = Path.home()
    for path in [
        home / "dev" / "whisper.cpp" / "build" / "bin" / "whisper-cli",
        home / "dev" / "whisper.cpp" / "build" / "bin" / "main",
        home / "dev" / "whisper.cpp" / "main",
    ]:
        if path.is_file():
            return str(path)

    raise RuntimeError(
        "whisper.cpp CLI was not found. Install/build whisper.cpp and set "
        "ONEVEX_WHISPER_CLI if it is not in PATH."
    )


def transcribe_audio(model_path: Path, whisper_cli: str | None) -> str:
    if not model_path.is_file():
        raise RuntimeError(f"Whisper model not found: {model_path}")

    if not AUDIO_FILE.is_file() or AUDIO_FILE.stat().st_size == 0:
        raise RuntimeError(f"Recording is missing or empty: {AUDIO_FILE}")

    TRANSCRIPT_FILE.unlink(missing_ok=True)
    cli_path = find_whisper_cli(whisper_cli)

    result = subprocess.run(
        [
            cli_path,
            "-m",
            str(model_path),
            "-f",
            str(AUDIO_FILE),
            "-otxt",
            "-of",
            str(TRANSCRIPT_BASE),
            "-nt",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        output = (result.stderr or result.stdout).strip()
        message = f"whisper.cpp failed with exit code {result.returncode}"
        if output:
            message = f"{message}: {output}"
        raise RuntimeError(message)

    if not TRANSCRIPT_FILE.is_file():
        raise RuntimeError(f"whisper.cpp did not create transcript: {TRANSCRIPT_FILE}")

    return TRANSCRIPT_FILE.read_text(encoding="utf-8").strip()


def stop_transcribe_type(model: str, whisper_cli: str | None) -> None:
    if not stop_recording():
        return

    transcript = transcribe_audio(Path(model).expanduser(), whisper_cli)
    if not transcript:
        logging.info("Transcript is empty; nothing to type")
        return

    type_text(transcript)
    logging.info("Typed transcript with %d characters", len(transcript))


def main() -> int:
    args = parse_args()
    configure_logging()

    try:
        if args.command == "start":
            start_recording()
        elif args.command == "stop-transcribe-type":
            stop_transcribe_type(args.model, args.whisper_cli)
        elif args.command == "cancel":
            stop_recording()
    except Exception:
        logging.exception("Voice input command failed: %s", args.command)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
