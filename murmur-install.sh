#!/bin/bash
# Murmur — Linux installer
# Downloads Murmur, extracts it to ~/murmur, and runs the setup script.
#
# Usage:
#   bash murmur-install.sh
#   curl -sSL https://murmurlabs.dev/downloads/murmur-install.sh | bash
set -e

VERSION="v1.2.1"
ZIP_URL="https://murmurlabs.dev/downloads/murmur-linux-$VERSION.zip"
INSTALL_DIR="$HOME/murmur"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BOLD='\033[1m'
NC='\033[0m'

echo -e "${BOLD}Murmur — Linux Installer${NC}"
echo "================================"
echo "Version : $VERSION"
echo "Location: $INSTALL_DIR"
echo ""

# ── Check dependencies ────────────────────────────────────────────────────
for cmd in curl unzip; do
    if ! command -v "$cmd" &>/dev/null; then
        echo -e "${RED}✗ '$cmd' is required. Install it with: sudo apt install $cmd${NC}"
        exit 1
    fi
done

# ── Download ──────────────────────────────────────────────────────────────
echo "Downloading Murmur $VERSION..."
TMP_ZIP=$(mktemp /tmp/murmur-XXXXXX.zip)
curl -L --progress-bar "$ZIP_URL" -o "$TMP_ZIP"
echo -e "${GREEN}✓ Downloaded${NC}"

# ── Extract ───────────────────────────────────────────────────────────────
echo ""
echo "Extracting..."
TMP_EXTRACT=$(mktemp -d /tmp/murmur-extract-XXXXXX)
unzip -q "$TMP_ZIP" -d "$TMP_EXTRACT"
rm "$TMP_ZIP"

# Zip contains a single top-level murmur/ folder
EXTRACTED="$TMP_EXTRACT/murmur"

if [ -d "$INSTALL_DIR" ]; then
    echo -e "${YELLOW}→ $INSTALL_DIR already exists — updating files in place.${NC}"
    cp -r "$EXTRACTED/." "$INSTALL_DIR/"
else
    mv "$EXTRACTED" "$INSTALL_DIR"
fi
rm -rf "$TMP_EXTRACT"
echo -e "${GREEN}✓ Extracted to $INSTALL_DIR${NC}"

# ── Run setup ─────────────────────────────────────────────────────────────
echo ""
cd "$INSTALL_DIR"
bash setup_linux.sh

# ── Done ──────────────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}================================${NC}"
echo -e "${GREEN}Installation complete!${NC}"
echo ""
echo "Start Murmur with:"
echo -e "  ${BOLD}$INSTALL_DIR/murmur.sh${NC}"
echo ""
echo "Or add this to your ~/.bashrc to launch from anywhere:"
echo -e "  ${BOLD}alias murmur='$INSTALL_DIR/murmur.sh'${NC}"
