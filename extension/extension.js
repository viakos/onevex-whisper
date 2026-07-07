import GLib from 'gi://GLib';
import Meta from 'gi://Meta';
import Shell from 'gi://Shell';
import St from 'gi://St';
import Clutter from 'gi://Clutter';

import {Extension} from 'resource:///org/gnome/shell/extensions/extension.js';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';

const KEYBINDING_NAME = 'show-rectangle';

const RECORDING_DOT_SIZE = 14;
const RECORDING_DOT_MARGIN_BOTTOM = 40;
const BLINK_DURATION_MS = 650;

const RECORDING_DOT_STYLE = `
    background-color: rgba(255, 0, 0, 0.95);
    border-radius: 999px;
`;

export default class OneVexWhisperExtension extends Extension {
    enable() {
        this._settings = this.getSettings();
        this._monitorsChangedId = 0;

        this._recordingDot = new St.Widget({
            reactive: false,
            style: RECORDING_DOT_STYLE,
            visible: false,
            y_align: Clutter.ActorAlign.CENTER,
        });
        this._recordingDot.set_size(RECORDING_DOT_SIZE, RECORDING_DOT_SIZE);

        Main.uiGroup.add_child(this._recordingDot);
        this._positionRecordingDot();

        this._monitorsChangedId = Main.layoutManager.connect(
            'monitors-changed',
            () => this._positionRecordingDot()
        );

        Main.wm.addKeybinding(
            KEYBINDING_NAME,
            this._settings,
            Meta.KeyBindingFlags.NONE,
            Shell.ActionMode.NORMAL,
            () => this._activate()
        );
    }

    disable() {
        Main.wm.removeKeybinding(KEYBINDING_NAME);

        if (this._recordingDot && this._recordingDot.visible)
            this._runVoiceCommand('cancel');

        if (this._monitorsChangedId) {
            Main.layoutManager.disconnect(this._monitorsChangedId);
            this._monitorsChangedId = 0;
        }

        this._stopBlinkingDot();

        if (this._recordingDot) {
            this._recordingDot.destroy();
            this._recordingDot = null;
        }

        this._settings = null;
    }

    _activate() {
        const isVisible = this._toggleRectangle();

        if (isVisible)
            this._runVoiceCommand('start');
        else
            this._runVoiceCommand('stop-transcribe-type');
    }

    _toggleRectangle() {
        if (!this._recordingDot)
            return false;

        this._positionRecordingDot();
        this._recordingDot.visible = !this._recordingDot.visible;

        if (this._recordingDot.visible)
            this._startBlinkingDot();
        else
            this._stopBlinkingDot();

        return this._recordingDot.visible;
    }

    _startBlinkingDot() {
        if (!this._recordingDot)
            return;

        this._recordingDot.opacity = 255;
        this._blinkRecordingDot();
    }

    _blinkRecordingDot() {
        if (!this._recordingDot || !this._recordingDot.visible)
            return;

        const targetOpacity = this._recordingDot.opacity > 128 ? 70 : 255;

        this._recordingDot.ease({
            opacity: targetOpacity,
            duration: BLINK_DURATION_MS,
            mode: Clutter.AnimationMode.EASE_IN_OUT_SINE,
            onComplete: () => this._blinkRecordingDot(),
        });
    }

    _stopBlinkingDot() {
        if (!this._recordingDot)
            return;

        this._recordingDot.remove_all_transitions();
        this._recordingDot.opacity = 255;
    }

    _positionRecordingDot() {
        if (!this._recordingDot)
            return;

        const monitor = Main.layoutManager.primaryMonitor;
        const x = monitor.x + Math.floor((monitor.width - RECORDING_DOT_SIZE) / 2);
        const y = monitor.y + monitor.height - RECORDING_DOT_SIZE - RECORDING_DOT_MARGIN_BOTTOM;

        this._recordingDot.set_position(x, y);
    }

    _runVoiceCommand(command) {
        const scriptPath = GLib.build_filenamev([
            this.path,
            'python',
            'voice_input.py',
        ]);

        if (!GLib.file_test(scriptPath, GLib.FileTest.IS_REGULAR)) {
            console.error(`OneVex Whisper: missing voice input helper: ${scriptPath}`);
            return;
        }

        try {
            GLib.spawn_async(
                this.path,
                ['python3', scriptPath, command],
                null,
                GLib.SpawnFlags.SEARCH_PATH,
                null
            );
        } catch (error) {
            console.error(`OneVex Whisper: failed to run voice input helper: ${error.message}`);
        }
    }
}
