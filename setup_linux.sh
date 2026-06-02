#!/bin/bash
set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BOLD='\033[1m'
NC='\033[0m'

echo -e "${BOLD}Murmur — Linux Setup${NC}"
echo "================================"
echo ""

# ── Python version ────────────────────────────────────────────────────────────
PY_VERSION=$(python3 --version 2>&1 | grep -oP '\d+\.\d+' | head -1)
PY_MAJOR=$(echo "$PY_VERSION" | cut -d. -f1)
PY_MINOR=$(echo "$PY_VERSION" | cut -d. -f2)

if [ "$PY_MAJOR" -lt 3 ] || { [ "$PY_MAJOR" -eq 3 ] && [ "$PY_MINOR" -lt 10 ]; }; then
    echo -e "${RED}✗ Python 3.10+ is required. Found: $PY_VERSION${NC}"
    echo "  Install it with: sudo apt install python3.10"
    exit 1
fi
echo -e "${GREEN}✓ Python $PY_VERSION${NC}"

# ── System packages ───────────────────────────────────────────────────────────
echo ""
echo "Installing system packages..."
sudo apt-get update -qq || true  # ignore broken third-party PPAs
# Package names changed in Ubuntu 24.04
if apt-cache show libgirepository-2.0-dev &>/dev/null 2>&1; then
    GI_DEV_PKG="libgirepository-2.0-dev"
else
    GI_DEV_PKG="libgirepository1.0-dev"
fi

# WebKitGTK package name changed in Ubuntu 24.04 (4.0 → 4.1)
if apt-cache show libwebkit2gtk-4.1-dev &>/dev/null 2>&1; then
    WEBKIT_PKG="libwebkit2gtk-4.1-dev"
    WEBKIT_GIR="gir1.2-webkit2-4.1"
else
    WEBKIT_PKG="libwebkit2gtk-4.0-dev"
    WEBKIT_GIR="gir1.2-webkit2-4.0"
fi

# The two appindicator flavours conflict; pick whichever is already installed,
# or prefer the ayatana variant on systems that have neither.
if dpkg -l libappindicator3-1 2>/dev/null | grep -q '^ii'; then
    APPIND_PKGS="libappindicator3-1 gir1.2-appindicator3-0.1"
elif apt-cache show libayatana-appindicator3-1 &>/dev/null 2>&1; then
    APPIND_PKGS="libayatana-appindicator3-1 gir1.2-ayatanaappindicator3-0.1"
else
    APPIND_PKGS="libappindicator3-1 gir1.2-appindicator3-0.1"
fi

sudo apt-get install -y \
    build-essential \
    python3-venv \
    python3-tk \
    python3-dev \
    python3-gi \
    python3-gi-cairo \
    xdotool \
    xclip \
    libportaudio2 \
    $APPIND_PKGS \
    "$GI_DEV_PKG" \
    "$WEBKIT_PKG" \
    "$WEBKIT_GIR" \
    libcairo2-dev \
    gnome-shell-extension-appindicator

echo -e "${GREEN}✓ System packages installed${NC}"

# ── Virtual environment ───────────────────────────────────────────────────────
echo ""
echo "Creating virtual environment..."
# --system-site-packages lets the venv use the system python3-gi, which has
# proper access to system GI typelibs (AppIndicator3, etc). A pip-built
# PyGObject cannot reliably find them.
python3 -m venv venv --system-site-packages
echo -e "${GREEN}✓ venv created${NC}"

# ── Python packages ───────────────────────────────────────────────────────────
echo ""
echo "Installing Python packages (this may take a minute)..."
venv/bin/pip install --upgrade pip --quiet
venv/bin/pip install -r requirements.txt --quiet
echo -e "${GREEN}✓ Python packages installed${NC}"

