# External Dependencies

This directory contains external dependencies for zdplasmapy.

## LoKI-B-cpp

LoKI-B is a Boltzmann equation solver for electron kinetics in low-temperature plasmas.

### Installation

Run the setup script to clone and compile LoKI-B-cpp:

```bash
cd external
./setup_loki_b.sh
```

Or follow the manual steps below.

### Manual Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/LoKI-Suite/LoKI-B-cpp.git
   cd LoKI-B-cpp
   ```

2. Build (Linux):
   ```bash
   # Option 1: Build with OpenBLAS backend
   cmake -DCMAKE_BUILD_TYPE=Release -DLOKIB_USE_OPENBLAS=ON -B build
   
   # Option 2: Build with Intel MKL backend
   cmake -DCMAKE_BUILD_TYPE=Release -DLOKIB_USE_MKL=ON -B build
   
   # Option 3: Build with pure Eigen (no backend flag)
   cmake -DCMAKE_BUILD_TYPE=Release -B build
   
   # Then compile (adjust -j flag to your CPU core count)
   cmake --build build -j 4
   ```

3. The compiled binary will be available at `LoKI-B-cpp/build/loki`

### Using Nix (Alternative)

If you have Nix installed:

```bash
# Development shell with dependencies
nix develop

# Build all binaries
nix build

# Run without cloning
nix run github:loki-suite/loki-b-cpp <input_file>
```

### Dependencies

- Git
- CMake
- C/C++ compiler (gcc/g++)
- Eigen (for linear algebra) - fetched automatically
- nlohmann-json (for JSON handling) - fetched automatically
- Optional: OpenBLAS or Intel MKL for better performance

### Testing LoKI-B

After a successful build, you can run the project's tests with CTest. Depending on the build layout, invoking ctest from specific subdirectories works best:

```bash
# From the build root, you can list tests
cd /root/projects/zdplasmapy/external/LoKI-B-cpp/build
ctest -N

# Run tests registered under the tests directory
ctest --test-dir /root/projects/zdplasmapy/external/LoKI-B-cpp/build/tests --output-on-failure -j 16

# Run tests registered under the ideas directory
ctest --test-dir /root/projects/zdplasmapy/external/LoKI-B-cpp/build/ideas --output-on-failure -j 16
```

If ctest from the build root shows no tests, use the `--test-dir` commands above.
