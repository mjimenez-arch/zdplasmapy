# Zero Dimensional Plasma Python (ZDPlasmaPy)

[![Python CI](https://github.com/mjimenez-arch/zdplasmapy/actions/workflows/python-ci.yml/badge.svg)](https://github.com/mjimenez-arch/zdplasmapy/actions/workflows/python-ci.yml)

**ZDPlasmaPy** is a flexible 0D global model for simulating low-temperature plasma chemistry. It is a refactored and modernized Python engine that solves coupled ordinary differential equations (ODEs) for particle and power balance.

## Features

-   **Flexible Engine:** Core global model is decoupled from chemistry definitions.
-   **Python-based Input:** Define complex chemistries in readable YAML and Python files.
-   **Robust Solver:** Uses `SciPy`'s stiff ODE solvers (BDF) for stability.
-   **EEDF Integration:** Couples with **LoKI-B** (Boltzmann solver) for non-Maxwellian electron energy distribution functions.
-   **Validation Ready:** Includes automated stoichiometry checks and reproduction of academic benchmarks (e.g., Chung 1999).

## Project Structure

```
zdplasmapy/
├── cases/              # Simulation cases (e.g., testArgon, testEEDF)
├── docs/               # Detailed documentation (Theory, EEDF, Dev Guide)
├── external/           # External dependencies (LoKI-B-cpp)
├── output/             # Simulation results and logs
├── scripts/            # Setup and utility scripts
├── src/                # Core source code
├── tests/              # Unit and integration tests
├── app.py              # Streamlit web interface
└── main.py             # Main entry point CLI
```

## Quick Start (Linux/WSL)

### 1. Prerequisites
You need **Python 3**, **Git**, and **CMake** (for building the Boltzmann solver).

### 2. Installation
We provide a helper script to setup the environment (install system dependencies, create venv, and build LoKI-B):

```bash
# Full setup (requires sudo for apt packages)
bash scripts/setup_wsl.sh
```

**Alternative (Manual Setup):**
If you prefer to manage your own environment:
1.  **System Config**: Install `cmake`, `g++`, `libeigen3-dev`, `nlohmann-json3-dev`.
2.  **Python Env**:
    ```bash
    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
    ```
3.  **Build Solver**:
    ```bash
    bash external/setup_loki_b.sh
    ```

### 3. Usage

Activate your environment and run a simulation case:

```bash
source .venv/bin/activate
python main.py cases/testArgon/config.yml
```

### 4. Running the Web App

To explore results interactively:

```bash
streamlit run app.py
```

## Documentation

-   [**Theory Guide**](docs/THEORY.md): Detailed physics and mathematical formulation.
-   [**EEDF Integration**](docs/EEDF_INTEGRATION.md): How the Boltzmann solver coupling is implemented.
-   [**Developer Guide**](docs/DEVELOPER_GUIDE.md): Tips for contributing and adding new cases.
-   [**Roadmap**](docs/ROADMAP.md): Future development plans.

---
*Disclaimer: This project is a research prototype developed with AI assistance focusing on workflow design and rapid prototyping.*