# ── GNOME AppIndicator extension (tray icon) ──────────────────────────────────
echo ""
if command -v gnome-extensions &> /dev/null && [ -n "$DBUS_SESSION_BUS_ADDRESS" ]; then
    ENABLED=0
    # Try Zorin OS extension first, fall back to upstream
    for EXT_ID in "zorin-appindicator@zorinos.com" "appindicatorsupport@rgcjonas.gmail.com"; do
        if gnome-extensions list 2>/dev/null | grep -q "$EXT_ID"; then
            gnome-extensions enable "$EXT_ID" 2>/dev/null && ENABLED=1 && break
        fi
    done
    if [ "$ENABLED" -eq 1 ]; then
        echo -e "${GREEN}✓ AppIndicator extension enabled (tray icon will work)${NC}"
    else
        echo -e "${YELLOW}→ Could not enable AppIndicator extension automatically.${NC}"
        echo "  Enable it manually in GNOME Extensions or the Extensions app."
    fi
else
    echo -e "${YELLOW}→ AppIndicator extension check skipped (no GNOME session detected).${NC}"
    echo "  After setup, make sure the AppIndicator extension is enabled for the tray icon."
fi

# ── .env file ─────────────────────────────────────────────────────────────────
echo ""
if [ ! -f .env ]; then
    if [ -f .env.example ]; then
        cp .env.example .env
        echo -e "${YELLOW}→ .env created from .env.example"
        echo "  Open .env and add your ANTHROPIC_API_KEY if you want AI cleanup.${NC}"
    else
        echo "ANTHROPIC_API_KEY=" > .env
        echo -e "${YELLOW}→ .env created. Add your ANTHROPIC_API_KEY if you want AI cleanup.${NC}"
    fi
else
    echo -e "${GREEN}✓ .env already exists${NC}"
fi

# ── input group (global hotkeys) ──────────────────────────────────────────────
echo ""
if groups "$USER" | grep -q '\binput\b'; then
    echo -e "${GREEN}✓ Already in 'input' group${NC}"
else
    echo "Adding $USER to the 'input' group (required for global hotkeys)..."
    sudo usermod -aG input "$USER"
    echo -e "${YELLOW}→ You must log out and log back in for this to take effect.${NC}"
    NEED_RELOGIN=1
fi

# ── CUDA detection ────────────────────────────────────────────────────────────
echo ""
if command -v nvidia-smi &> /dev/null; then
    GPU=$(nvidia-smi --query-gpu=name --format=csv,noheader 2>/dev/null | head -1)
    echo -e "${GREEN}✓ NVIDIA GPU detected: $GPU${NC}"
    echo "  Murmur will use CUDA by default (large-v3 model)."
    echo "  Make sure the CUDA libraries are installed for faster-whisper."
else
    echo -e "${YELLOW}→ No NVIDIA GPU detected — writing CPU settings (medium model, int8).${NC}"
    # Write CPU-safe defaults to settings.json so the app doesn't try to load CUDA.
    if [ ! -f settings.json ]; then
        cat > settings.json << 'SETTINGS_EOF'
{
  "WHISPER_MODEL": "medium",
  "WHISPER_DEVICE": "cpu",
  "WHISPER_COMPUTE_TYPE": "int8"
}
SETTINGS_EOF
        echo -e "${GREEN}✓ settings.json written with CPU defaults.${NC}"
    else
        echo "  settings.json already exists — not overwriting."
        echo "  If Murmur fails to start, set WHISPER_DEVICE=cpu, WHISPER_MODEL=medium in Settings."
    fi
fi

# ── Launch script ─────────────────────────────────────────────────────────────
echo ""
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cat > murmur.sh << EOF
#!/bin/bash
cd "$SCRIPT_DIR"
exec ./venv/bin/python main.py "\$@"
EOF
chmod +x murmur.sh
echo -e "${GREEN}✓ Created launch script: murmur.sh${NC}"

# ── Done ──────────────────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}================================${NC}"
echo -e "${GREEN}Setup complete!${NC}"
echo ""
echo "Start Murmur with:"
echo -e "  ${BOLD}./murmur.sh${NC}"
echo ""

if [ -n "$NEED_RELOGIN" ]; then
    echo -e "${YELLOW}Remember: log out and back in first so the hotkey (input group) works.${NC}"
    echo ""
fi
