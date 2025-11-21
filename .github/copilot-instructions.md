# Copilot Instructions for zdplasmapy

**Project Overview**
- Scientific Python engine for 0D plasma chemistry modeling.
- Core: `global_model.py` (ODE solver, stiff chemistry, diagnostic output).
- Inputs: Python or YAML "recipe" files (see `input_models/` and `cases/`).
- Main runner: `main.py` (CLI), `app.py` (Streamlit UI).

**Key Workflows**
- Run a simulation:  
  `python main.py` (edit `input_filename` or `config_path` to select model/case).
- Run web UI:  
  `streamlit run app.py`
- Debug mode:  
  `GlobalModel(..., debug=True)` writes `stoichiometry_report.txt` and prints stepwise diagnostics.
- Tests:  
  `python -m unittest tests/test_parser.py` (species order and stoichiometry checks).

**Input Model Conventions**
- Python input: must expose `get_model_definition()` returning a dict with:
  - `species`: ordered list (background gas first, electrons as `'e'`).
  - `reactions`: list of dicts (`formula`, `rate_coeff_func`, `energy_loss_func`).
  - `geometry`, `constant_data`, `declarations_func`, `initial_values`, `time_settings`.
  - Optional: `flow_parameters`, `power_input_func`.
- YAML input: use `build_model_definition(config_path)` (see `main.py`).

**Patterns & Pitfalls**
- Reaction formulas: `'reactants -> products'`, terms separated by `' + '` (spaces matter).
- Species names: may include charge (`O2+`, `O-`); parser matches longest names first.
- Mass constants: keys in `constant_data` as `mass_<SpeciesName>` (strip `+`/`-`).
- Solver: `scipy.integrate.solve_ivp` with `method='BDF'`, `rtol=1e-6`, `atol=1e-8`.
- Do not reorder `species` or change solver API without updating tests and benchmarks.

**Examples**
- Model loader:  
  `model_definition = load_input_file('input_models/oxygen.py')`
- Reaction dict:  
  ```python
  {
    'formula': 'e + O2 -> O2+ + 2 e',
    'rate_coeff_func': lambda params: ...,
    'energy_loss_func': lambda params: ...
  }
  ```
- Test expectations:  
  Species order in `input_models/oxygen.py` is `['O2','O2+','O','O+','O-','e']`.

**PR Guidance**
- Small fixes: direct commit.
- Changes to numerical behavior: require justification, regression test, and example output.

---
If you want more examples or stricter rules, let me know which files or workflows to expand.