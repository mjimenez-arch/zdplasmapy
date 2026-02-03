> [!WARNING]
> **Status: Under Revision**
> This document may contain outdated references (e.g. `app_new.py` is now `app.py`).

# Minimal Refactor Summary

## Changes Implemented

### 1. **Parameter Grouping System**
Created `src/case_utils.py` with:
- `discover_cases()`: Automatically finds all valid case folders in `cases/`
- `get_case_config_path()`: Helper to build config paths
- `group_parameters()`: Organizes flat parameter dict into logical groups

### 2. **Updated `src/util.py`**
- Added wrapper around `declarations_func` to automatically convert flat params to grouped structure
- Groups parameters into 4 categories:
  - `constants`: Physical constants (m_e, q_e, k_B, epsilon_0)
  - `variables`: Time-dependent state (Te_eV, Th_eV, na, ne, etc.)
  - `geometry`: Geometry-related (Reff, volume, L, R, etc.)
  - `species`: Species-specific (mass_*, sigma_*, etc.)

### 3. **New `app_new.py`** (Streamlit UI)
- Sidebar with automatic case discovery
- Dropdown to select any case from `cases/` folder
- Manual path override for custom locations
- Displays which config is being used
- Clean run button + results visualization

### 4. **Updated Case Declarations**
- `cases/ashida1995/declarations.py`: Uses grouped params
- `cases/chung_1999_o2_icp/declarations_new.py`: Example with grouped params

## New Parameter Access Pattern

**Old style** (flat dictionary):
```python
def case_declarations(params):
    Te_eV = params['Te_eV']
    m_e = params['constants']['m_e']
    mass_Ar = params['mass_Ar']
    # ...
```

**New style** (grouped):
```python
def case_declarations(params):
    constants = params.get('constants', {})
    variables = params.get('variables', {})
    geometry = params.get('geometry', {})
    species = params.get('species', {})
    
    Te_eV = variables.get('Te_eV', 1.0)
    m_e = constants.get('m_e', 9.10938e-31)
    mass_Ar = species.get('mass_Ar', 39.95 * 1.67e-27)
    Reff = geometry.get('Reff', 0.01)
    # ...
```

## Benefits
✓ **Cleaner**: Logical organization of parameters  
✓ **Scalable**: Easy to add new variables without cluttering  
✓ **Consistent**: Same pattern across all cases  
✓ **Safer**: `.get()` with defaults prevents KeyError  
✓ **Self-documenting**: Clear role of each parameter group  

## Testing

### CLI
```powershell
python main.py --config cases/ashida1995/config.yml
python main.py --config cases/chung_1999_o2_icp/config.yml
```

### Streamlit
```powershell
streamlit run app_new.py
```
- Select case from sidebar dropdown
- Click "Run Simulation"
- View plots and final state

## Migration Checklist
- [x] `src/case_utils.py` created
- [x] `src/util.py` updated with grouping wrapper
- [x] `app_new.py` with case discovery
- [x] `ashida1995/declarations.py` uses grouped params
- [x] Example `chung_1999_o2_icp/declarations_new.py` provided
- [ ] Replace `app.py` with `app_new.py` (user decision)
- [ ] Replace `declarations.py` in chung case with `_new` version (user decision)
- [ ] Test both cases end-to-end
- [ ] Update any other custom cases to use grouped params

## Next Steps
1. **Test**: Run both ashida and chung cases via CLI and app
2. **Validate**: Confirm no KeyError, correct physics
3. **Replace**: Rename `app_new.py` → `app.py` if satisfied
4. **Document**: Update main README with new parameter pattern
5. **Cleanup**: Remove `_new` suffix from declaration files once validated
