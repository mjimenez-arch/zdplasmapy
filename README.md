# Python Global Plasma Model (GPMPy)

A flexible 0D global model for simulating low-temperature plasma chemistry, refactored from a legacy MATLAB code for improved robustness, flexibility, and testability.

This repository contains a Python-based engine for 0D (global) modeling of low-temperature plasmas. The engine solves a system of coupled ordinary differential equations for particle and power balance to determine the evolution of species densities and the electron temperature. The project demonstrates a complete refactoring of an older scientific code into a modern, modular, and maintainable software architecture.

![Example Oxygen Model Results](path/to/your/successful_oxygen_plot.png)
*(To add an image: take a screenshot of your successful Oxygen plot, save it in this folder, and replace the path above with the filename.)*

## Features

- **Flexible Engine:** The core `global_model.py` is a generic ODE solver engine, completely separate from the plasma physics.
- **Python-based Input:** Plasma chemistries are defined in separate, easy-to-read Python "recipe" files, allowing for syntax highlighting, version control, and unlimited complexity.
- **Robust Solver:** Utilizes the stiff ODE solver (`BDF`) from the SciPy library for numerical stability.
- **Self-Consistent Initialization:** Automatically calculates initial background gas density to be consistent with the specified pressure via the ideal gas law.
- **Built-in Diagnostics:** Includes an integrated stoichiometry debugger that generates a `stoichiometry_report.txt` file when in debug mode, allowing for easy verification of the reaction set.
- **Academic Accuracy:** The Oxygen model is a faithful implementation of the physics described in the paper by **Chung et al., J. Appl. Phys. 86, 3536 (1999)**.

## Theoretical Background

For a detailed explanation of the underlying physics and the mathematical formulation of the ODE system, please see the [**THEORY.md**](THEORY.md) document.

---

## Getting Started

### 1. Prerequisites
- Anaconda or Miniconda installed.
- `git` installed on your system.

### 2. Setup

First, clone the repository and set up the Conda environment.

```bash
# Clone the repository
git clone https://github.com/YourUsername/python-plasma-global-model.git
cd python-plasma-global-model

# Create a new Conda environment with all required packages
conda create -n plasma_env python=3.9 numpy scipy matplotlib

# Activate the environment
conda activate plasma_env
```

### 3. How to Run a Simulation

The simulation is controlled and executed from the `main.py` script.

**A. Configure the Simulation:**
Open `main.py` in an editor.
- **Choose the model:** Uncomment the desired `input_filename` to switch between Oxygen and Argon.
- **Toggle debug mode:** Set `debug=True` to generate detailed console output and the `stoichiometry_report.txt` file. Set to `False` for a clean run.

```python
# In main.py:
input_filename = 'input_models/final_model_input.py' # Oxygen Model
# input_filename = 'input_models/argon_model_input.py'   # Argon Model

model = GlobalModel(model_definition, debug=True)
```

**B. Run the Code:**
Execute the script from your terminal (make sure your `plasma_env` is active):

```bash
python main.py
```

The script will run the simulation and display plots of the species densities and electron temperature over time.

---

## Project Structure

- **`main.py`**: The main executable script to run a simulation.
- **`global_model.py`**: The core, generic plasma model engine.
- **`model_parser.py`**: Utility to load the Python-based input files.
- **`input_models/`**: Folder containing the chemistry "recipe" files.
  - `final_model_input.py`: Oxygen plasma model (Chung 1999).
  - `argon_model_input.py`: A basic Argon plasma model.
- **`THEORY.md`**: A detailed document explaining the underlying physics and equations.
