# zdplasmapy Project Roadmap

This document outlines the strategic vision and planned development phases for the `zdplasmapy` suite. The goal is to evolve this project from a simple 0D solver into a comprehensive, interactive tool for plasma chemistry research and exploration.

---

### Phase 1: Readability & Interactivity Refactor

*Goal: To build a flexible foundation and deliver a powerful interactive simulation tool.*

-   [ ] **Refactor Input Format:** Introduce `Species` and `Reaction` classes to create a cleaner, object-oriented "recipe" format.
-   [ ] **Modularize Transport Physics:** Create a `transport_models.py` library to allow for pluggable transport equations (e.g., Chung 1999, Simple Diffusion).
-   [ ] **Prototype Interactive Simulator:** Build the "real-time" `app.py` with sliders for power/pressure/flow and a run/pause capability to explore plasma dynamics like hysteresis.

---

### Phase 2: High-Fidelity Physics & Chemistry

*Goal: To significantly improve the physical accuracy of the model by integrating a Boltzmann solver and building a robust chemistry management system.*

-   [ ] **Develop `bifrost` (LoKI-B Wrapper):** Create the Python wrapper for the compiled LoKI-B C++ executable. Its purpose is to take a gas mixture and E/N as input and return EEDF-consistent rate coefficients.
-   [ ] **Implement Hybrid Solver Mode:** Upgrade the `zdplasmapy` engine to use `bifrost`. Create lookup tables mapping mean electron energy (`<ε>`) to the accurate rate coefficients from LoKI-B, replacing the simple Arrhenius fits.
-   [ ] **Implement CSV-based Chemistry:** Create a loader to define entire reaction sets in easy-to-edit `.csv` files, enabling the management of very large chemistries.
-   [ ] **Develop GUI Chemistry Mixer:** Add UI elements to the web app to interactively select and combine different chemistry files.

---

### Phase 3: Automated Science & Performance

*Goal: To enable large-scale data generation through automation and performance enhancements.*

-   [ ] **Build Parametric Study Tool:** Create a script (`run_study.py`) to automate running the model over large parameter grids and save the results.
-   [ ] **Implement GPU Acceleration:** Explore using libraries like `CuPy` (for NumPy operations) and potentially GPU-accelerated ODE solvers (from `JAX` or `Numba`) to dramatically speed up large parametric studies.
-   [ ] **Build Advanced Visualization Tool:** Create a script (`plot_study_results.py`) to generate 2D contour plots from the now much larger parametric study datasets.
-   [ ] **Implement Validation Workflow:** Create a `validate.py` script to automatically compare simulation results against experimental data, calculate the error, and integrate with Git/MLflow to track the impact of chemistry changes.

---

### Phase 4: The Intelligent Predictor

*Goal: To integrate machine learning for instant predictions and intelligent initialization.*

-   [ ] **Train a Surrogate ML Model:** Use the massive, GPU-accelerated parametric study data to train a high-accuracy neural network.
-   [ ] **Build "Ignition Domain Mapper":** Run specialized studies to map the basin of attraction for plasma ignition and train a classification model.
-   [ ] **Integrate ML into GUI:** Power the interactive sliders with the fast ML model for real-time predictions and add a "Verify with Full Model" button.
-   [ ] **Use ML for Smart Initialization:** Use the ML model's predictions to provide better initial guesses for the 0D, 1D, or 2D solvers.
