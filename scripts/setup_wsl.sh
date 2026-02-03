#!/bin/bash
# WSL Development Environment Setup for zdplasmapy
# Run from WSL terminal: bash scripts/setup_wsl.sh

set -e  # Exit on error

echo "=== zdplasmapy WSL Setup ==="
echo ""

# 1. Update package lists
echo "[1/6] Updating package lists..."
sudo apt update

# 2. Install build tools and dependencies
echo "[2/6] Installing build tools (CMake, GCC, etc.)..."
sudo apt install -y build-essential cmake git

echo "[3/6] Installing LoKI-B dependencies (Eigen, nlohmann-json)..."
sudo apt install -y libeigen3-dev nlohmann-json3-dev

# 3. Install Python and venv
echo "[4/6] Installing Python 3 and venv..."
sudo apt install -y python3 python3-venv python3-pip

# 4. Create Python virtual environment
echo "[5/6] Creating Python virtual environment..."
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
    echo "Virtual environment created at .venv"
else
    echo "Virtual environment already exists, skipping..."
fi

# 5. Activate venv and install Python dependencies
echo "[6/6] Installing Python dependencies..."
source .venv/bin/activate
pip install --upgrade pip
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
else
    echo "Warning: requirements.txt not found, skipping pip install"
fi

# 6. Build LoKI-B using the external setup script
if [ -f "external/setup_loki_b.sh" ]; then
    echo ""
    echo "=== Running LoKI-B Setup ==="
    # Make executable just in case
    chmod +x external/setup_loki_b.sh
    # Execute the script
    ./external/setup_loki_b.sh
else
    echo "Warning: external/setup_loki_b.sh not found. Skipping LoKI-B build."
fi

# 7. Configure git if needed
echo ""
echo "=== Git Configuration ==="
if ! git config --global user.name > /dev/null 2>&1; then
    echo "Git user.name not set. Configure with:"
    echo "  git config --global user.name \"Your Name\""
    echo "  git config --global user.email \"your.email@example.com\""
else
    echo "✓ Git configured: $(git config --global user.name) <$(git config --global user.email)>"
fi

# Set autocrlf for cross-platform compatibility
git config --global core.autocrlf input
echo "✓ Git autocrlf set to 'input' for Linux line endings"

echo ""
echo "=== Setup Complete ==="
echo ""
echo "Next steps:"
echo "  1. Activate venv:      source .venv/bin/activate"
echo "  2. Run tests:          python -m unittest discover -s tests -p 'test_*.py' -v"
echo "  3. Run simulation:     python main.py"
echo ""
echo "LoKI-B executable (if built): external/loki-b/LoKI-B-cpp/build/app/loki"
echo ""
