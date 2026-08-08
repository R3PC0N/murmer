import os
import stat
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import app_paths
import autostart
import config
import hotkeys
import linux_bootstrap


class XdgPathTests(unittest.TestCase):
    def test_default_paths(self):
        paths = app_paths.linux_paths(
            environ={}, home=Path("/home/tester"), uid=123, temp_dir=Path("/tmp")
        )
        self.assertEqual(paths.config, Path("/home/tester/.config/murmur"))
        self.assertEqual(paths.data, Path("/home/tester/.local/share/murmur"))
        self.assertEqual(paths.state, Path("/home/tester/.local/state/murmur"))
        self.assertEqual(paths.runtime, Path("/tmp/murmur-runtime-123"))

    def test_environment_overrides(self):
        environment = {
            "XDG_CONFIG_HOME": "/xdg/config",
            "XDG_DATA_HOME": "/xdg/data",
            "XDG_STATE_HOME": "/xdg/state",
            "XDG_RUNTIME_DIR": "/xdg/runtime",
        }
        paths = app_paths.linux_paths(environment, Path("/unused"), uid=123)
        self.assertEqual(paths.config, Path("/xdg/config/murmur"))
        self.assertEqual(paths.data, Path("/xdg/data/murmur"))
        self.assertEqual(paths.state, Path("/xdg/state/murmur"))
        self.assertEqual(paths.runtime, Path("/xdg/runtime/murmur"))

    def test_windows_config_paths_remain_source_relative(self):
        source = Path("C:/Murmur")
        settings, env_file, legacy_settings, legacy_env = app_paths.config_files(
            source, platform="win32"
        )
        self.assertEqual(settings, source / "settings.json")
        self.assertEqual(env_file, source / ".env")
        self.assertEqual(settings, legacy_settings)
        self.assertEqual(env_file, legacy_env)


