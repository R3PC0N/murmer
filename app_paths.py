"""Platform paths and backward-compatible Linux XDG migration helpers."""

import os
import stat
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from collections.abc import Mapping


@dataclass(frozen=True)
class LinuxPaths:
    config: Path
    data: Path
    state: Path
    runtime: Path


def linux_paths(
    environ: Mapping[str, str] | None = None,
    home: Path | None = None,
    uid: int | None = None,
    temp_dir: Path | None = None,
) -> LinuxPaths:
    environ = os.environ if environ is None else environ
    home = Path.home() if home is None else Path(home)
    uid = os.getuid() if uid is None else uid
    temp_dir = Path(tempfile.gettempdir()) if temp_dir is None else Path(temp_dir)

    config_home = Path(environ.get("XDG_CONFIG_HOME", home / ".config"))
    data_home = Path(environ.get("XDG_DATA_HOME", home / ".local/share"))
    state_home = Path(environ.get("XDG_STATE_HOME", home / ".local/state"))
    runtime_home = environ.get("XDG_RUNTIME_DIR")
    runtime = (
        Path(runtime_home) / "murmur"
        if runtime_home
        else temp_dir / f"murmur-runtime-{uid}"
    )
    return LinuxPaths(
        config=config_home / "murmur",
        data=data_home / "murmur",
        state=state_home / "murmur",
        runtime=runtime,
    )


def ensure_private_directory(path: Path) -> Path:
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    info = path.lstat()
    if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
        raise RuntimeError(f"Murmur private path is not a directory: {path}")
    if hasattr(os, "getuid") and info.st_uid != os.getuid():
        raise RuntimeError(f"Murmur private path is not owned by the current user: {path}")
    path.chmod(0o700)
    return path


def runtime_directory(**kwargs) -> Path:
    return ensure_private_directory(linux_paths(**kwargs).runtime)


def migrate_file(source: Path, destination: Path, mode: int = 0o600) -> bool:
    """Copy a legacy file once, leaving it untouched and never replacing XDG data."""
    if destination.exists() or not source.is_file():
        return False
    destination.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    destination.parent.chmod(0o700)
    payload = source.read_bytes()
    try:
        descriptor = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL, mode)
    except FileExistsError:
        return False
    try:
        with os.fdopen(descriptor, "wb") as output:
            output.write(payload)
            output.flush()
            os.fsync(output.fileno())
        destination.chmod(mode)
    except Exception:
        try:
            destination.unlink()
        except FileNotFoundError:
            pass
        raise
    return True


def atomic_write_text(path: Path, text: str, mode: int = 0o600) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    path.parent.chmod(0o700)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        os.fchmod(descriptor, mode)
        with os.fdopen(descriptor, "w", encoding="utf-8") as output:
            output.write(text)
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, path)
        path.chmod(mode)
    except Exception:
        try:
            os.close(descriptor)
        except OSError:
            pass
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass
        raise


def initialize_linux_config(source_dir: Path, **kwargs) -> LinuxPaths:
    paths = linux_paths(**kwargs)
    migrate_file(source_dir / "settings.json", paths.config / "settings.json")
    migrate_file(source_dir / ".env", paths.config / ".env")
    return paths


def initialize_linux_logs(
    home: Path | None = None,
    environ: Mapping[str, str] | None = None,
    **kwargs,
) -> LinuxPaths:
    paths = linux_paths(environ=environ, home=home, **kwargs)
    legacy = (Path.home() if home is None else Path(home)) / ".local/share/Murmur"
    ensure_private_directory(paths.data)
    ensure_private_directory(paths.state)
    migrate_file(legacy / "history.log", paths.data / "history.log")
    migrate_file(legacy / "startup.log", paths.state / "startup.log")
    return paths


def config_files(
    source_dir: Path,
    platform: str | None = None,
    **kwargs,
) -> tuple[Path, Path, Path, Path]:
    """Return settings/env destinations followed by their legacy paths."""
    platform = sys.platform if platform is None else platform
    legacy_settings = source_dir / "settings.json"
    legacy_env = source_dir / ".env"
    if platform == "win32":
        return legacy_settings, legacy_env, legacy_settings, legacy_env
    paths = linux_paths(**kwargs)
    return paths.config / "settings.json", paths.config / ".env", legacy_settings, legacy_env


def instance_lock_path(**kwargs) -> Path:
    return runtime_directory(**kwargs) / "instance.lock"
