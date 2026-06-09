import os
import re
import shutil
import subprocess
import threading
import time

import sublime
import sublime_plugin


SETTINGS_FILE = "AutoAppearance.sublime-settings"
PREFERENCES_FILE = "Preferences.sublime-settings"

PORTAL_BUS_NAME = "org.freedesktop.portal.Desktop"
PORTAL_OBJECT_PATH = "/org/freedesktop/portal/desktop"
PORTAL_SETTINGS_INTERFACE = "org.freedesktop.portal.Settings"
PORTAL_APPEARANCE_NAMESPACE = "org.freedesktop.appearance"
PORTAL_COLOR_SCHEME_KEY = "color-scheme"

COLOR_SCHEMES = {
    0: "no_preference",
    1: "dark",
    2: "light",
}


_controller = None


def plugin_loaded():
    global _controller

    _controller = AutoAppearanceController()
    _controller.start()
    sublime.load_settings(SETTINGS_FILE).add_on_change("auto_appearance.reload", _restart)


def plugin_unloaded():
    global _controller

    sublime.load_settings(SETTINGS_FILE).clear_on_change("auto_appearance.reload")
    if _controller:
        _controller.stop()
    _controller = None


def _restart():
    if _controller:
        _controller.restart()


class AutoAppearanceSyncCommand(sublime_plugin.ApplicationCommand):
    def run(self):
        if _controller:
            _controller.sync_now("manual")


class AutoAppearanceRestartCommand(sublime_plugin.ApplicationCommand):
    def run(self):
        if _controller:
            _controller.restart()


