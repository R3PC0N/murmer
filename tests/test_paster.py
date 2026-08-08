import subprocess
import unittest
from unittest.mock import patch

import paster


class BackendDetectionTests(unittest.TestCase):
    def test_windows_is_selected_independently_of_session_variables(self):
        self.assertEqual(
            paster.detect_backend("win32", {"XDG_SESSION_TYPE": "wayland"}),
            "windows",
        )

    def test_x11_session_is_selected(self):
        self.assertEqual(
            paster.detect_backend("linux", {"XDG_SESSION_TYPE": "x11", "DISPLAY": ":0"}),
            "x11",
        )

    def test_wayland_session_wins_when_xwayland_display_is_present(self):
        environment = {
            "XDG_SESSION_TYPE": "wayland",
            "WAYLAND_DISPLAY": "wayland-1",
            "DISPLAY": ":0",
        }
        self.assertEqual(paster.detect_backend("linux", environment), "wayland")

    def test_wayland_display_is_sufficient(self):
        self.assertEqual(
            paster.detect_backend("linux", {"WAYLAND_DISPLAY": "wayland-1"}),
            "wayland",
        )

    def test_unknown_linux_session_has_a_clear_error(self):
        with self.assertRaisesRegex(paster.TextInsertionError, "Cannot determine"):
            paster.detect_backend("linux", {})


class CommandTests(unittest.TestCase):
    def test_missing_wayland_executable_has_a_clear_error(self):
        with patch("paster.shutil.which", return_value=None):
            with self.assertRaisesRegex(paster.TextInsertionError, "wtype.*not found"):
                paster._paste_wayland("hello")

    def test_missing_x11_executable_has_a_clear_error(self):
        with patch("paster.shutil.which", return_value=None):
            with self.assertRaisesRegex(paster.TextInsertionError, "xdotool.*not found"):
                paster._paste_x11("hello")

    @patch("paster.subprocess.run")
    @patch("paster.shutil.which", return_value="/usr/bin/wtype")
    def test_wayland_passes_literal_text_via_delayed_stdin(self, _which, run):
        run.return_value = subprocess.CompletedProcess(
            ["/usr/bin/wtype", "-d", "5", "-"], 0, "", ""
        )
        text = "Shell: $(nothing); $HOME && echo 'nope'\nHé — € ñ 中文\nTabbed:\tafter"

        paster._paste_wayland(text)

        run.assert_called_once_with(
            ["/usr/bin/wtype", "-d", "5", "-"],
            input=(
                "Shell: $(nothing); $HOME && echo 'nope'\n"
                "Hé — € ñ 中文\n"
                "Tabbed:    after"
            ),
            text=True,
            capture_output=True,
            check=False,
        )

    @patch("paster.subprocess.run")
    @patch("paster.shutil.which", return_value="/usr/bin/wtype")
    def test_wayland_preserves_newlines_and_normalizes_every_tab(self, _which, run):
        run.return_value = subprocess.CompletedProcess([], 0, "", "")

        paster._paste_wayland("one\t\ttwo\nthree")

        self.assertEqual(run.call_args.kwargs["input"], "one        two\nthree")

    @patch("paster.subprocess.run")
    @patch("paster.shutil.which", return_value="/usr/bin/xdotool")
    def test_x11_preserves_xdotool_argument_construction(self, _which, run):
        run.return_value = subprocess.CompletedProcess([], 0, "", "")
        text = "quotes ' and shell $syntax"

        paster._paste_x11(text)

        run.assert_called_once_with(
            [
                "/usr/bin/xdotool",
                "type",
                "--clearmodifiers",
                "--delay",
                "0",
                "--",
                text,
            ],
            input=None,
            text=True,
            capture_output=True,
            check=False,
        )

    @patch("paster.subprocess.run")
    @patch("paster.shutil.which", return_value="/usr/bin/wtype")
    def test_nonzero_exit_is_reported(self, _which, run):
        run.return_value = subprocess.CompletedProcess([], 2, "", "permission denied")

        with self.assertRaisesRegex(paster.TextInsertionError, "permission denied"):
            paster._paste_wayland("hello")


if __name__ == "__main__":
    unittest.main()
