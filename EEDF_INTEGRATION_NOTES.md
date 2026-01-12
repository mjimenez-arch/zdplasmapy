# EEDF Rate Coefficient Integration - Implementation Summary

## Changes Made

### 1. Enhanced LoKI-B Output Parsing (`src/eedf_solver.py`)
- Extended `_parse_loki_json_output()` to extract rate coefficients from LoKI-B JSON output
- Now returns `rate_coefficients` dict alongside EEDF and energy grid
- Added swarm parameters and power balance to diagnostics

### 2. Added Rate Coefficient Lookup (`src/global_model.py`)
- New method `_get_eedf_rate_coefficient(reaction, t)` retrieves rates from EEDF results
- Uses nearest timestamp matching for temporal lookup
- Matches reactions by `process_id` from chemistry file

### 3. Integrated EEDF Rates into ODE Solver (`src/global_model.py`)
- Modified rate calculation loop to check `use_eedf` flag
- Reactions marked `use_eedf=True` now use LoKI-B computed rates
- Falls back to analytical formulas for non-EEDF reactions

### 4. Updated Argon Chemistry (`cases/testArgon/chemistry_updated.yml`)
- **Moved elastic to `reactions_eedf`** - now uses cross-section-based rate from LoKI-B
- Process ID: `"Ar -> Ar"` for elastic momentum transfer
- Removed analytical elastic formula `1.84e-8 * Te**1.5`
- Updated reference to indicate all electron-impact processes from LXCat

## How It Works

1. **At t=0.0**: LoKI-B runs, computes EEDF and rate coefficients for all processes (elastic, excitation, ionization)
2. **During simulation**: Reactions with `use_eedf=True` fetch rates from cached LoKI results
3. **Elastic energy transfer**: Now consistent with EEDF calculation (same cross-sections)

## Next Steps

Replace `cases/testArgon/chemistry.yml` with `chemistry_updated.yml` content and test:
```bash
python main.py cases/testArgon/config.yml
```

This implements the Plasimo-style approach where elastic uses cross-section-based rates.
