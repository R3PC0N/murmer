#!/bin/bash
set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BOLD='\033[1m'
NC='\033[0m'

echo -e "${BOLD}Murmer — Linux Setup${NC}"
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
sudo apt-get update -qq
sudo apt-get install -y \
    python3-venv \
    python3-tk \
    xdotool \
    xclip \
    libportaudio2 \
    libappindicator3-1 \
    gir1.2-appindicator3-0.1

echo -e "${GREEN}✓ System packages installed${NC}"

# ── Virtual environment ───────────────────────────────────────────────────────
echo ""
echo "Creating virtual environment..."
python3 -m venv venv
echo -e "${GREEN}✓ venv created${NC}"

# ── Python packages ───────────────────────────────────────────────────────────
echo ""
echo "Installing Python packages (this may take a minute)..."
venv/bin/pip install --upgrade pip --quiet
venv/bin/pip install -r requirements.txt --quiet
echo -e "${GREEN}✓ Python packages installed${NC}"

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
    echo "  Murmer will use CUDA by default (large-v3 model)."
    echo "  Make sure the CUDA libraries are installed for faster-whisper."
else
    echo -e "${YELLOW}→ No NVIDIA GPU detected — Murmer will run on CPU.${NC}"
    echo "  Consider using the medium model in Settings → Transcription."
fi

# ── Launch script ─────────────────────────────────────────────────────────────
echo ""
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cat > murmer.sh << EOF
#!/bin/bash
cd "$SCRIPT_DIR"
exec ./venv/bin/python main.py "\$@"
EOF
chmod +x murmer.sh
echo -e "${GREEN}✓ Created launch script: murmer.sh${NC}"

# ── Done ──────────────────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}================================${NC}"
echo -e "${GREEN}Setup complete!${NC}"
echo ""
echo "Start Murmer with:"
echo -e "  ${BOLD}./murmer.sh${NC}"
echo ""

if [ -n "$NEED_RELOGIN" ]; then
    echo -e "${YELLOW}Remember: log out and back in first so the hotkey (input group) works.${NC}"
    echo ""
fi
