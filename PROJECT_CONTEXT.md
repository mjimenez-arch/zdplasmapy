# zdplasmapy Project Context

**Last Updated:** November 25, 2025  
**Purpose:** Comprehensive context for external AI assistants

---

## Project Overview

**zdplasmapy** is a scientific Python engine for 0D global plasma chemistry modeling. It solves stiff ODE systems for species densities and electron temperature in low-temperature plasmas.

**Repository:** github.com/mjimenez-arch/zdplasmapy  
**Current Branch:** `feature/publication-centric-refactor`  
**Python Version:** 3.13  
**License:** MIT

---

## Core Architecture

### Main Components

1. **`global_model.py`** - Core ODE solver using `scipy.integrate.solve_ivp` (BDF method)
   - Solves particle balance and electron energy equations
   - Handles power deposition, flow, and wall losses
   - Outputs time-resolved diagnostics

2. **`src/chemistry_parser.py`** - Parses `chemistry.yml` files
   - Converts string expressions to Python callables using **AST validation** (security-hardened)
   - Builds rate coefficient and energy loss functions
   - **Important:** Uses AST whitelist to prevent RCE; never use raw `eval()`

3. **`src/config_parser.py`** - Validates case configuration files
   - JSON Schema validation via `jsonschema`
   - Optional Jinja2 templating support
   - Outputs [OK]/[FAIL] validation messages (ASCII for Windows compatibility)

4. **`main.py`** - CLI entry point
   - Loads YAML cases from `cases/<case_name>/`
   - Runs simulation and saves results to `output/`

5. **`app.py`** - Streamlit web interface (optional)

### File Structure

```
zdplasmapy/
├── global_model.py          # Core solver
├── main.py                  # CLI runner
├── app.py                   # Streamlit UI
├── src/
│   ├── chemistry_parser.py  # YAML → callables (AST-validated)
│   ├── config_parser.py     # Config validation
│   └── eedf_solver.py       # EEDF solver abstraction (NEW, scaffold only)
├── cases/
│   ├── chung1999/           # Oxygen discharge (current test benchmark)
│   │   ├── chemistry.yml
│   │   └── config.yml
│   └── ashida1995/          # Argon discharge (legacy)
├── tests/
│   ├── test_parser.py                      # Chemistry parsing tests
│   └── test_chemistry_parser_security.py   # Security hardening tests
├── external/
│   └── loki-b/
│       └── README.md        # LOKI-B build instructions (only tracked file)
└── .gitignore               # Ignores external/loki-b/* except README
```

---

## Critical Conventions

### Chemistry Configuration (`chemistry.yml`)

**Species List:**
```yaml
species:
  - O2      # Background gas (ALWAYS first)
  - O2+
  - O
  - O+
  - O-
  - e       # Electrons (symbol: 'e')
```
- **Order matters:** Background gas first, electrons typically last
- **Naming:** May include charges (`O2+`, `O-`); parser matches longest names first

**Reaction Syntax:**
```yaml
reactions:
  - formula: "e + O2 -> O2+ + 2 e"
    rate_coefficient: "2.34e-14 * exp(-12.06 / Te)"  # Te = electron temp (eV)
    energy_loss: "12.06"
```
- **Formula rules:** `reactants -> products`, terms separated by ` + ` (spaces required)
- **Expression shortcuts:** `Te` → `p['Te_eV']`, `Tg` → `p['Tg_K']`
- **Allowed functions:** `math.exp`, `math.sqrt`, `math.log`, `p.get()`, `p[...]` subscripts
- **Forbidden:** Imports, arbitrary attributes, `eval`, `exec`, `__builtins__`

**Mass Constants:**
```yaml
constant_data:
  mass_O2: 5.31e-26   # kg (species name without +/-)
  mass_O: 2.66e-26
```

### Configuration File (`config.yml`)

**Required Sections:**
```yaml
geometry:
  type: "cylinder"
  characteristic_length: 0.05  # meters

initial_conditions:
  Te_eV: 2.0
  n_e: 1e16  # m^-3
  n_O2: 2.7e22  # background density

solver:
  t_end: 1e-3  # seconds
  rtol: 1e-6
  atol: 1e-8
```

---

## Recent Changes (Security Fix)

### Vulnerability Patched (November 2025)
**Issue:** `chemistry_parser.py` used `eval()` to convert string expressions → RCE vulnerability  
**Fix:** Replaced with AST-based validation  
**Status:** ✅ Complete, 15/15 tests passing

**Security Implementation:**
```python
def _build_lambda(expr: str, param_name: str = 'p'):
    """Convert string expression to callable using AST validation."""
    # Replace shortcuts
    expr = expr.replace('Te', f"{param_name}['Te_eV']")
    expr = expr.replace('Tg', f"{param_name}['Tg_K']")
    
    # Parse and validate AST
    tree = ast.parse(expr, mode='eval')
    _validate_ast(tree)  # Whitelist-based security check
    
    # Compile with empty builtins
    code = compile(tree, '<string>', 'eval')
    return lambda p: eval(code, {"__builtins__": {}, "math": math}, {param_name: p})
```

**Whitelist:**
- Arithmetic: `+`, `-`, `*`, `/`, `**`, `//`, `%`
- Functions: `math.exp()`, `math.sqrt()`, `math.log()`
- Data access: `p[...]`, `p.get(...)`
- Blocked: `__import__`, attribute chains (except `p.get`), arbitrary functions

**Test Coverage:**
- `test_chemistry_parser_security.py` (8 tests)
- Validates allowed syntax (Te shortcuts, math functions, p.get)
- Rejects malicious code (imports, attribute access, exec)

---

## Current Development Focus

### LOKI-B EEDF Solver Integration (In Progress)

**Goal:** Replace Maxwellian rate coefficients with Boltzmann solver results

