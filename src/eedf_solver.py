# src/eedf_solver.py
"""
EEDF (Electron Energy Distribution Function) solver interface.

Provides pluggable backend support for:
  - LOKI-B (Kinetic Boltzmann solver)
  - Analytical approximations (Maxwellian)
  - Future: BOLSIG+, Bolos, etc.

Generates electron impact rate coefficients as functions of Te and other plasma parameters.
"""

from typing import Dict, Any, Optional, Protocol, Tuple, List, Callable
import json
import os
import subprocess
import tempfile
import warnings
import logging
import numpy as np
from pathlib import Path


class EEDFBackend(Protocol):
    def run(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute an EEDF computation with a backend-specific request.

        The request is a normalized dict produced by zdplasmapy with keys like:
        - gas: { species: List[str] }
        - field: { type: "uniform", value: float }
        - pressure: float (Pa or Torr based on backend adapter)
        - temperature: float (K)
        - grid: { emin: float, emax: float, points: int }
        - options: { ... backend-specific optional flags }

        Returns a normalized response dict with at least:
        - eedf: List[float]
        - energy_grid: List[float]
        - diagnostics: Dict[str, Any]
        """
        ...


def _detect_loki_binary(explicit_path: Optional[str]) -> Optional[str]:
    if explicit_path and os.path.isfile(explicit_path) and os.access(explicit_path, os.X_OK):
        return explicit_path
    candidates = [
        os.path.join(os.path.dirname(__file__), "..", "external", "LoKI-B-cpp", "build", "app", "loki"),
        os.path.join(os.path.dirname(__file__), "..", "external", "LoKI-B-cpp", "build", "loki"),
        os.path.join(os.path.dirname(__file__), "..", "external", "LoKI-B-cpp", "build", "bin", "loki"),
    ]
    for p in candidates:
        p = os.path.abspath(p)
        if os.path.isfile(p) and os.access(p, os.X_OK):
            return p
    return None


def _find_lxcat_files(gas_species: List[str], loki_root: Optional[str] = None) -> List[str]:
    """
    Auto-detect LXCat cross-section files for given gas species.
    Searches in LoKI-B-cpp/input/<Species>/ directories.
    
    Args:
        gas_species: List of gas species names (e.g., ['Ar'], ['O2'], ['N2'])
        loki_root: Root directory of LoKI-B-cpp installation
    
    Returns:
        List of absolute paths to LXCat files
    """
    if loki_root is None:
        # Try to find LoKI root from binary path
        binary = _detect_loki_binary(None)
        if binary:
            loki_root = os.path.abspath(os.path.join(os.path.dirname(binary), "..", ".."))
        else:
            loki_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "external", "LoKI-B-cpp"))
    
    lxcat_files = []
    input_dir = os.path.join(loki_root, "input")
    
    if not os.path.isdir(input_dir):
        return []
    
    # Map common species names to directory names
    species_map = {
        'Ar': 'Argon',
        'O2': 'Oxygen',
        'O': 'Oxygen',
        'N2': 'Nitrogen',
        'N': 'Nitrogen',
        'He': 'Helium',
        'H2': 'Hydrogen',
    }
    
    for species in gas_species:
        # Clean species name (remove charge, vibrational states, etc.)
        base_species = species.split('(')[0].strip().replace('+', '').replace('-', '').replace('*', '')
        
        # Get directory name
        dir_name = species_map.get(base_species, base_species)
        species_dir = os.path.join(input_dir, dir_name)
        
        if os.path.isdir(species_dir):
            # Find all .txt files in the species directory
            for filename in os.listdir(species_dir):
                if filename.endswith('.txt') and 'LXCat' in filename:
                    lxcat_files.append(os.path.join(species_dir, filename))
    
    return lxcat_files


def _find_database_files(loki_root: Optional[str] = None) -> Dict[str, str]:
    """
    Find LoKI-B database files (masses, frequencies, etc.).
    
    Returns:
        Dict mapping database names to file paths
    """
    if loki_root is None:
        binary = _detect_loki_binary(None)
        if binary:
            loki_root = os.path.abspath(os.path.join(os.path.dirname(binary), "..", ".."))
        else:
            loki_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "external", "LoKI-B-cpp"))
    
    databases_dir = os.path.join(loki_root, "input", "Databases")
    
    db_files = {}
    if os.path.isdir(databases_dir):
        for db_name in ["masses.txt", "harmonicFrequencies.txt", "anharmonicFrequencies.txt", 
                       "rotationalConstants.txt", "quadrupoleMoment.txt", "OPBParameter.txt"]:
            db_path = os.path.join(databases_dir, db_name)
            if os.path.isfile(db_path):
                db_files[db_name] = db_path
    
    return db_files


def _build_loki_input(req: Dict[str, Any]) -> str:
    """
    Translate normalized request into LoKI-B input format (YAML-like with % comments).
    This function isolates schema differences so future changes only require edits here.
    
    LoKI-B uses a custom input format similar to YAML.
    See: https://github.com/LoKI-Suite/LoKI-B-cpp/blob/main/tests/cases/argon_full/lokib.in
    """
    gas_species = req.get("gas", {}).get("species", [])
    gas_fractions = req.get("gas", {}).get("fractions", [1.0] * len(gas_species))
    field = req.get("field", {'value': 100.0})
    pressure = req.get("pressure", 133.32)  # default: 1 Torr in Pa
    temperature = req.get("temperature", 300.0)
    grid = req.get("grid", {'emin': 0.01, 'emax': 30.0, 'points': 200})
    options = req.get('options', {}) or {}

    physics_opts = options.get('physics', {}) or {}
    numerics_opts = options.get('numerics', {}) or {}
    energy_grid_opts = numerics_opts.get('energy_grid', {}) or {}

    include_ee = bool(physics_opts.get('coulomb_collisions', False))
    max_energy = energy_grid_opts.get('emax_eV', grid.get('emax', 30.0))
    cell_number = energy_grid_opts.get('points', grid.get('points', 200))
    max_power_balance_error = numerics_opts.get('precision', 1e-9)
    max_eedf_rel_error = numerics_opts.get('convergence', 1e-9)
    
    # Get LXCat files - prioritize reaction-specific cross-sections, then auto-detect
    lxcat_files = req.get("options", {}).get("lxcat_files", [])
    if not lxcat_files:
        # Check if reactions specify cross-section files
        reactions = req.get("options", {}).get("reactions", [])
        cross_section_files = set()
        for rxn in reactions:
            if rxn.get('use_eedf') and rxn.get('cross_section'):
                # Resolve relative path to LoKI input directory
                loki_root = req.get("options", {}).get("loki_root")
                if loki_root is None:
                    binary = _detect_loki_binary(None)
                    if binary:
                        loki_root = os.path.abspath(os.path.join(os.path.dirname(binary), "..", ".."))
                    else:
                        loki_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "external", "LoKI-B-cpp"))
                
                # Map species to directory (e.g., O2 -> Oxygen)
                species_map = {'O2': 'Oxygen', 'O': 'Oxygen', 'N2': 'Nitrogen', 'Ar': 'Argon', 'He': 'Helium'}
                base_species = gas_species[0].split('(')[0].strip().replace('+', '').replace('-', '')
                dir_name = species_map.get(base_species, base_species)
                
                cs_file = os.path.join(loki_root, "input", dir_name, rxn['cross_section'])
                if os.path.isfile(cs_file):
                    cross_section_files.add(cs_file)
        
        lxcat_files = list(cross_section_files)
        
        # Fallback: auto-detect if no cross-sections specified
        if not lxcat_files:
            lxcat_files = _find_lxcat_files(gas_species)
    
    # Get database files
    db_files = _find_database_files()
    
    # Build gas fraction lines
    fraction_lines = []
    for species, frac in zip(gas_species, gas_fractions):
        fraction_lines.append(f"      - {species} = {frac}")
    
    # Build LXCat files section
    lxcat_section = ""
    if lxcat_files:
        lxcat_lines = []
        for lxcat_file in lxcat_files:
            lxcat_lines.append(f"    - {lxcat_file}")
        lxcat_section = f"""  LXCatFiles:
{chr(10).join(lxcat_lines)}"""
    else:
        raise ValueError(f"No LXCat cross-section files found for species: {gas_species}. "
                        f"Please provide them via options.lxcat_files or ensure they exist in "
                        f"external/LoKI-B-cpp/input/<Species>/")
    
    # Build gas properties section with database files
    gas_props_section = f"""  gasProperties:
    mass: {db_files.get('masses.txt', 'Databases/masses.txt')}
    fraction:
{chr(10).join(fraction_lines)}"""
    
    # Add optional database files if they exist
    if 'harmonicFrequencies.txt' in db_files:
        gas_props_section += f"\n    harmonicFrequency: {db_files['harmonicFrequencies.txt']}"
    if 'anharmonicFrequencies.txt' in db_files:
        gas_props_section += f"\n    anharmonicFrequency: {db_files['anharmonicFrequencies.txt']}"
    if 'rotationalConstants.txt' in db_files:
        gas_props_section += f"\n    rotationalConstant: {db_files['rotationalConstants.txt']}"
    if 'quadrupoleMoment.txt' in db_files:
        gas_props_section += f"\n    electricQuadrupoleMoment: {db_files['quadrupoleMoment.txt']}"
        gas_props_section += f"\n    OPBParameter: {db_files['OPBParameter.txt']}"
    
    # Build state population (use defaults for now, can be customized via options)
    # LoKI uses specific state names from the cross-section files
    # Map species names to LoKI-B ground state labels (as defined in LXCat files)
    state_pop_lines = []
    ground_state_map = {
        'Ar': 'Ar(1S0)',
        'O2': 'O2(X)',
        'O': 'O(3P)',
        'N2': 'N2(X)',
        'N': 'N(4S)',
        'He': 'He(1S)',
        'H2': 'H2(X)',
    }
    
    for species in gas_species:
        # Clean species name (remove charge, vibrational states, etc.)
        base_species = species.split('(')[0].strip().replace('+', '').replace('-', '').replace('*', '')
        
        # Get ground state name or use default
        ground_state = ground_state_map.get(base_species, f"{species}(X)")
        
        if ground_state == 'O2(X)':
            # Use Boltzmann distribution for O2(X) manifold
            state_pop_lines.append(f"      - {ground_state} = boltzmannPopulation@gasTemperature")
        else:
            state_pop_lines.append(f"      - {ground_state} = 1.0")
    
    # Determine if we have a single point or a scan
    # Check if field value is a string (e.g. "linspace(...)") or float
    field_val = field.get("value", 100.0)
    if isinstance(field_val, str):
        reduced_field_str = field_val
    else:
        reduced_field_str = f"{field_val}"
        
    if isinstance(temperature, str):
        te_str = temperature
    else:
        te_str = f"{temperature}" # e.g. 1 (the initial Te guess for Boltzmann solver)
        # Note: loki usually takes electronTemperature as a guess or a range?
        # For 'boltzmann' EEDF type, this parameter might be the thermal energy of the lattice?
        # No, 'electronTemperature' in 'workingConditions' is usually the initial guess OR the fixed value 
        # if 'prescribedEedf' is used.
        # But for 'boltzmann', it acts as a guess.
        
    # Build minimal LoKI input
    loki_input = f"""% Auto-generated input for zdplasmapy EEDF solver

workingConditions:
  reducedField: {reduced_field_str}
  electronTemperature: {te_str}
  excitationFrequency: 0
  gasPressure: {pressure}
  gasTemperature: {temperature}  % This is gas temperature (usually float)
  electronDensity: 1e19
  chamberLength: 1.0
  chamberRadius: 1.0

electronKinetics:
  isOn: true
  eedfType: boltzmann
  ionizationOperatorType: conservative
  growthModelType: temporal
  includeEECollisions: {str(include_ee).lower()}
{lxcat_section}
{gas_props_section}
  stateProperties:
    population:
{chr(10).join(state_pop_lines)}
  numerics:
    energyGrid:
      maxEnergy: {max_energy}
      cellNumber: {cell_number}
    smartGrid:
      minEedfDecay: 20
    maxPowerBalanceRelError: {max_power_balance_error}
    nonLinearRoutines:
      algorithm: mixingDirectSolutions
      mixingParameter: 0.7
      maxEedfRelError: {max_eedf_rel_error}

chemistry:
  isOn: false

gui:
  isOn: false

output:
  isOn: true
  writeJSON: true
  JSONFile: output.json
  folder: output
  dataFiles:
    - eedf
    - swarmParameters
    - rateCoefficients
    - powerBalance
"""
    
    return loki_input


def _parse_loki_output(payload: str) -> Dict[str, Any]:
    """
    Parse LoKI-B text output (eedf.txt format).
    This keeps a single choke point if LoKI output format evolves.
    """
    # Fallback: try to parse two-column whitespace output
    energy: List[float] = []
    eedf: List[float] = []
    for line in payload.splitlines():
        parts = line.strip().split()
        if len(parts) >= 2:
            try:
                energy.append(float(parts[0]))
                eedf.append(float(parts[1]))
            except ValueError:
                continue
    return {"energy_grid": energy, "eedf": eedf, "diagnostics": {"format": "text"}}


def _parse_loki_json_output(output_dir: str) -> Dict[str, Any]:
    """
    Parse LoKI-B JSON output from the given directory.
    Handles both single-point runs and parameter scans (LookUpTable).
    """
    json_path = os.path.join(output_dir, "output.json")
    if not os.path.exists(json_path):
        return {}

    try:
        with open(json_path, "r") as f:
            data = json.load(f)
            
        # Check for Scan Mode (keys like "reducedField_10", "reducedField_20"...)
        scan_keys = [k for k in data.keys() if k.startswith("reducedField_")]
        
        if scan_keys:
            # Parse as Lookup Table
            print(f"DEBUG: Detected Parameter Scan with {len(scan_keys)} points.")
            table_entries = []
            
            for key in scan_keys:
                # Extract field value from key (e.g. reducedField_10.5 -> 10.5)
                # Or from the data inside if available?
                # Data inside usually has "workingConditions": {"reducedField": val} ?
                # The key format is usually user-defined or automatic. 
                # Let's try to get it from the key suffix first.
                try:
                    # LoKI key format: reducedField_<val>
                    val_str = key.replace("reducedField_", "")
                    reduced_field = float(val_str)
                except ValueError:
                    reduced_field = 0.0 # Fallback
                
                entry_data = data[key]
                rates = entry_data.get("rateCoefficients")
                
                # Handling Swarm Parameters (List of Dicts -> Flat Dict)
                # LoKI-B inconsistency: checks for both camelCase and snake_case
                raw_swarm = entry_data.get("swarmParameters")
                if raw_swarm is None:
                    raw_swarm = entry_data.get("swarm_parameters", [])
                
                swarm_params = {}
                if isinstance(raw_swarm, list):
                    for item in raw_swarm:
                        for k, v in item.items():
                             if isinstance(v, dict) and "value" in v:
                                 swarm_params[k] = v["value"]
                             else:
                                 swarm_params[k] = v
                elif isinstance(raw_swarm, dict):
                    swarm_params = raw_swarm
                
                # Fallback: If rates missing in JSON, check text file
                # LoKI-B key is e.g. "reducedField_10.5".
                # Folder usually matches this key.
                if not rates:
                    # Try both nesting levels observed
                    paths_to_try = [
                        os.path.join(output_dir, "output", key, "rateCoefficients.txt"),
                        os.path.join(output_dir, "output", "output", key, "rateCoefficients.txt")
                    ]
                    
                    for txt_path in paths_to_try:
                        if os.path.exists(txt_path):
                            if not rates: rates = {} # Initialize if None
                            try:
                                with open(txt_path, "r") as f:
                                    lines = f.readlines()
                                for line in lines[1:]:
                                    line = line.strip()
                                    if not line or line.startswith('---') or line.startswith('*'): continue
                                    parts = line.split(None, 2)
                                    if len(parts) >= 3:
                                        try:
                                            val = float(parts[0])
                                            d = parts[2].strip()
                                            rates[d] = val
                                        except ValueError: pass
                                # If successful, break
                                if rates: break
                            except Exception as e:
                                print(f"Warning: Error parsing {txt_path}: {e}")

                table_entries.append({
                    "reduced_field_Td": reduced_field,
                    "rate_coefficients": rates or {},
                    "swarm_parameters": swarm_params
                })
            
            # Sort by reduced field
            table_entries.sort(key=lambda x: x["reduced_field_Td"])
            
            return {
                "type": "lookup_table",
                "param": "reduced_field_Td",
                "entries": table_entries
            }
            
        else:
            # Single Point Mode (Legacy)
            # Structure is direct: {"energyGrid": ..., "eedf": ...}
            energy = data.get("energyGrid") or data.get("energy") or []
            eedf = data.get("eedf") or data.get("f") or []
            rate_coeffs = data.get("rateCoefficients") or {}
            swarm_params = data.get("swarmParameters") or {}
            
            return {
                "type": "single",
                "energy_grid": energy, 
                "eedf": eedf, 
                "rate_coefficients": rate_coeffs,
                "swarm_parameters": swarm_params
            }
            
    except Exception as e:
        print(f"DEBUG: JSON parse error: {e}")
        return {}


class LoKIBackend:
    def __init__(self, binary_path: Optional[str] = None):
        self.binary = _detect_loki_binary(binary_path)
        if not self.binary:
            raise FileNotFoundError("LoKI-B binary not found. Set eedf.loki_binary or place it under external/LoKI-B-cpp/build/app/loki")

    def run(self, request: Dict[str, Any]) -> Dict[str, Any]:
        loki_input_text = _build_loki_input(request)
        
        # Use persistent output directory structure: output/eedf/
        base_output_dir = "output"
        eedf_dir = os.path.join(base_output_dir, "eedf")
        os.makedirs(eedf_dir, exist_ok=True)
        
        # Prevent LoKI-B interactive prompt by clearing output/eedf/output if it exists
        actual_output_dir = os.path.join(eedf_dir, "output")
        if os.path.exists(actual_output_dir):
            import shutil
            try:
                shutil.rmtree(actual_output_dir)
            except OSError as e:
                print(f"Warning: Could not clear output directory {actual_output_dir}: {e}")

        in_path = os.path.join(eedf_dir, "lokib.in")
        # loki_output_dir seemed unused or redundant if LoKI writes to 'output'
        # But we keep it if needed for other things? No, let's just stick to standard.
        
        print(f"\n=== Running LoKI-B ===")
        print(f"DEBUG: I AM RUNNING FROM {__file__}") 
        print(f"Binary: {self.binary}")
        print(f"Working directory: {os.path.abspath(eedf_dir)}")
        print(f"Input file: {os.path.abspath(in_path)}")
        
        # Write input file
        with open(in_path, "w") as f:
            f.write(loki_input_text)
        print(f"Input file written ({len(loki_input_text)} bytes)")
        
        # Run LoKI-B (it expects to be run in the directory with the input file)
        print(f"Executing: {self.binary} lokib.in")
        proc = subprocess.run(
            [self.binary, "lokib.in"], 
            cwd=eedf_dir,
            capture_output=True, 
            text=True
        )
        
        print(f"Return code: {proc.returncode}")
        if proc.stdout:
            print(f"STDOUT:\n{proc.stdout[:500]}")
        if proc.stderr:
            print(f"STDERR:\n{proc.stderr[:500]}")
        
        if proc.returncode != 0:
            raise RuntimeError(f"LoKI-B failed: {proc.stderr.strip() or proc.stdout.strip()}")
        
        # LoKI-B creates its own 'output' subdirectory
        actual_output_dir = os.path.join(eedf_dir, "output")
        
        # List output directory contents
        print(f"\nOutput directory contents:")
        if os.path.exists(actual_output_dir):
            for item in os.listdir(actual_output_dir):
                item_path = os.path.join(actual_output_dir, item)
                size = os.path.getsize(item_path) if os.path.isfile(item_path) else 0
                print(f"  {item} ({size} bytes)")
        else:
            print(f"  WARNING: Output directory {actual_output_dir} does not exist!")
        
        print(f"\n*** LoKI-B output location: {os.path.abspath(actual_output_dir)}/ ***\n")
        
        # Try to read JSON output first (if writeJSON: true)
        # Note: LoKI-B seems to write output.json in the working directory (eedf_dir),
        # not inside the output folder, despite 'folder: output' config?
        # Or maybe it puts it there if JSONFile path is relative?
        # Anyway, we found it at output/eedf/output.json.
        result = _parse_loki_json_output(eedf_dir)
        if result:
            return result
        
        # Fallback to text EEDF file
        eedf_file = os.path.join(actual_output_dir, "eedf.txt")
        if os.path.isfile(eedf_file):
            print(f"Reading {eedf_file}")
            with open(eedf_file, "r") as f:
                payload = f.read()
        else:
            # Last resort: parse stdout
            print(f"WARNING: No output files found, using stdout")
            payload = proc.stdout
                
        return _parse_loki_output(payload)


class NullBackend:
    """Placeholder backend to support stubbing or alternative solvers later (BolOS, BOLSIG-)."""
    def run(self, request: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError("No EEDF backend configured. Choose 'loki' or implement another backend.")


def get_eedf_backend(config: Dict[str, Any]) -> EEDFBackend:
    eedf_cfg = (config or {}).get("eedf", {})
    backend = eedf_cfg.get("backend", "loki").lower()
    if backend == "loki":
        return LoKIBackend(binary_path=eedf_cfg.get("loki_binary"))
    elif backend in ("bolos", "bolsig", "bolsig-"):
        # Future: implement adapters here with their input/output translators
        return NullBackend()
    else:
        return NullBackend()


def run_eedf(config: Dict[str, Any], request: Dict[str, Any]) -> Dict[str, Any]:
    """
    Public entrypoint for EEDF solving. Selects backend via `config['eedf']['backend']`.
    Returns normalized output dict: { 'energy_grid': [...], 'eedf': [...], 'diagnostics': {...} }.
    """
    backend = get_eedf_backend(config)
    return backend.run(request)


class EEDFSolver:
    """Base class for EEDF solvers."""
    
    def __init__(self, cache_dir: Optional[Path] = None):
        """Initialize EEDF solver.
        
        Args:
            cache_dir: Directory for caching lookup tables. If None, uses ./eedf_cache/
        """
        self.cache_dir = Path(cache_dir) if cache_dir else Path("eedf_cache")
        self.cache_dir.mkdir(exist_ok=True, parents=True)
    
    def get_rate_coefficient(self, reaction_id: str, params: Dict) -> float:
        """Compute rate coefficient for a reaction at given plasma parameters.
        
        Args:
            reaction_id: Unique identifier for reaction (e.g., 'e + Ar -> Ar+ + 2e')
            params: Plasma parameters dict (must include 'Te_eV', 'n_e', etc.)
        
        Returns:
            Rate coefficient in m^3/s
        """
        raise NotImplementedError("Subclasses must implement get_rate_coefficient")
    
    def build_rate_function(self, reaction_id: str, **solver_kwargs) -> Callable:
        """Build a rate coefficient function for use in chemistry_parser.
        
        Args:
            reaction_id: Reaction identifier
            **solver_kwargs: Solver-specific options (cross-section file, etc.)
        
        Returns:
            Callable that takes params dict and returns rate coefficient
        """
        raise NotImplementedError("Subclasses must implement build_rate_function")


logger = logging.getLogger(__name__)


class LokiBSolver(EEDFSolver):
    """LOKI-B Boltzmann solver wrapper.

    Phase 1 implementation:
    - Builds Te-based lookup tables for a reaction using placeholder input/output.
    - Interpolates log(k) vs Te (numerically stable over wide ranges).
    - Caches tables as .npz for reuse.
    """

    def __init__(self, loki_executable: Optional[str] = None, cache_dir: Optional[Path] = None):
        """Initialize solver and verify executable.

        Args:
            loki_executable: Path to loki-b executable. If None, search PATH.
            cache_dir: Cache directory for rate tables.
        """
        super().__init__(cache_dir)
        if loki_executable is None:
            # Try common executable names from LoKI-B++ build layout.
            loki_executable = self._auto_detect_executable()
        if not loki_executable or not Path(loki_executable).exists():
            raise FileNotFoundError(
                "LoKI-B executable not found. Build LoKI-B++ (app/loki) or provide loki_executable path."
            )
        self.loki_executable = loki_executable
        self._verify_installation()
        self._rate_tables: Dict[str, tuple] = {}

    def _auto_detect_executable(self) -> Optional[str]:
        """Attempt to locate LoKI-B++ executable in common places.

        Search order:
          1. Explicit names in PATH ("loki", "loki-b", "LoKI-B")
          2. Local build folders: ./external/loki-b/LoKI-B-cpp/build/app/
          3. ./bin/ directory if user copied binary there.
        Returns first existing path or None.
        """
        import shutil
        candidates: List[str] = []
        # PATH names
        for name in ["loki", "loki-b", "LoKI-B", "loki.exe", "LoKI-B.exe"]:
            found = shutil.which(name)
            if found:
                return found
        # Local project relative paths
        rel_paths = [
            Path("external/loki-b/LoKI-B-cpp/build/app/loki"),
            Path("external/loki-b/LoKI-B-cpp/build/app/LoKI-B"),
            Path("bin/loki"),
            Path("bin/LoKI-B"),
            Path("bin/loki.exe"),
            Path("bin/LoKI-B.exe"),
        ]
        for p in rel_paths:
            if p.exists():
                return str(p)
        return None

    def _verify_installation(self) -> None:
        try:
            result = subprocess.run(
                [self.loki_executable, "--version"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode != 0:
                warnings.warn(f"LOKI-B version check failed: {result.stderr}")
        except Exception as e:
            warnings.warn(f"Could not verify LOKI-B installation: {e}")

    def _generate_input_file(self, reaction_id: str, params: Dict, cross_section_file: str) -> Path:
        """Placeholder JSON input generator for future ASCII format."""
        input_data = {
            "reaction": reaction_id,
            "electron_temperature_eV": params.get("Te_eV", 2.0),
            "reduced_field_Td": params.get("E_N_Td", 50.0),
            "cross_section_file": cross_section_file,
        }
        param_hash = hashlib.md5(json.dumps(input_data, sort_keys=True).encode()).hexdigest()[:8]
        input_file = self.cache_dir / f"loki_input_{param_hash}.json"
        with open(input_file, "w") as f:
            json.dump(input_data, f, indent=2)
        return input_file

    def _run_loki(self, input_file: Path) -> Path:
        """Invoke executable (placeholder command signature)."""
        output_file = input_file.with_suffix(".out")
        if output_file.exists():
            return output_file
        try:
            subprocess.run(
                [self.loki_executable, str(input_file), "-o", str(output_file)],
                capture_output=True,
                text=True,
                timeout=60,
                check=True,
            )
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"LOKI-B failed: {e.stderr}") from e
        except subprocess.TimeoutExpired:
            raise RuntimeError("LOKI-B timed out after 60 s")
        return output_file

    def _parse_output(self, output_file: Path) -> Dict:
        if not output_file.exists():
            raise FileNotFoundError(f"Missing LOKI-B output: {output_file}")
        with open(output_file, "r") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                raise NotImplementedError("Non-JSON output parsing not implemented yet")

    def get_rate_coefficient(self, reaction_id: str, params: Dict) -> float:
        """Return interpolated rate if table exists else raise."""
        if reaction_id not in self._rate_tables:
            raise KeyError(
                f"Rate table for reaction '{reaction_id}' not built. Call build_rate_function first."
            )
        te = params.get("Te_eV", 2.0)
        te_array, logk_array = self._rate_tables[reaction_id]
        logk = np.interp(te, te_array, logk_array)
        return float(np.exp(logk))

    def build_rate_function(
        self,
        reaction_id: str,
        cross_section_file: str,
        te_range: Optional[List[float]] = None,
        force_recompute: bool = False,
    ) -> Callable:
        if te_range is None:
            te_range = [0.5, 1.0, 2.0, 3.0, 5.0, 7.0, 10.0]
        cache_key = {
            "reaction": reaction_id,
            "xs_file": str(cross_section_file),
            "te_range": te_range,
            "version": 1,
        }
        table_hash = hashlib.md5(json.dumps(cache_key, sort_keys=True).encode()).hexdigest()[:10]
        cache_file = self.cache_dir / f"loki_table_{table_hash}.npz"

        if cache_file.exists() and not force_recompute:
            try:
                data = np.load(cache_file)
                te_array = data["te"]
                logk_array = data["logk"]
                logger.debug(f"Loaded cached table {cache_file}")
            except Exception as e:
                logger.warning(f"Cache load failed ({e}); recomputing table")
                te_array, logk_array = self._compute_table(reaction_id, cross_section_file, te_range, cache_file)
        else:
            te_array, logk_array = self._compute_table(reaction_id, cross_section_file, te_range, cache_file)

        self._rate_tables[reaction_id] = (te_array, logk_array)

        def rate_func(p: Dict) -> float:
            te = p.get("Te_eV", 2.0)
            logk = np.interp(te, te_array, logk_array)
            return float(np.exp(logk))

        return rate_func

    def _compute_table(
        self,
        reaction_id: str,
        cross_section_file: str,
        te_range: List[float],
        cache_file: Path,
    ) -> tuple:
        logk_values: List[float] = []
        for te in te_range:
            params = {"Te_eV": te}
            input_file = self._generate_input_file(reaction_id, params, cross_section_file)
            output_file = self._run_loki(input_file)
            result = self._parse_output(output_file)
            k = result.get("rate_coefficient", 0.0)
            k = max(k, 1e-30)
            logk_values.append(float(np.log(k)))
        te_array = np.array(te_range, dtype=float)
        logk_array = np.array(logk_values, dtype=float)
        try:
            np.savez(cache_file, te=te_array, logk=logk_array)
            logger.debug(f"Cached table written: {cache_file}")
        except Exception as e:
            logger.warning(f"Failed to write cache {cache_file}: {e}")
        return te_array, logk_array


class MaxwellianSolver(EEDFSolver):
    """Analytical Maxwellian EEDF approximation (fallback)."""
    
    def __init__(self, cache_dir: Optional[Path] = None):
        super().__init__(cache_dir)
        warnings.warn("Using Maxwellian approximation - less accurate than Boltzmann solver")
    
    def get_rate_coefficient(self, reaction_id: str, params: Dict) -> float:
        """Placeholder for Maxwellian rate calculation."""
        # Fallback to simple analytical form
        te = params.get("Te_eV", 2.0)
        # Example: crude power-law approximation
        return 1e-13 * (te ** 0.5)
    
    def build_rate_function(self, reaction_id: str, **solver_kwargs) -> Callable:
        """Build analytical rate function (Maxwellian assumption)."""
        def rate_func(p: Dict) -> float:
            return self.get_rate_coefficient(reaction_id, p)
        
        return rate_func


def get_solver(backend: str = "maxwellian", **kwargs) -> EEDFSolver:
    """Factory function to get EEDF solver instance.
    
    Args:
        backend: Solver backend ('loki-b', 'maxwellian')
        **kwargs: Passed to solver constructor
    
    Returns:
        EEDFSolver instance
    
    Example:
        >>> solver = get_solver('loki-b', loki_executable='/path/to/loki-b')
        >>> rate_func = solver.build_rate_function('e + Ar -> Ar+ + 2e', 
        ...                                         cross_section_file='ar_ionization.txt')
    """
    solvers = {
        "loki-b": LokiBSolver,
        "loki": LokiBSolver,  # alias
        "maxwellian": MaxwellianSolver,
    }
    
    if backend not in solvers:
        raise ValueError(f"Unknown EEDF backend: {backend}. Choose from {list(solvers.keys())}")
    
    return solvers[backend](**kwargs)
