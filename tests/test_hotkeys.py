import subprocess
import sys
import types
import unittest
from unittest.mock import Mock, patch

import hotkeys


class BackendSelectionTests(unittest.TestCase):
    def test_windows_backend(self):
        self.assertEqual(hotkeys.detect_backend("win32", {}), "windows")

    def test_x11_backend(self):
        self.assertEqual(
            hotkeys.detect_backend("linux", {"XDG_SESSION_TYPE": "x11", "DISPLAY": ":0"}),
            "x11",
        )

    def test_hyprland_wins_when_xwayland_display_exists(self):
        environment = {
            "XDG_SESSION_TYPE": "wayland",
            "WAYLAND_DISPLAY": "wayland-1",
            "DISPLAY": ":0",
            "XDG_CURRENT_DESKTOP": "Hyprland",
        }
        self.assertEqual(
            hotkeys.detect_backend("linux", environment, hyprctl_available=True),
            "hyprland",
        )

    def test_other_wayland_is_explicitly_unsupported(self):
        environment = {
            "XDG_SESSION_TYPE": "wayland",
            "WAYLAND_DISPLAY": "wayland-1",
            "XDG_CURRENT_DESKTOP": "sway",
        }
        self.assertEqual(
            hotkeys.detect_backend("linux", environment, hyprctl_available=True),
            "unsupported-wayland",
        )

    def test_wayland_settings_use_selection_instead_of_raw_capture(self):
        with patch("hotkeys.detect_backend", return_value="hyprland"):
            self.assertEqual(hotkeys.capture_mode(), "select")


class KeyTests(unittest.TestCase):
    def test_key_normalization(self):
        self.assertEqual(hotkeys.normalize_key(" F8 "), "f8")
        self.assertEqual(hotkeys.normalize_key("Escape"), "esc")
        self.assertEqual(hotkeys._hyprland_key("f8"), "F8")

    def test_unsupported_key_is_rejected(self):
        with self.assertRaises(hotkeys.HotkeyError):
            hotkeys.normalize_key("not-a-key")

    def test_x11_preserves_arbitrary_character_keys(self):
        fake_keyboard = types.SimpleNamespace(Key=types.SimpleNamespace(
            **{f"f{i}": object() for i in range(1, 13)},
            **{name: object() for name in (
                "space", "enter", "tab", "backspace", "delete", "esc",
                "ctrl", "ctrl_l", "ctrl_r", "alt", "alt_l", "alt_r",
                "shift", "shift_l", "shift_r", "caps_lock", "up", "down",
                "left", "right", "home", "end", "page_up", "page_down",
            )},
        ))
        fake_pynput = types.SimpleNamespace(keyboard=fake_keyboard)
        with patch.dict(sys.modules, {"pynput": fake_pynput}):
            self.assertEqual(hotkeys._pynput_key(";"), ";")

    def test_plain_bind_output_is_parsed(self):
        output = """bindd
\tmodmask: 0
\tkey: F9
\tdescription: Start dictation
\tdispatcher: exec
\targ: voxtype record start

bindrd
\tmodmask: 0
\tkey: F9
\tdescription: Stop dictation
\tdispatcher: exec
\targ: voxtype record stop
"""
        records = hotkeys._parse_hyprland_binds(output)
        self.assertEqual([record["type"] for record in records], ["bindd", "bindrd"])
        self.assertEqual(records[0]["key"], "F9")
        self.assertEqual(records[1]["description"], "Stop dictation")


