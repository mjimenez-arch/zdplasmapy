"""Unit tests for `LokiBSolver` using a fake external executable.

These tests avoid calling the real LoKI-B binary. Instead they create a
temporary python script mimicking the CLI signature:
    loki-b <input.json> -o <output.json>
which writes a JSON file with a deterministic dummy rate.

We test:
- Table building & interpolation returns positive rates.
- Cache (.npz) is created and reused (no recomputation when force_recompute=False).
"""
from __future__ import annotations
import json
import tempfile
from pathlib import Path
import unittest
import numpy as np

from src.eedf_solver import LokiBSolver

FAKE_SOLVER_CODE = r"""#!/usr/bin/env python3
import sys, json, math
if len(sys.argv) < 4 or sys.argv[2] != '-o':
    print('Usage: loki-b <input.json> -o <output.json>', file=sys.stderr)
    sys.exit(1)
input_file = sys.argv[1]
output_file = sys.argv[3]
with open(input_file,'r') as f:
    data = json.load(f)
Te = float(data.get('electron_temperature_eV', 2.0))
k = 1.0e-14 * (Te ** 0.5) * math.exp(-10.0/max(Te,1e-6))  # arbitrary dummy formula
with open(output_file,'w') as f:
    json.dump({"rate_coefficient": k, "Te_eV": Te}, f)
"""

REACTION_ID = "e + O2 -> O2+ + 2 e"
CROSS_SECTION_FILE = "O2_LXCat.txt"
TE_RANGE = [0.5, 1.0, 2.0, 3.0, 5.0]

# @unittest.skip("Skipping until LoKI-B build succeeds")
class TestLokiBSolver(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.tmpdir = Path(self.tmp.name)
        self.fake_exe = self.tmpdir / "loki-b.py"
        self.fake_exe.write_text(FAKE_SOLVER_CODE, encoding="utf-8")
        self.fake_exe.chmod(0o755)
        self.cache_dir = self.tmpdir / "cache"
        self.solver = LokiBSolver(loki_executable=str(self.fake_exe), cache_dir=self.cache_dir)

    def tearDown(self):
        self.tmp.cleanup()

    def test_rate_function_positive(self):
        rate_func = self.solver.build_rate_function(
            REACTION_ID,
            cross_section_file=CROSS_SECTION_FILE,
            te_range=TE_RANGE,
            force_recompute=True,
        )
        for Te in [0.6, 1.5, 4.0]:
            k = rate_func({"Te_eV": Te})
            self.assertGreater(k, 0.0, f"Rate should be > 0 for Te={Te}")

    def test_cache_created_and_reused(self):
        # First build (force recompute) -> creates cache
        _ = self.solver.build_rate_function(
            REACTION_ID,
            cross_section_file=CROSS_SECTION_FILE,
            te_range=TE_RANGE,
            force_recompute=True,
        )
        cache_files = list(self.cache_dir.glob("loki_table_*.npz"))
        self.assertEqual(len(cache_files), 1, "Expected one cache file after initial build")
        first_cache = cache_files[0]
        first_mtime = first_cache.stat().st_mtime

        # Second build (no recompute) should reuse same file (mtime unchanged)
        _ = self.solver.build_rate_function(
            REACTION_ID,
            cross_section_file=CROSS_SECTION_FILE,
            te_range=TE_RANGE,
            force_recompute=False,
        )
        second_mtime = first_cache.stat().st_mtime
        self.assertEqual(first_mtime, second_mtime, "Cache file should not be rewritten when reusing")

    def test_get_rate_coefficient_direct(self):
        # Build table then call get_rate_coefficient
        _ = self.solver.build_rate_function(
            REACTION_ID,
            cross_section_file=CROSS_SECTION_FILE,
            te_range=TE_RANGE,
            force_recompute=True,
        )
        k = self.solver.get_rate_coefficient(REACTION_ID, {"Te_eV": 2.5})
        self.assertGreater(k, 0.0)

if __name__ == "__main__":
    unittest.main()
