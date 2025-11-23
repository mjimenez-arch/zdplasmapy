# src/eedf_solver.py
"""
EEDF (Electron Energy Distribution Function) solver interface.

Provides pluggable backend support for:
  - LOKI-B (Kinetic Boltzmann solver)
  - Analytical approximations (Maxwellian)
  - Future: BOLSIG+, Bolos, etc.

Generates electron impact rate coefficients as functions of Te and other plasma parameters.
"""

import subprocess
import json
import os
import hashlib
from pathlib import Path
from typing import Dict, Callable, Optional, List
import warnings


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


class LokiBSolver(EEDFSolver):
    """LOKI-B Boltzmann solver wrapper."""
    
    def __init__(self, loki_executable: Optional[str] = None, cache_dir: Optional[Path] = None):
        """Initialize LOKI-B solver.
        
        Args:
            loki_executable: Path to loki-b executable. If None, searches PATH.
            cache_dir: Directory for caching lookup tables.
        """
        super().__init__(cache_dir)
        
        # Find LOKI-B executable
        if loki_executable is None:
            loki_executable = self._find_executable("loki-b")
        
        if not loki_executable or not Path(loki_executable).exists():
            raise FileNotFoundError(
                "LOKI-B executable not found. Install loki-b-cpp and ensure it's in PATH, "
                "or specify path with loki_executable='path/to/loki-b'"
            )
        
        self.loki_executable = loki_executable
        self._verify_installation()
    
    def _find_executable(self, name: str) -> Optional[str]:
        """Search for executable in PATH."""
        import shutil
        return shutil.which(name)
    
    def _verify_installation(self):
        """Verify LOKI-B is installed and working."""
        try:
            result = subprocess.run(
                [self.loki_executable, "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode != 0:
                warnings.warn(f"LOKI-B executable found but version check failed: {result.stderr}")
        except Exception as e:
            warnings.warn(f"Could not verify LOKI-B installation: {e}")
    
    def _generate_input_file(self, reaction_id: str, params: Dict, cross_section_file: str) -> Path:
        """Generate LOKI-B input file for a reaction.
        
        Args:
            reaction_id: Reaction identifier
            params: Plasma parameters
            cross_section_file: Path to cross-section data
        
        Returns:
            Path to generated input file
        """
        # TODO: Generate LOKI-B input format
        # This is a placeholder - actual format depends on LOKI-B requirements
        input_data = {
            "reaction": reaction_id,
            "electron_temperature_eV": params.get("Te_eV", 2.0),
            "reduced_field_Td": params.get("E_N_Td", 50.0),
            "cross_section_file": cross_section_file
        }
        
        # Create unique filename based on parameters
        param_hash = hashlib.md5(json.dumps(input_data, sort_keys=True).encode()).hexdigest()[:8]
        input_file = self.cache_dir / f"loki_input_{param_hash}.json"
        
        with open(input_file, 'w') as f:
            json.dump(input_data, f, indent=2)
        
        return input_file
    
    def _run_loki(self, input_file: Path) -> Path:
        """Run LOKI-B solver.
        
        Args:
            input_file: Path to LOKI-B input file
        
        Returns:
            Path to LOKI-B output file
        """
        output_file = input_file.with_suffix(".out")
        
        # Check if cached result exists
        if output_file.exists():
            return output_file
        
        # Run LOKI-B
        try:
            result = subprocess.run(
                [self.loki_executable, str(input_file), "-o", str(output_file)],
                capture_output=True,
                text=True,
                timeout=60,
                check=True
            )
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"LOKI-B failed: {e.stderr}") from e
        except subprocess.TimeoutExpired:
            raise RuntimeError("LOKI-B timed out after 60 seconds")
        
        return output_file
    
    def _parse_output(self, output_file: Path) -> Dict:
        """Parse LOKI-B output file.
        
        Args:
            output_file: Path to LOKI-B output
        
        Returns:
            Dict with rate coefficients and EEDF data
        """
        # TODO: Implement actual LOKI-B output parsing
        # This is a placeholder - format depends on LOKI-B output
        if not output_file.exists():
            raise FileNotFoundError(f"LOKI-B output not found: {output_file}")
        
        with open(output_file, 'r') as f:
            # Placeholder: assume JSON output
            try:
                data = json.load(f)
                return data
            except json.JSONDecodeError:
                # If not JSON, implement custom parser
                raise NotImplementedError("LOKI-B output parser not yet implemented")
    
    def get_rate_coefficient(self, reaction_id: str, params: Dict) -> float:
        """Compute rate coefficient using LOKI-B.
        
        Args:
            reaction_id: Reaction identifier
            params: Plasma parameters
        
        Returns:
            Rate coefficient in m^3/s
        """
        # TODO: Implement lookup from precomputed table or on-demand calculation
        raise NotImplementedError("get_rate_coefficient needs implementation")
    
    def build_rate_function(self, reaction_id: str, cross_section_file: str) -> Callable:
        """Build rate coefficient function using LOKI-B lookup table.
        
        Args:
            reaction_id: Reaction identifier
            cross_section_file: Path to cross-section data file
        
        Returns:
            Callable that takes params dict and returns rate coefficient
        """
        # Generate lookup table covering typical parameter range
        # TODO: Implement adaptive grid or user-specified range
        te_range = [0.5, 1.0, 2.0, 3.0, 5.0, 10.0]  # eV
        
        lookup_table = {}
        for te in te_range:
            params = {"Te_eV": te}
            input_file = self._generate_input_file(reaction_id, params, cross_section_file)
            output_file = self._run_loki(input_file)
            result = self._parse_output(output_file)
            lookup_table[te] = result.get("rate_coefficient", 0.0)
        
        # Return interpolation function
        def rate_func(p: Dict) -> float:
            """Interpolated rate coefficient from LOKI-B lookup table."""
            import numpy as np
            te = p.get("Te_eV", 2.0)
            
            # Simple linear interpolation (upgrade to scipy.interp1d if needed)
            te_array = np.array(list(lookup_table.keys()))
            rate_array = np.array(list(lookup_table.values()))
            
            return np.interp(te, te_array, rate_array)
        
        return rate_func


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
        "maxwellian": MaxwellianSolver,
    }
    
    if backend not in solvers:
        raise ValueError(f"Unknown EEDF backend: {backend}. Choose from {list(solvers.keys())}")
    
    return solvers[backend](**kwargs)
