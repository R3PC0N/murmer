#!/bin/bash
# Portable user-level bootstrap. System packages remain distro-managed; see README.md.
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "Murmur — portable Linux bootstrap"
echo "================================="

if ! command -v python3 >/dev/null 2>&1; then
    echo "ERROR: Python 3.10 or newer is required." >&2
    echo "Install the Python prerequisites listed for your distribution in README.md." >&2
    exit 1
fi

if ! python3 -c 'import sys; raise SystemExit(sys.version_info < (3, 10))'; then
    echo "ERROR: Python 3.10 or newer is required; found $(python3 --version 2>&1)." >&2
    exit 1
fi
echo "Python: $(python3 --version 2>&1)"

if [ ! -d .venv ]; then
    echo "Creating .venv with access to system GTK/PyGObject packages..."
    if ! python3 -m venv --system-site-packages .venv; then
        echo "ERROR: Python venv support is unavailable." >&2
        echo "Install the Python venv prerequisites listed in README.md, then rerun setup." >&2
        exit 1
    fi
else
    echo "Using existing .venv."
fi

if [ ! -x .venv/bin/python ]; then
    echo "ERROR: .venv/bin/python is missing or not executable." >&2
    exit 1
fi

echo "Installing Python dependencies..."
.venv/bin/python -m pip install -r requirements.txt

echo "Checking Linux desktop and audio capabilities..."
if ! .venv/bin/python linux_bootstrap.py check; then
    echo "Bootstrap stopped without changing system packages." >&2
    exit 1
fi

.venv/bin/python linux_bootstrap.py install-desktop \
    --app-dir "$SCRIPT_DIR" --python "$SCRIPT_DIR/.venv/bin/python"
.venv/bin/python linux_bootstrap.py install-config --app-dir "$SCRIPT_DIR"

cat > murmur.sh <<'EOF'
#!/bin/bash
set -e
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"
exec "$SCRIPT_DIR/.venv/bin/python" "$SCRIPT_DIR/main.py" "$@"
EOF
chmod +x murmur.sh

echo
echo "Setup complete. Start Murmur with:"
echo "  $SCRIPT_DIR/murmur.sh"
echo "It is also available as Murmur in normal XDG application launchers."
