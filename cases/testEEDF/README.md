# Test Case: EEDF Solver Integration

This is a minimal test case to validate the EEDF solver (LoKI-B) integration with zdplasmapy.

## Purpose

- Demonstrate EEDF backend configuration
- Validate LoKI-B input/output translation
- Serve as a template for EEDF-driven global models

## Chemistry

Simple Argon chemistry with electron-impact reactions:
- Elastic scattering
- Ionization: `e + Ar -> Ar+ + 2e`
- Excitation to metastable state

## Configuration

- Uses LoKI-B backend for EEDF calculation
- Reduced electric field E/N = 100 Td
- Low pressure (1 Pa) for strong non-equilibrium effects

## Running

```bash
# From zdplasmapy root
python main.py  # Edit main.py to point to cases/testEEDF/config.yml
```

Expected behavior:
- LoKI-B computes EEDF at each timestep
- Rate coefficients updated from EEDF rather than assuming Maxwellian
- Should converge to steady-state in ~1 ms