**Status:** 🔄 Scaffolded (structure only, not functional)

**Files Created:**
- `src/eedf_solver.py` - Solver abstraction layer
  - `EEDFSolver` base class
  - `LokiBSolver` subprocess wrapper (placeholders)
  - `MaxwellianSolver` fallback
  - `get_solver()` factory
- `external/loki-b/README.md` - Build/integration guide

**Pending Implementation:**
1. LOKI-B input file generator (`_generate_input_file()`)
2. Output parser (`_parse_output()`)
3. Config schema extension (optional `eedf:` section)
4. Chemistry parser integration (detect `eedf: true` flag)
5. Cross-section file management strategy

**External Dependency:**
- LOKI-B: C++ Boltzmann solver ([GitHub](https://github.com/IST-Lisbon/loki-b-cpp))
- Requires CMake build, placed in `bin/loki-b` (ignored by git)
- Uses LXCat cross-section files (not yet tracked)

---

## Testing Conventions

**Run Tests:**
```powershell
python -m unittest discover -s tests -p "test_*.py" -v
```

**Current Benchmark:**
- **Case:** `chung1999` (oxygen discharge)
- **Chemistry:** 6 species (O2, O2+, O, O+, O-, e)
- **Previous:** `ashida1995` (argon) - deprecated for tests

**Key Test Files:**
- `test_parser.py` - Species order, stoichiometry validation
- `test_chemistry_parser_security.py` - RCE prevention

**Expected Species Order (chung1999):**
```python
['O2', 'O2+', 'O', 'O+', 'O-', 'e']
```

---

## Solver Details

**ODE Method:** `scipy.integrate.solve_ivp` with `method='BDF'` (stiff solver)  
**Tolerances:** `rtol=1e-6`, `atol=1e-8`  
**State Vector:** `[n_species1, n_species2, ..., Te_eV]`

**Debug Mode:**
```python
GlobalModel(..., debug=True)
```
- Writes `stoichiometry_report.txt`
- Prints stepwise diagnostics during integration

---

## Running Simulations

**CLI:**
```powershell
python main.py
```
Edit `main.py` to set `case_name = 'chung1999'` or other case folder.

**Streamlit UI:**
```powershell
streamlit run app.py
```

**Output Location:** `output/<case_name>/`

---

## Git Workflow

**Feature Branches:**
- `feature/publication-centric-refactor` (current)
- `feature/loki-b-eedf-integration` (LOKI-B work)

**PR Guidelines:**
- Small fixes: direct commit
- Numerical changes: require justification + regression test + example output

**CI:** GitHub Actions auto-discovers tests

---

## Dependencies

**Core:**
- `scipy` - ODE solver
- `numpy` - Array operations
- `pyyaml` - Config file parsing
- `jsonschema` - Config validation

**Optional:**
- `streamlit` - Web UI
- `jinja2` - Config templating

**External (not packaged):**
- LOKI-B executable (C++, user builds separately)

---

## Common Pitfalls

1. **Species reordering breaks tests** - Background gas must be first
2. **Reaction formula spacing** - Use ` + ` (with spaces) not `+`
3. **Mass constant naming** - Strip charges: `mass_O2+` → `mass_O2`
4. **Windows encoding** - Use ASCII [OK]/[FAIL] not Unicode ✓/✗
5. **Never use `eval()`** - Always validate with AST first
6. **Solver API changes** - Update tests and benchmarks if modifying solve_ivp calls

---

## Next Steps (Pending Work)

**High Priority:**
- [ ] Commit security fix to feature branch
- [ ] Implement LOKI-B input generator
- [ ] Implement LOKI-B output parser

**Medium Priority:**
- [ ] Extend config schema for EEDF section
- [ ] Integrate EEDF solver into chemistry parser
- [ ] Document cross-section file strategy

**Low Priority:**
- [ ] Fix f-string cosmetic warning (line 52, config_parser.py)
- [ ] Add more test cases (different chemistries)

---

## Example: Loading a Model

```python
from src.chemistry_parser import load_chemistry
from src.config_parser import load_config

# Load case
chemistry = load_chemistry('cases/chung1999/chemistry.yml')
config = load_config('cases/chung1999/config.yml')

# Extract species and reactions
species = chemistry['species']  # ['O2', 'O2+', 'O', 'O+', 'O-', 'e']
reactions = chemistry['reactions']  # List of dicts

# Each reaction has:
# - 'formula': str
# - 'rate_coeff_func': callable(p) -> float
# - 'energy_loss_func': callable(p) -> float
```

---

## Contact & Documentation

**Main Docs:**
- `README.md` - Installation and quick start
- `THEORY.md` - Mathematical model equations
- `ROADMAP.md` - Feature planning
- `.github/copilot-instructions.md` - Copilot-specific guidance

**Developer:** mjimenez-arch  
**Issues:** Use GitHub Issues for bugs/features

---

## Quick Reference: Key Functions

| Function | Location | Purpose |
|----------|----------|---------|
| `load_chemistry()` | `src/chemistry_parser.py` | Parse chemistry.yml → dict |
| `load_config()` | `src/config_parser.py` | Validate config.yml → dict |
| `_build_lambda()` | `src/chemistry_parser.py` | String expr → callable (AST-validated) |
| `GlobalModel.solve()` | `global_model.py` | Run ODE integration |
| `get_solver()` | `src/eedf_solver.py` | Get EEDF solver instance |

---

## Version History

- **v0.3 (Nov 2025):** Security hardening (AST validation), LOKI-B scaffold
- **v0.2:** Multi-case YAML support, Streamlit UI
- **v0.1:** Initial global model implementation

---

**End of Context Document**

_This document summarizes the state as of November 25, 2025. For live updates, check the repository._
