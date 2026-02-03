> [!NOTE]
> **Status: Verified**
> Validated against codebase (Feb 2026).

# zdplasmapy Configuration File Format

This document describes the standard format for `config.yml` files in zdplasmapy case folders.

## Overview

Each case folder (`cases/<case_name>/`) must contain a `config.yml` file that defines:
- Metadata (name, description, references)
- Chemistry file reference(s)
- Physical parameters (pressure, power, temperature)
- Reactor geometry
- Transport model selection
- Initial plasma conditions

## File Structure

```yaml
# --- Metadata ---
name: "Short descriptive name"
description: "Detailed description including publication reference"

# --- Chemistry Reference ---
chemistry:
  file: "./chemistry.yml"  # Single file
  # OR
  files:                   # Multiple files (merged)
    - "./chemistry1.yml"
    - "./chemistry2.yml"

# --- Simulation Parameters ---
parameters:
  pressure_Pa: 5.5         # Gas pressure (Pa)
  power_W: 58              # Input power (W)
  gas_temp_K: 600          # Neutral gas temperature (K)
  time_end_s: 1.0          # Simulation end time (s)

# --- Reactor Geometry ---
geometry:
  type: cylindrical        # 'cylindrical' or 'parallel_plate'
  # For cylindrical:
  length_m: 0.48           # Cylinder length (m)
  radius_m: 0.15           # Cylinder radius (m)
  # For parallel_plate:
  # area_m2: 0.01          # Electrode area (m^2)
  # gap_m: 0.025           # Gap between electrodes (m)

# --- Transport Model ---
transport_model: "declarations"
# Options:
#   - "declarations": Use custom declarations.py in case folder
#   - A registered class name from src/transport_models.py
#   - "default": No transport (chemistry only)

# --- Initial Conditions ---
initial_conditions:
  Te_eV: 2.5               # Initial electron temperature (eV)
  species_densities:       # Initial densities (m^-3)
    O2+: 1.0e12
    O: 1.0e13
    O+: 1.0e12
    O-: 1.0e11
    e: 1.0e12

# --- Optional: Additional Parameters ---
additional_parameters:
  sigma: 1.25e-20          # Case-specific parameters
  # Add any parameters needed by declarations.py

# --- Optional: Validation Data ---
#validation:
#  manifest_file: "./validation/metadata.yml"
```

## Required Fields

### Top-Level Required
- `name` (string): Brief, descriptive name
- `description` (string): Detailed description with publication reference
- `chemistry` (object): Chemistry file reference(s)
- `parameters` (object): Simulation parameters
- `geometry` (object): Reactor geometry
- `transport_model` (string): Transport model selection
- `initial_conditions` (object): Initial plasma state

### Parameters Section Required
- `pressure_Pa` (number > 0): Gas pressure in Pascals
- `power_W` (number ≥ 0): Input power in Watts
- `gas_temp_K` (number > 0): Neutral gas temperature in Kelvin
- `time_end_s` (number > 0): Simulation end time in seconds

### Geometry Section Required
- `type` (string): Must be `"cylindrical"` or `"parallel_plate"`
- **For cylindrical:**
  - `length_m` (number > 0): Cylinder length in meters
  - `radius_m` (number > 0): Cylinder radius in meters
- **For parallel_plate:**
  - `area_m2` (number > 0): Electrode area in square meters
  - `gap_m` (number > 0): Gap between electrodes in meters

### Initial Conditions Section Required
- `Te_eV` (number > 0): Initial electron temperature in eV
- `species_densities` (object): Dictionary of species names to densities (m^-3)
  - Must contain at least one species
  - Species names must match those in chemistry.yml

## Naming Conventions

### Units in Field Names
Always include units as suffix using underscores:
- `_Pa`: Pascals
- `_W`: Watts
- `_K`: Kelvin
- `_eV`: electron volts
- `_m`: meters
- `_m2`: square meters
- `_s`: seconds

### Field Naming Style
- Use `snake_case` for all field names
- Be explicit: `length_m` not just `length`
- Use descriptive names: `gas_temp_K` not just `T`

## Chemistry File Reference

### Single File
```yaml
chemistry:
  file: "./chemistry.yml"
```

### Multiple Files (Merged)
```yaml
chemistry:
  files:
    - "./chemistry_base.yml"
    - "./chemistry_extra.yml"
```

Species and reactions from all files will be merged.

## Transport Model Selection

### Custom Per-Case (Recommended for Publications)
```yaml
transport_model: "declarations"
```
Requires `declarations.py` in the same folder with functions:
- `compute_geometry(config)` → dict with volume, Reff, etc.
- `compute_constant_data(config)` → dict with derived constants
- `power_input_func(t, volume)` → float (power in W)
- `calculate_declarations(params)` → dict (wall losses, etc.)

### Registered Class (Reusable Models)
```yaml
transport_model: "chung_1999"
```
Uses a class from `src/transport_models.py` registry.

### No Transport (Chemistry Only)
```yaml
transport_model: "default"
```

## Validation

The configuration is validated against a JSON schema (`src/config_schema.json`).

### Install Validation Dependencies
```bash
pip install jsonschema
```

### Validate Manually
```python
from src.config_parser import load_config
config = load_config("cases/my_case/config.yml")
# ValidationError raised if invalid
```

## Examples

### Minimal Valid Config
```yaml
name: "Test Case"
description: "A minimal example"
chemistry:
  file: "./chemistry.yml"
parameters:
  pressure_Pa: 10.0
  power_W: 100.0
  gas_temp_K: 300.0
  time_end_s: 0.1
geometry:
  type: cylindrical
  length_m: 0.1
  radius_m: 0.05
transport_model: "default"
initial_conditions:
  Te_eV: 1.0
  species_densities:
    Ar+: 1e10
    e: 1e10
```

### Full Featured Config
See `cases/chung_1999_o2_icp/config.yml` or `cases/ashida1995/config.yml` for complete examples.

## Best Practices

1. **Always include units in field names** to avoid ambiguity
2. **Add comments** to document unusual choices or parameter sources
3. **Keep descriptions brief but informative** - include DOI or full citation
4. **Use consistent indentation** (2 spaces recommended)
5. **Order sections logically**: metadata → chemistry → parameters → geometry → physics → initial conditions
6. **Validate before committing** to catch errors early
7. **Document additional_parameters** if using custom declarations.py

## Common Errors

### Missing Required Field
```
ValidationError: 'pressure_Pa' is a required property
```
**Solution:** Add the missing field to the `parameters` section.

### Wrong Geometry Fields
```
ValueError: Cylindrical geometry requires radius_m and length_m
```
**Solution:** Ensure geometry fields match the selected type.

### Invalid Species Reference
```
KeyError: Species 'Ar2+' not found in chemistry
```
**Solution:** Check species names in `initial_conditions.species_densities` match `chemistry.yml`.

## Version History

- **v1.0** (Nov 2025): Initial format definition for publication-centric refactor