class MigrationTests(unittest.TestCase):
    def test_legacy_settings_migrate_once_without_removal(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source"
            source.mkdir()
            legacy = source / "settings.json"
            legacy.write_text('{"PUSH_TO_TALK_KEY": "f8"}')
            environment = {"XDG_CONFIG_HOME": str(root / "config")}

            paths = app_paths.initialize_linux_config(
                source, environ=environment, home=root, uid=1000, temp_dir=root
            )
            destination = paths.config / "settings.json"
            first_mtime = destination.stat().st_mtime_ns
            app_paths.initialize_linux_config(
                source, environ=environment, home=root, uid=1000, temp_dir=root
            )

            self.assertEqual(destination.read_text(), legacy.read_text())
            self.assertTrue(legacy.exists())
            self.assertEqual(destination.stat().st_mtime_ns, first_mtime)
            self.assertEqual(stat.S_IMODE(destination.stat().st_mode), 0o600)

    def test_existing_xdg_settings_win_over_legacy(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            legacy = root / "legacy.json"
            destination = root / "config/settings.json"
            legacy.write_text("legacy")
            destination.parent.mkdir()
            destination.write_text("xdg")

            self.assertFalse(app_paths.migrate_file(legacy, destination))
            self.assertEqual(destination.read_text(), "xdg")

    def test_config_reads_xdg_before_legacy(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            xdg = root / "config/settings.json"
            legacy = root / "source/settings.json"
            xdg.parent.mkdir(parents=True)
            legacy.parent.mkdir(parents=True)
            xdg.write_text('{"PUSH_TO_TALK_KEY": "f8"}')
            legacy.write_text('{"PUSH_TO_TALK_KEY": "f9"}')
            with patch.multiple(
                config,
                _SETTINGS_FILE=xdg,
                _LEGACY_SETTINGS_FILE=legacy,
            ):
                loaded = config._load()

            self.assertEqual(loaded["PUSH_TO_TALK_KEY"], "f8")

    def test_config_save_writes_xdg_and_preserves_legacy(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            xdg = root / "config/settings.json"
            legacy = root / "source/settings.json"
            legacy.parent.mkdir(parents=True)
            legacy.write_text('{"PUSH_TO_TALK_KEY": "f8"}')
            with (
                patch.multiple(
                    config,
                    _SETTINGS_FILE=xdg,
                    _LEGACY_SETTINGS_FILE=legacy,
                ),
                patch("config._apply"),
            ):
                config.save({"WHISPER_LANGUAGE": "nl"})

            self.assertIn('"PUSH_TO_TALK_KEY": "f8"', xdg.read_text())
            self.assertIn('"WHISPER_LANGUAGE": "nl"', xdg.read_text())
            self.assertEqual(legacy.read_text(), '{"PUSH_TO_TALK_KEY": "f8"}')
            self.assertEqual(stat.S_IMODE(xdg.stat().st_mode), 0o600)

    def test_env_migration_preserves_secret_without_printing(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            legacy = root / ".env"
            destination = root / "config/.env"
            legacy.write_text("ANTHROPIC_API_KEY=test-secret\n")

            with patch("builtins.print") as output:
                self.assertTrue(app_paths.migrate_file(legacy, destination))

            output.assert_not_called()
            self.assertEqual(destination.read_bytes(), legacy.read_bytes())
            self.assertEqual(stat.S_IMODE(destination.stat().st_mode), 0o600)

    def test_history_and_startup_log_migration(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            legacy = home / ".local/share/Murmur"
            legacy.mkdir(parents=True)
            (legacy / "history.log").write_text("history")
            (legacy / "startup.log").write_text("startup")

            paths = app_paths.initialize_linux_logs(home=home, environ={})

            self.assertEqual((paths.data / "history.log").read_text(), "history")
            self.assertEqual((paths.state / "startup.log").read_text(), "startup")
            self.assertTrue((legacy / "history.log").exists())
            self.assertTrue((legacy / "startup.log").exists())


class RuntimePathTests(unittest.TestCase):
    def test_runtime_directory_is_private(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            runtime = app_paths.runtime_directory(
                environ={"XDG_RUNTIME_DIR": str(root)}, home=root, uid=os.getuid()
            )
            self.assertEqual(runtime, root / "murmur")
            self.assertEqual(stat.S_IMODE(runtime.stat().st_mode), 0o700)

    def test_fallback_lock_is_per_user(self):
        with tempfile.TemporaryDirectory() as directory:
            lock = app_paths.instance_lock_path(
                environ={}, home=Path(directory), uid=4242, temp_dir=Path(directory)
            )
            self.assertEqual(lock, Path(directory) / "murmur-runtime-4242/instance.lock")

    def test_hotkey_socket_uses_murmur_runtime_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            runtime = Path(directory) / "murmur"
            runtime.mkdir()
            with patch("hotkeys.app_paths.runtime_directory", return_value=runtime):
                backend = hotkeys.HyprlandHotkeyBackend("f8", lambda: None, lambda: None)
            self.assertEqual(backend.socket_path.parent, runtime)
            self.assertTrue(backend.socket_path.name.startswith("hotkey-"))


class IntegrationPathTests(unittest.TestCase):
    def test_autostart_honors_xdg_config_home(self):
        desktop = autostart._linux_desktop_file(
            {"XDG_CONFIG_HOME": "/custom/config"}, Path("/unused")
        )
        self.assertEqual(desktop, Path("/custom/config/autostart/murmur.desktop"))

    def test_bootstrap_creates_xdg_env_not_source_env(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source"
            source.mkdir()
            (source / ".env.example").write_text("ANTHROPIC_API_KEY=\n")
            with patch.dict(os.environ, {"XDG_CONFIG_HOME": str(root / "config")}):
                config_dir = linux_bootstrap.install_config(source)

            self.assertTrue((config_dir / ".env").exists())
            self.assertFalse((source / ".env").exists())


if __name__ == "__main__":
    unittest.main()
