
# tests/test_loki_input_gen.py
import unittest
import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.eedf_solver import _build_loki_input

class TestLokiInputGeneration(unittest.TestCase):
    def test_pass_through_parameters(self):
        """Test that strings like 'linspace' are passed through for scans."""
        req = {
            "gas": {"species": ["Ar"]},
            "field": {"value": "linspace(10,50,5)"},  # String scan
            "temperature": "linspace(0.03, 5.0, 300)", # String scan
            "options": {
                # Mocks for file finding to avoid disk access in unit test
                "lxcat_files": ["/tmp/ar.txt"],
            }
        }
        
        # We need to mock _find_database_files or ensure it returns something safe
        # But _build_loki_input calls _find_database_files.
        # Ideally we'd mock it, but for now we rely on the function being robust 
        # or we just check the output string.
        
        loki_in = _build_loki_input(req)
        
        self.assertIn("reducedField: linspace(10,50,5)", loki_in)
        self.assertIn("electronTemperature: linspace(0.03, 5.0, 300)", loki_in)
        self.assertIn("dataFiles:", loki_in)

if __name__ == '__main__':
    unittest.main()
