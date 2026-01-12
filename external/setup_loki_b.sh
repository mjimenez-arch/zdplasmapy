#!/bin/bash
# Setup script for LoKI-B-cpp installation

set -e  # Exit on error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOKI_DIR="$SCRIPT_DIR/LoKI-B-cpp"

echo "================================"
echo "LoKI-B-cpp Installation Script"
echo "================================"
echo ""

# Check for required dependencies
echo "Checking dependencies..."

if ! command -v git &> /dev/null; then
    echo "Error: git is not installed. Please install git first."
    exit 1
fi

if ! command -v cmake &> /dev/null; then
    echo "Error: cmake is not installed. Please install cmake first."
    exit 1
fi

if ! command -v g++ &> /dev/null; then
    echo "Error: g++ is not installed. Please install g++ first."
    exit 1
fi

echo "✓ All required dependencies found"
echo ""

# Clone repository if not already present
if [ -d "$LOKI_DIR" ]; then
    echo "LoKI-B-cpp directory already exists at: $LOKI_DIR"
    read -p "Do you want to update it? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "Updating LoKI-B-cpp..."
        cd "$LOKI_DIR"
        git pull
    fi
else
    echo "Cloning LoKI-B-cpp repository..."
    cd "$SCRIPT_DIR"
    git clone https://github.com/LoKI-Suite/LoKI-B-cpp.git
    cd "$LOKI_DIR"
fi

echo ""
echo "Choose backend for Eigen:"
echo "  1) Pure Eigen (default, no external BLAS)"
echo "  2) OpenBLAS (requires libopenblas-dev)"
echo "  3) Intel MKL (requires Intel MKL)"
echo ""
read -p "Enter choice (1-3) [default: 1]: " backend_choice

case $backend_choice in
    2)
        BACKEND_FLAG="-DLOKIB_USE_OPENBLAS=ON"
        echo "Building with OpenBLAS backend"
        ;;
    3)
        BACKEND_FLAG="-DLOKIB_USE_MKL=ON"
        echo "Building with Intel MKL backend"
        ;;
    *)
        BACKEND_FLAG=""
        echo "Building with pure Eigen (no external BLAS)"
        ;;
esac

# Detect number of cores
NUM_CORES=$(nproc 2>/dev/null || sysctl -n hw.ncpu 2>/dev/null || echo 4)
echo ""
echo "Detected $NUM_CORES CPU cores"

# Change to LoKI-B-cpp directory
cd "$LOKI_DIR"

# Check for Ninja
if command -v ninja &> /dev/null; then
    GENERATOR="-G Ninja"
    echo "Using Ninja build system for faster compilation"
else
    GENERATOR=""
    echo "Using Make build system (install ninja-build for faster compilation)"
fi

# Configure
echo ""
echo "Configuring build..."
cmake -DCMAKE_BUILD_TYPE=Release $BACKEND_FLAG $GENERATOR -B build

# Build
echo ""
echo "Building LoKI-B-cpp (using $NUM_CORES parallel jobs)..."
# Prefer building the main executable target explicitly if available
cmake --build build -j $NUM_CORES --target loki || cmake --build build -j $NUM_CORES

# Verify build: check common binary locations
LOKI_BIN=""
if [ -x "$LOKI_DIR/build/loki" ]; then
    LOKI_BIN="$LOKI_DIR/build/loki"
elif [ -x "$LOKI_DIR/build/bin/loki" ]; then
    LOKI_BIN="$LOKI_DIR/build/bin/loki"
elif [ -x "$LOKI_DIR/build/LoKI-B/loki" ]; then
    LOKI_BIN="$LOKI_DIR/build/LoKI-B/loki"
elif [ -x "$LOKI_DIR/build/app/loki" ]; then
    LOKI_BIN="$LOKI_DIR/build/app/loki"
fi

if [ -n "$LOKI_BIN" ]; then
    echo ""
    echo "================================"
    echo "✓ Build successful!"
    echo "================================"
    echo ""
    echo "LoKI-B binary location: $LOKI_BIN"
    echo ""
    echo "To use LoKI-B, run:"
    echo "  $LOKI_BIN <input_file>"
    echo ""
else
    echo ""
    echo "================================"
    echo "✗ Build failed!"
    echo "================================"
    echo ""
    echo "Please check the error messages above."
    exit 1
fi
