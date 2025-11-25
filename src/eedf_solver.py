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
import logging
import numpy as np


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
