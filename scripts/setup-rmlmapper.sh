#!/bin/bash
# Download RMLMapper JAR for RML validation
# Usage: ./scripts/setup-rmlmapper.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
TOOLS_DIR="$PROJECT_DIR/tools"
JAR_PATH="$TOOLS_DIR/rmlmapper.jar"

# Check Java is available
if ! command -v java &> /dev/null; then
    echo "Error: Java is not installed or not in PATH."
    echo "RMLMapper requires Java 11 or later."
    echo "Install it with: sudo apt install default-jre  (Debian/Ubuntu)"
    echo "                  brew install openjdk          (macOS)"
    exit 1
fi

JAVA_VERSION=$(java -version 2>&1 | head -n 1)
echo "Found Java: $JAVA_VERSION"

# Create tools directory
mkdir -p "$TOOLS_DIR"

# Check if JAR already exists
if [ -f "$JAR_PATH" ]; then
    echo "RMLMapper JAR already exists at $JAR_PATH"
    echo "Delete it first if you want to re-download."
    exit 0
fi

echo "Downloading latest RMLMapper..."

# Get latest release download URL from GitHub API
DOWNLOAD_URL=$(curl -s https://api.github.com/repos/RMLio/rmlmapper-java/releases/latest \
    | grep "browser_download_url.*-all.jar" \
    | head -n 1 \
    | cut -d '"' -f 4)

if [ -z "$DOWNLOAD_URL" ]; then
    echo "Error: Could not determine download URL from GitHub releases."
    echo "Please download manually from:"
    echo "  https://github.com/RMLio/rmlmapper-java/releases"
    exit 1
fi

echo "  URL: $DOWNLOAD_URL"
curl -L -o "$JAR_PATH" "$DOWNLOAD_URL"

# Verify download
if [ ! -f "$JAR_PATH" ]; then
    echo "Error: Download failed."
    exit 1
fi

FILE_SIZE=$(stat -c%s "$JAR_PATH" 2>/dev/null || stat -f%z "$JAR_PATH" 2>/dev/null)
echo "  Size: $FILE_SIZE bytes"

echo ""
echo "RMLMapper downloaded successfully to $JAR_PATH"
echo "Configuration in config/config.yaml is already set to use this path."
