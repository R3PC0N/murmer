import subprocess
import unittest
from unittest.mock import call, patch

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
    @patch("paster.subprocess.run")
    @patch("paster.shutil.which", return_value="/usr/bin/wtype")
    @patch("paster.detect_backend", return_value="wayland")
    def test_paste_text_sends_cleaned_value_to_wayland_stdin(
        self, _detect_backend, _which, run
    ):
        run.return_value = subprocess.CompletedProcess(
            ["/usr/bin/wtype", "-d", "5", "-"], 0, "", ""
        )
        text = "CLEANED OUTPUT 12345 — € ñ 中文\nLiteral: $HOME; $(echo raw)\tend"

        paster.paste_text(text)

        run.assert_called_once_with(
            ["/usr/bin/wtype", "-d", "5", "-"],
            input=(
                "CLEANED OUTPUT 12345 — € ñ 中文\n"
                "Literal: $HOME; $(echo raw)    end"
            ),
            text=True,
            capture_output=True,
            check=False,
        )

    def test_wayland_chunking_prefers_whitespace_without_changing_text(self):
        text = "alpha beta, gamma delta\nHé — € ñ 中文 punctuation! final"

        chunks = paster._chunk_wayland_text(text, max_chars=18)

        self.assertEqual(
            chunks,
            ["alpha beta, gamma ", "delta\nHé — € ñ 中文 ", "punctuation! final"],
        )
        self.assertEqual("".join(chunks), text)
        self.assertTrue(all(len(chunk) <= 18 for chunk in chunks))

    def test_wayland_chunking_uses_punctuation_then_hard_boundary(self):
        punctuated = "abcdefghij,klmnopqrst"
        unbroken = "abcdefghijklmnopqrstuvwxyz"

        punctuation_chunks = paster._chunk_wayland_text(punctuated, max_chars=12)
        hard_chunks = paster._chunk_wayland_text(unbroken, max_chars=10)

        self.assertEqual(punctuation_chunks[0], "abcdefghij,")
        self.assertEqual("".join(punctuation_chunks), punctuated)
        self.assertEqual(hard_chunks, ["abcdefghij", "klmnopqrst", "uvwxyz"])

    @patch("paster.time.sleep")
    @patch("paster.subprocess.run")
    @patch("paster.shutil.which", return_value="/usr/bin/wtype")
    def test_long_wayland_text_uses_sequential_literal_chunks(
        self, _which, run, sleep
    ):
        run.return_value = subprocess.CompletedProcess([], 0, "", "")
        text = (
            "Dit is een langere Nederlandse test, met punctuation; Unicode € ñ 中文, "
            "een newline\nen shell-achtige tekst: $HOME $(echo raw).\tEinde."
        )
        normalized = text.replace("\t", "    ")
        expected_chunks = paster._chunk_wayland_text(normalized)

        paster._paste_wayland(text)

        self.assertGreater(len(expected_chunks), 1)
        self.assertEqual("".join(expected_chunks), normalized)
        self.assertEqual(
            run.call_args_list,
            [
                call(
                    ["/usr/bin/wtype", "-d", "5", "-"],
                    input=chunk,
                    text=True,
                    capture_output=True,
                    check=False,
                )
                for chunk in expected_chunks
            ],
        )
        self.assertEqual(
            sleep.call_args_list,
            [call(paster._WAYLAND_CHUNK_PAUSE_SECONDS)]
            * (len(expected_chunks) - 1),
        )

    @patch("paster.time.sleep")
    @patch("paster.subprocess.run")
    @patch("paster.shutil.which", return_value="/usr/bin/wtype")
    def test_wayland_chunk_failure_stops_later_chunks(self, _which, run, sleep):
        run.side_effect = [
            subprocess.CompletedProcess([], 0, "", ""),
            subprocess.CompletedProcess([], 2, "", "chunk failed"),
        ]
        text = "first chunk words " * 12

        with self.assertRaisesRegex(paster.TextInsertionError, "chunk failed"):
            paster._paste_wayland(text)

        self.assertEqual(run.call_count, 2)
        sleep.assert_called_once_with(paster._WAYLAND_CHUNK_PAUSE_SECONDS)

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
        text = "Shell: $HOME; $(raw)\nHé € 中文\tend"

        paster._paste_wayland(text)

        run.assert_called_once_with(
            ["/usr/bin/wtype", "-d", "5", "-"],
            input="Shell: $HOME; $(raw)\nHé € 中文    end",
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

    @patch("paster._paste_x11")
    @patch("paster.detect_backend", return_value="x11")
    def test_paste_text_keeps_x11_dispatch_unchanged(self, _detect, paste_x11):
        paster.paste_text("exact text")

        paste_x11.assert_called_once_with("exact text")

    @patch("paster._paste_windows")
    @patch("paster.detect_backend", return_value="windows")
    def test_paste_text_keeps_windows_dispatch_unchanged(
        self, _detect, paste_windows
    ):
        paster.paste_text("exact text")

        paste_windows.assert_called_once_with("exact text")

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
