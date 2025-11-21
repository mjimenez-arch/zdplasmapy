# zdplasmapy Case Directory Structure

This repository contains input models and case studies for the zdplasmapy global plasma chemistry engine.

## Case Folders

- `cases/ashida1995/` — Argon discharge model (Ashida et al. 1995)
- `cases/chung1999/` — Oxygen ICP model (Chung et al. 1999)

Each case folder contains:
- `declarations.py` — Parameter and function definitions for the case
- `input.yaml` or `input.py` — Model configuration (YAML or Python)
- Any additional data or scripts required for the case

## Updating/Adding Cases
- Place new case folders in `cases/` with a clear, short name (e.g., `smith2020`)
- Update this README if you add or rename a case

## Example Usage
To run a case:
```bash
python main.py --config cases/chung1999/input.yaml
```
Or for Python input:
```bash
python main.py --input cases/chung1999/input.py
```

For more details, see the main project README and the documentation in each case folder.
