import ast
import tempfile
import unittest
from pathlib import Path

import linux_bootstrap


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "linux_runtime_files.txt"


def runtime_project_files() -> set[str]:
    """Follow project-local imports from main.py without importing the app."""
    found = set()
    pending = ["main.py"]
    while pending:
        relative = pending.pop()
        if relative in found:
            continue
        found.add(relative)
        tree = ast.parse((ROOT / relative).read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            names = []
            if isinstance(node, ast.Import):
                names = [alias.name.split(".", 1)[0] for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                names = [node.module.split(".", 1)[0]]
            for name in names:
                candidate = f"{name}.py"
                if (ROOT / candidate).is_file() and candidate not in found:
                    pending.append(candidate)
    return found


class PackagingManifestTests(unittest.TestCase):
    def test_manifest_contains_all_runtime_project_imports(self):
        packaged = {
            line.strip() for line in MANIFEST.read_text().splitlines() if line.strip()
        }
        self.assertEqual(runtime_project_files() - packaged, set())
        self.assertIn("hotkeys.py", packaged)

    def test_manifest_entries_exist_and_builder_consumes_manifest(self):
        entries = [
            line.strip() for line in MANIFEST.read_text().splitlines() if line.strip()
        ]
        self.assertTrue(all((ROOT / entry).is_file() for entry in entries))
        builder = (ROOT / "build_linux_zip.ps1").read_text(encoding="utf-8")
        self.assertIn('Get-Content "$src\\linux_runtime_files.txt"', builder)
        self.assertIn('"$src\\linux_bootstrap.py"', builder)
        self.assertIn('"$src\\README.md"', builder)

    def test_portable_setup_does_not_manage_system_packages_or_permissions(self):
        setup = (ROOT / "setup_linux.sh").read_text(encoding="utf-8")
        for forbidden in (
            "sudo", "apt-get", "apt-cache", "dpkg", "pacman", "usermod",
            "nvidia-smi", "gnome-extensions",
        ):
            self.assertNotIn(forbidden, setup)


class CapabilitySelectionTests(unittest.TestCase):
    def missing(self, environment, available):
        return linux_bootstrap.missing_executables(
            environment,
            which=lambda name: f"/usr/bin/{name}" if name in available else None,
        )

    def test_wayland_requires_wtype_but_not_xdotool(self):
        environment = {"XDG_SESSION_TYPE": "wayland", "WAYLAND_DISPLAY": "wayland-1"}
        self.assertEqual(self.missing(environment, {"xdg-open"}), ["wtype"])

    def test_hyprland_also_requires_hyprctl(self):
        environment = {
            "XDG_SESSION_TYPE": "wayland",
            "WAYLAND_DISPLAY": "wayland-1",
            "XDG_CURRENT_DESKTOP": "Hyprland",
        }
        self.assertEqual(self.missing(environment, {"xdg-open", "wtype"}), ["hyprctl"])

    def test_x11_requires_xdotool_but_not_wayland_tools(self):
        environment = {"XDG_SESSION_TYPE": "x11", "DISPLAY": ":0"}
        self.assertEqual(self.missing(environment, {"xdg-open"}), ["xdotool"])


class DesktopEntryTests(unittest.TestCase):
    def test_desktop_entry_is_visible_and_paths_are_quoted(self):
        entry = linux_bootstrap.render_desktop_entry(
            Path('/opt/Murmur $app/.venv/bin/python'),
            Path('/opt/Murmur $app/main.py'),
        )
        self.assertNotIn("NoDisplay=true", entry)
        self.assertIn("Terminal=false", entry)
        self.assertIn('Exec="/opt/Murmur \\$app/.venv/bin/python"', entry)
        self.assertIn('"/opt/Murmur \\$app/main.py"', entry)

    def test_install_honors_xdg_data_home(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            app = root / "Murmur app"
            app.mkdir()
            (app / "main.py").touch()
            (app / "murmur.svg").write_text("<svg/>")
            venv_python = app / ".venv/bin/python"
            venv_python.parent.mkdir(parents=True)
            venv_python.symlink_to("/usr/bin/python3")
            desktop = linux_bootstrap.install_desktop_entry(
                app,
                venv_python,
                {"XDG_DATA_HOME": str(root / "data")},
            )
            text = desktop.read_text()

        self.assertEqual(desktop, root / "data/applications/murmur.desktop")
        self.assertIn(f'Exec="{venv_python.absolute()}"', text)
        self.assertIn(f'"{app.resolve()}/main.py"', text)


if __name__ == "__main__":
    unittest.main()