class AutoAppearanceController:
    def __init__(self):
        self.settings = sublime.load_settings(SETTINGS_FILE)
        self._lock = threading.RLock()
        self._stop_event = threading.Event()
        self._monitor_process = None
        self._monitor_thread = None
        self._sync_timer = None

    def start(self):
        with self._lock:
            if not self._enabled():
                self._debug("disabled")
                return

            if self._monitor_thread and self._monitor_thread.is_alive():
                return

            self._stop_event.clear()
            self._monitor_thread = threading.Thread(
                target=self._monitor_loop,
                name="AutoAppearance busctl monitor",
                daemon=True,
            )
            self._monitor_thread.start()

        self.sync_now("startup")

    def stop(self):
        with self._lock:
            self._stop_event.set()
            self._cancel_pending_sync()
            process = self._monitor_process
            thread = self._monitor_thread
            self._monitor_process = None

        if process and process.poll() is None:
            try:
                process.terminate()
            except OSError:
                pass

        if thread and thread is not threading.current_thread():
            thread.join(timeout=2.0)

        with self._lock:
            if self._monitor_thread is thread:
                self._monitor_thread = None

    def restart(self):
        self._debug("restarting")
        self.stop()
        self.start()

    def sync_now(self, reason):
        thread = threading.Thread(
            target=self._sync_from_worker,
            args=(reason,),
            name="AutoAppearance sync",
            daemon=True,
        )
        thread.start()

    def _monitor_loop(self):
        backoff_seconds = 1.0

        while not self._stop_event.is_set():
            binary = self._busctl_binary()
            if not binary:
                self._status("AutoAppearance: busctl was not found")
                return

            argv = [
                binary,
                "--user",
                "monitor",
                PORTAL_BUS_NAME,
            ]

            try:
                self._debug("starting monitor: {}".format(" ".join(argv)))
                process = subprocess.Popen(
                    argv,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    universal_newlines=True,
                    bufsize=1,
                )
            except OSError as exc:
                self._status("AutoAppearance: could not start busctl monitor")
                self._debug("monitor start failed: {!r}".format(exc))
                return

            with self._lock:
                self._monitor_process = process

            watching_setting_changed = False
            saw_appearance_namespace = False
            saw_color_scheme_key = False

            try:
                assert process.stdout is not None
                for line in process.stdout:
                    if self._stop_event.is_set():
                        break

                    if line.startswith("\u2023 Type=") or line.startswith("Type="):
                        watching_setting_changed = False
                        saw_appearance_namespace = False
                        saw_color_scheme_key = False

                    if "Member=SettingChanged" in line:
                        self._debug("portal SettingChanged signal detected")
                        watching_setting_changed = True
                        saw_appearance_namespace = False
                        saw_color_scheme_key = False

                    if watching_setting_changed:
                        if PORTAL_APPEARANCE_NAMESPACE in line:
                            saw_appearance_namespace = True
                        if PORTAL_COLOR_SCHEME_KEY in line:
                            saw_color_scheme_key = True

                        if saw_appearance_namespace and saw_color_scheme_key:
                            self._debug("portal color-scheme change detected")
                            self._schedule_sync("portal-signal")
                            watching_setting_changed = False
            finally:
                with self._lock:
                    if self._monitor_process is process:
                        self._monitor_process = None

                if process.poll() is None:
                    try:
                        process.terminate()
                    except OSError:
                        pass

                return_code = process.wait()

            if self._stop_event.is_set():
                break

            self._debug("monitor exited with code {}".format(return_code))
            time.sleep(backoff_seconds)
            backoff_seconds = min(backoff_seconds * 2.0, 30.0)

    def _schedule_sync(self, reason):
        with self._lock:
            self._cancel_pending_sync()
            self._sync_timer = threading.Timer(
                float(self.settings.get("sync_debounce_seconds", 0.25)),
                self._sync_from_worker,
                args=(reason,),
            )
            self._sync_timer.daemon = True
            self._sync_timer.start()

    def _cancel_pending_sync(self):
        if self._sync_timer:
            self._sync_timer.cancel()
            self._sync_timer = None

    def _sync_from_worker(self, reason):
        if not self._enabled():
            return

        value = self._read_portal_color_scheme()
        if value is None:
            return

        scheme = COLOR_SCHEMES.get(value)
        if not scheme:
            self._debug("unknown portal color-scheme value: {}".format(value))
            return

        if scheme == "no_preference":
            scheme = self.settings.get("no_preference", "light")

        if scheme not in ("dark", "light"):
            self._debug("invalid no_preference setting: {!r}".format(scheme))
            return

        self._debug("syncing {} scheme ({})".format(scheme, reason))
        sublime.set_timeout(lambda: self._apply_scheme(scheme), 0)

    def _read_portal_color_scheme(self):
        binary = self._busctl_binary()
        if not binary:
            self._status("AutoAppearance: busctl was not found")
            return None

        argv = [
            binary,
            "--user",
            "call",
            PORTAL_BUS_NAME,
            PORTAL_OBJECT_PATH,
            PORTAL_SETTINGS_INTERFACE,
            "ReadOne",
            "ss",
            PORTAL_APPEARANCE_NAMESPACE,
            PORTAL_COLOR_SCHEME_KEY,
        ]

        try:
            process = subprocess.Popen(
                argv,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
            )
        except OSError as exc:
            self._status("AutoAppearance: could not read system color scheme")
            self._debug("busctl read failed: {!r}".format(exc))
            return None

        try:
            stdout, stderr = process.communicate(
                timeout=float(self.settings.get("busctl_timeout_seconds", 3.0))
            )
        except subprocess.TimeoutExpired as exc:
            process.kill()
            stdout, stderr = process.communicate()
            self._status("AutoAppearance: system color scheme read timed out")
            self._debug("busctl read timed out: {!r}".format(exc))
            return None

        if process.returncode != 0:
            self._status("AutoAppearance: portal color scheme read failed")
            self._debug("busctl stderr: {}".format(stderr.strip()))
            return None

        value = _parse_busctl_uint32(stdout)
        if value is None:
            self._debug("could not parse busctl output: {!r}".format(stdout))
            return None

        return value

    def _apply_scheme(self, scheme):
        preferences = sublime.load_settings(PREFERENCES_FILE)
        theme = preferences.get("{}_theme".format(scheme))
        color_scheme = preferences.get("{}_color_scheme".format(scheme))

        if not theme and not color_scheme:
            self._status(
                "AutoAppearance: no Sublime {} appearance settings found".format(scheme)
            )
            self._debug(
                "missing {}_theme and {}_color_scheme preferences".format(scheme, scheme)
            )
            return

        changed = False

        if theme and preferences.get("theme") != theme:
            preferences.set("theme", theme)
            changed = True

        if color_scheme and preferences.get("color_scheme") != color_scheme:
            preferences.set("color_scheme", color_scheme)
            changed = True

        if changed:
            sublime.save_settings(PREFERENCES_FILE)
            self._status("AutoAppearance: switched to {} appearance".format(scheme))

    def _enabled(self):
        return bool(self.settings.get("enabled", True))

    def _busctl_binary(self):
        configured = self.settings.get("busctl_binary", "busctl")
        if os.path.isabs(configured) and os.access(configured, os.X_OK):
            return configured

        found = shutil.which(configured)
        if found:
            return found

        for candidate in ("/usr/bin/busctl", "/bin/busctl", "/usr/local/bin/busctl"):
            if os.access(candidate, os.X_OK):
                return candidate

        return None

    def _status(self, message):
        sublime.set_timeout(lambda: sublime.status_message(message), 0)

    def _debug(self, message):
        if self.settings.get("debug", False):
            print("[AutoAppearance] {}".format(message))


def _parse_busctl_uint32(output):
    matches = re.findall(r"\b(?:UINT32|uint32|u)\s+([0-9]+)\b", output)
    if matches:
        return int(matches[-1])

    tokens = re.findall(r"\b[0-9]+\b", output)
    if tokens:
        return int(tokens[-1])

    return None
