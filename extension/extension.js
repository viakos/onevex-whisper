import GLib from 'gi://GLib';
import Meta from 'gi://Meta';
import Shell from 'gi://Shell';
import St from 'gi://St';

import {Extension} from 'resource:///org/gnome/shell/extensions/extension.js';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';

const KEYBINDING_NAME = 'show-rectangle';

const RECTANGLE_WIDTH = 100;
const RECTANGLE_HEIGHT = 30;
const RECTANGLE_MARGIN_BOTTOM = 40;

const RECTANGLE_STYLE = `
    background-color: rgba(255, 0, 0, 0.65);
    border: 2px solid white;
    border-radius: 6px;
`;

export default class OneVexWhisperExtension extends Extension {
    enable() {
        this._settings = this.getSettings();
        this._monitorsChangedId = 0;

        this._rectangle = new St.Widget({
            reactive: false,
            style: RECTANGLE_STYLE,
            visible: false,
        });
        this._rectangle.set_size(RECTANGLE_WIDTH, RECTANGLE_HEIGHT);

        Main.uiGroup.add_child(this._rectangle);
        this._positionRectangle();

        this._monitorsChangedId = Main.layoutManager.connect(
            'monitors-changed',
            () => this._positionRectangle()
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

        if (this._rectangle && this._rectangle.visible)
            this._runVoiceCommand('cancel');

        if (this._monitorsChangedId) {
            Main.layoutManager.disconnect(this._monitorsChangedId);
            this._monitorsChangedId = 0;
        }

        if (this._rectangle) {
            this._rectangle.destroy();
            this._rectangle = null;
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
        if (!this._rectangle)
            return false;

        this._positionRectangle();
        this._rectangle.visible = !this._rectangle.visible;

        return this._rectangle.visible;
    }

    _positionRectangle() {
        if (!this._rectangle)
            return;

        const monitor = Main.layoutManager.primaryMonitor;
        const x = monitor.x + Math.floor((monitor.width - RECTANGLE_WIDTH) / 2);
        const y = monitor.y + monitor.height - RECTANGLE_HEIGHT - RECTANGLE_MARGIN_BOTTOM;

        this._rectangle.set_position(x, y);
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
