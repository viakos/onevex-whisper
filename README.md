# OneVex Whisper GNOME Extension

OneVex Whisper is a small GNOME Shell extension for Fedora GNOME 50 on Wayland.
Press `Ctrl+Space` to show a blinking red recording indicator and start recording from the microphone. Press `Ctrl+Space` again to hide the indicator, stop recording, transcribe the speech with Whisper, and type the spoken text into the currently focused field.

The recording indicator is shown near the bottom center of the primary monitor:

- Size: `14 x 14`
- Position: centered horizontally, `40px` above the bottom edge
- Style: blinking red circle

## Important Wayland Note

Wayland does not allow normal applications to inject keyboard input into other applications directly. To type into desktop apps, web apps, terminals, and other focused fields, this project uses `ydotool`, which sends input through Linux `uinput`.

Install `ydotool` before testing text insertion:

```bash
sudo dnf install ydotool
```

This project includes a development helper that creates and starts a system service for `ydotoold`:

```bash
./scripts/setup-ydotoold-system-service.sh
```

The helper creates `/etc/systemd/system/onevex-whisper-ydotoold.service` and starts `ydotoold` as root, because Fedora commonly exposes `/dev/uinput` as `root:root` with `0600` permissions. The service socket is created at `/run/onevex-whisper/ydotool_socket` and owned by your user.

If the service fails, check its logs:

```bash
sudo journalctl -u onevex-whisper-ydotoold.service --no-pager
```

The Python helper sets `YDOTOOL_SOCKET=/run/onevex-whisper/ydotool_socket` when it calls `ydotool`.

The helper intentionally waits briefly and releases common modifier keys before typing. Without this, the `Ctrl+Space` trigger can leave `Ctrl` active for the first generated characters, causing text such as `This is my text` to be interpreted as shortcuts like `Ctrl+S` instead of plain text.

The recording indicator can still appear without `ydotool`, but text insertion will fail and the Python helper will log the error to `~/.local/state/onevex-whisper/text-injector.log`.

## Speech To Text Dependencies

This project expects a local `whisper.cpp` command-line binary and a local GGML model.

The model path used by default is:

```text
models/ggml-small.bin
```

The helper searches for the Whisper CLI in this order:

- `ONEVEX_WHISPER_CLI`, if set
- `whisper-cli` in `PATH`
- `whisper-cpp` in `PATH`
- `~/dev/whisper.cpp/build/bin/whisper-cli`
- `~/dev/whisper.cpp/build/bin/main`
- `~/dev/whisper.cpp/main`

If you need to build `whisper.cpp`:

```bash
git clone https://github.com/ggerganov/whisper.cpp ~/dev/whisper.cpp
cmake -S ~/dev/whisper.cpp -B ~/dev/whisper.cpp/build
cmake --build ~/dev/whisper.cpp/build -j
```

Audio recording uses `pw-record`, which is usually available through PipeWire tools on Fedora:

```bash
sudo dnf install pipewire-utils
```

Runtime logs are written to:

```text
~/.local/state/onevex-whisper/voice-input.log
~/.local/state/onevex-whisper/recorder.log
~/.local/state/onevex-whisper/text-injector.log
```

## Project Layout

```text
extension/
  extension.js
  metadata.json
  python/type_text.py
  python/voice_input.py
  schemas/org.gnome.shell.extensions.onevex-whisper.gschema.xml
models/
  ggml-small.bin
scripts/
  deploy-dev.sh
```

The Python helper lives inside the extension directory so the installed extension and development source always use the same code.

## Development Install

From the project root:

```bash
./scripts/deploy-dev.sh install
```

The script:

- Compiles the GSettings schema with `glib-compile-schemas`
- Creates a symlink from `~/.local/share/gnome-shell/extensions/onevex-whisper@local` to this project's `extension/` directory
- Attempts to enable the extension with `gnome-extensions enable onevex-whisper@local`

On Wayland, GNOME Shell extensions are loaded at login. If this is the first install or GNOME does not see changes, log out and log back in.

## Check GNOME Can See The Extension

After installing, check whether GNOME Shell can see the extension:

```bash
gnome-extensions list | grep onevex-whisper
```

Expected output:

```text
onevex-whisper@local
```

To see detailed extension state:

```bash
gnome-extensions info onevex-whisper@local
```

If GNOME says the extension does not exist, run the development install again and then log out and log back in:

```bash
./scripts/deploy-dev.sh install
```

## Development Workflow

1. Edit files in this project.
2. Run `./scripts/deploy-dev.sh install` after schema changes.
3. Log out and back in when GNOME Shell needs to reload the extension.
4. Watch extension logs with:

```bash
journalctl --user -f -o cat /usr/bin/gnome-shell
```

5. Watch Python helper logs with:

```bash
tail -f ~/.local/state/onevex-whisper/text-injector.log
```

6. Check that `ydotoold` is running:

```bash
systemctl status onevex-whisper-ydotoold.service --no-pager
```

## Uninstall Development Symlink

```bash
./scripts/uninstall-dev.sh
```

This is equivalent to:

```bash
./scripts/deploy-dev.sh uninstall
```

The uninstall command disables the extension if `gnome-extensions` is available, then removes only the development symlink created by this project. It refuses to remove unrelated extension directories.

To remove the optional system `ydotoold` service created by this project:

```bash
./scripts/uninstall-ydotoold-system-service.sh
```

## Manual Voice Helper Test

Start recording:

```bash
python3 extension/python/voice_input.py start
```

Speak into the microphone, focus a text field, then stop, transcribe, and type:

```bash
python3 extension/python/voice_input.py stop-transcribe-type
```

If recording works but typing fails, fix `ydotool` or `ydotoold` before debugging the GNOME extension.