class HyprlandBackendTests(unittest.TestCase):
    def make_backend(self):
        with patch(
            "hotkeys.app_paths.runtime_directory",
            return_value=hotkeys.Path("/tmp/murmur-test-runtime"),
        ):
            return hotkeys.HyprlandHotkeyBackend("f8", Mock(), Mock())

    def test_existing_binding_is_reported_without_unbinding_it(self):
        backend = self.make_backend()
        conflict = {
            "key": "F8", "modmask": "0", "description": "Existing action",
            "arg": "existing-command",
        }
        with (
            patch("hotkeys._bindings_for_key", return_value=[conflict]),
            patch("hotkeys._run_hyprctl") as run,
        ):
            with self.assertRaisesRegex(hotkeys.HotkeyError, "Existing action"):
                backend._check_conflicts()
        run.assert_not_called()

    def test_stale_murmur_binding_is_cleaned(self):
        backend = self.make_backend()
        stale = {
            "key": "F8", "modmask": "0",
            "description": "Murmur push-to-talk press [old]",
        }
        with (
            patch("hotkeys._bindings_for_key", return_value=[stale]),
            patch("hotkeys._run_hyprctl") as run,
        ):
            backend._check_conflicts()
        run.assert_called_once_with(["keyword", "unbind", ", F8"])

    def test_press_release_commands_and_cleanup(self):
        backend = self.make_backend()
        fake_socket = Mock()
        fake_thread = Mock()
        with (
            patch("hotkeys._bindings_for_key", return_value=[]),
            patch("hotkeys._run_hyprctl") as run,
            patch("hotkeys.socket.socket", return_value=fake_socket),
            patch("hotkeys.threading.Thread", return_value=fake_thread),
            patch("hotkeys.os.chmod"),
            patch.object(hotkeys.Path, "unlink"),
        ):
            backend.start()
            backend.stop()

        keyword_calls = [call.args[0] for call in run.call_args_list]
        self.assertEqual(keyword_calls[0][:2], ["keyword", "bindd"])
        self.assertEqual(keyword_calls[1][:2], ["keyword", "binddr"])
        self.assertIn(" emit ", keyword_calls[0][2])
        self.assertIn(" press ", keyword_calls[0][2])
        self.assertIn(" release ", keyword_calls[1][2])
        self.assertEqual(keyword_calls[2], ["keyword", "unbind", ", F8"])

    def test_release_registration_failure_removes_press_binding(self):
        backend = self.make_backend()
        fake_socket = Mock()
        calls = []

        def run(args):
            calls.append(args)
            if args[:2] == ["keyword", "binddr"]:
                raise hotkeys.HotkeyError("release failed")
            return ""

        with (
            patch("hotkeys._bindings_for_key", return_value=[]),
            patch("hotkeys._run_hyprctl", side_effect=run),
            patch("hotkeys.socket.socket", return_value=fake_socket),
            patch("hotkeys.threading.Thread", return_value=Mock()),
            patch("hotkeys.os.chmod"),
            patch.object(hotkeys.Path, "unlink"),
        ):
            with self.assertRaisesRegex(hotkeys.HotkeyError, "release failed"):
                backend.start()

        self.assertIn(["keyword", "unbind", ", F8"], calls)

    def test_hotkey_options_report_conflicts(self):
        records = [
            {"key": "F8", "modmask": "0", "description": "Existing F8 action"},
            {"key": "F9", "modmask": "0", "description": "Murmur push-to-talk press [self]"},
        ]
        with (
            patch("hotkeys.detect_backend", return_value="hyprland"),
            patch("hotkeys._run_hyprctl", return_value="bind output"),
            patch("hotkeys._parse_hyprland_binds", return_value=records),
        ):
            options = {item["key"]: item for item in hotkeys.hotkey_options()}

        self.assertFalse(options["f8"]["available"])
        self.assertEqual(options["f8"]["conflicts"], ["Existing F8 action"])
        self.assertTrue(options["f9"]["available"])


class HyprctlCommandTests(unittest.TestCase):
    @patch("hotkeys.shutil.which", return_value="/usr/bin/hyprctl")
    @patch("hotkeys.subprocess.run")
    def test_hyprctl_uses_argument_array(self, run, _which):
        run.return_value = subprocess.CompletedProcess([], 0, "ok\n", "")
        hotkeys._run_hyprctl(["keyword", "unbind", ", F8"])
        run.assert_called_once_with(
            ["/usr/bin/hyprctl", "keyword", "unbind", ", F8"],
            text=True,
            capture_output=True,
            check=False,
            timeout=5,
        )


if __name__ == "__main__":
    unittest.main()
