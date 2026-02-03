"""
Integration tests for LoKI-B adapter (real execution).
"""
import unittest
import os
import sys

# Ensure src is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.eedf_solver import run_eedf, _detect_loki_binary

class TestLokiIntegration(unittest.TestCase):
    def setUp(self):
        # Check if LoKI binary exists before running
        self.binary = _detect_loki_binary(None)
        if not self.binary:
            self.skipTest("LoKI-B binary not found")

    def test_loki_single_point(self):
        """Test LoKI execution with simple Argon input (single point)."""
        config = {
            'eedf': {
                'enabled': True,
                'backend': 'loki',
            }
        }
        
        request = {
            'gas': {
                'species': ['Ar'],
                'fractions': [1.0],
            },
            'field': {
                'type': 'uniform',
                'value': 100.0,
            },
            'pressure': 133.32,
            'temperature': 300.0,
            'grid': {'emin': 0.1, 'emax': 20.0, 'points': 50},
            'options': {},
        }
        
        try:
            result = run_eedf(config, request)
        except Exception as e:
            self.fail(f"LoKI execution failed: {e}")
            
        # Verify result structure
        self.assertIn('type', result)
        # Should be unwrapped to 'single'
        self.assertEqual(result['type'], 'single') 
        self.assertIn('rate_coefficients', result)
        self.assertIn('swarm_parameters', result)
        
        # Check for expected physics keys
        rates = result['rate_coefficients']
        # Depending on LXCat file, keys might vary, but usually contain 'Ionization' or similar
        # Just check it's not empty if we expect reactions (default request has no reactions though!)
        # Wait, run_eedf builds input. If no reactions requested, rate_coefficients might be empty.
        # But swarm parameters should be present.
        swarm = result['swarm_parameters']
        self.assertTrue(len(swarm) > 0, "Swarm parameters should be returned")

if __name__ == '__main__':
    unittest.main()
