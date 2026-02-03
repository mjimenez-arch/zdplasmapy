> [!NOTE]
> **Status: Verified**
> Validated against codebase (Feb 2026).

# EEDF Integration Summary

**Date**: December 8, 2025  
**Branch**: `feature/loki-b-eedf-integration`  
**Status**: Functional, testing in progress

## Overview

Successfully integrated LoKI-B Boltzmann solver for non-Maxwellian electron energy distribution function (EEDF) calculations in zdplasmapy. This enables accurate electron impact rate coefficients based on cross-section data instead of assuming Maxwellian distributions.

## Key Components

### 1. EEDF Solver Backend (`src/eedf_solver.py`)
- **Architecture**: Pluggable Protocol-based system supporting multiple solvers
- **Current Backend**: LoKI-B (C++ Boltzmann solver)
- **Future Support**: BOLSIG+, Bolos planned
- **Features**:
  - Auto-detection of LoKI binary in `external/LoKI-B-cpp/build/`
  - Cross-section file resolution (LXCat format)
  - Database file auto-detection (masses, frequencies, etc.)
  - Input/output translation between zdplasmapy and LoKI formats
  - Process ID matching for reaction disambiguation

### 2. Chemistry Parser Updates (`src/chemistry_parser.py`)
- **New Section**: `reactions_eedf` in chemistry.yml files
- **Structure**:
  ```yaml
  reactions_eedf:
    file: "external/LoKI-B-cpp/input/Oxygen/O2_LXCat.txt"
    reference: "Phelps 1985, www.LXCat.net"
    reactions:
      - {formula: "e + O2 -> e + O2", process: "O2 -> O2", energy_loss: ..., type: "elastic"}
      - {formula: "e + O2 -> O2+ + 2e", process: "O2 -> O2^+", energy_loss: 12.1, type: "ionization"}
  ```
- **Features**:
  - Project-relative cross-section file paths
  - Process ID field for matching reactions to cross-section data
  - Mixed mode: EEDF reactions (`use_eedf: True`) + analytic reactions (`use_eedf: False`)

### 3. Configuration System (`src/config_loader.py`)
- **Location**: EEDF settings in `additional_parameters.eedf`
- **Schema**:
  ```yaml
  additional_parameters:
    eedf:
      enabled: true
      backend: loki
      timestamps: [0.0, 1.0e-6, 5.0e-6, 1.0e-5, ...]
      options: {}
  ```
- **Timestamp Control**: EEDF calculated only at specified times (not every step)

### 4. Global Model Integration (`src/global_model.py`)
- **Modification**: Added EEDF calls in `_ode_system()` method
- **Logic**: 
  - Check if current time matches a timestamp (within tolerance)
  - Build EEDF request with current plasma parameters
  - Call LoKI-B backend
  - Cache results to avoid redundant calls
  - Use EEDF-derived rate coefficients for electron-impact reactions
- **Attributes**: `eedf_enabled`, `eedf_backend`, `eedf_timestamps`, `eedf_results`

### 5. External Dependencies
- **LoKI-B Installation**: `external/setup_loki_b.sh` script
  - Auto-clones from GitHub
  - Detects Ninja build system for faster compilation
  - Pure Eigen backend (no OpenBLAS/MKL required by default)
  - Binary location: `external/LoKI-B-cpp/build/app/loki`
- **Cross-sections**: LXCat format in `external/LoKI-B-cpp/input/<Species>/`
- **Database Files**: masses.txt, harmonicFrequencies.txt, etc.

### 6. Test Case (`cases/testEEDF/`)
- **Chemistry**: Oxygen plasma (based on Chung 1999)
- **Species**: O2, O2+, O, O+, O-, e
- **Reactions**: 
  - 2 EEDF-driven (elastic, ionization) from cross-sections
  - 11 analytic (attachment, recombination, dissociation, wall losses)
- **Configuration**: 1 Torr, 10W power, cylindrical geometry
- **Purpose**: Validation of EEDF integration, template for future cases

## Implementation Details

### Cross-Section File Resolution
1. Chemistry parser reads `file` path from `reactions_eedf` section
2. Path resolved relative to project root
3. EEDF backend receives absolute path to cross-section file
4. LoKI loads cross-sections and maps to processes via `process` field

### Timestamp-Based Execution
- **Rationale**: EEDF calculation is expensive, only needed when conditions change significantly
- **Mechanism**: User specifies timestamps in config (e.g., `[0, 1e-6, 1e-5, ...]`)
- **Tolerance**: `abs(t - timestamp) < 1e-9` for floating-point comparison
- **Caching**: Results stored in `self.eedf_results` dict keyed by timestamp

### LoKI Input Format
- **Format**: YAML-like with `%` comments (not standard YAML)
- **Sections**: workingConditions, electronKinetics, chemistry, output
- **Translation**: `_build_loki_input()` converts zdplasmapy request to LoKI format
- **Ground States**: Species mapping (Ar→Ar(1S0), O2→O2(X), etc.)

### Output Parsing
- **Preferred**: JSON output (`output.json` with energyGrid, eedf fields)
- **Fallback**: Text output (`eedf.txt` two-column format)
- **Normalization**: Backend returns `{energy_grid: [...], eedf: [...], diagnostics: {...}}`

