"""
Quick standalone test for LoKI-B adapter.
Run this before full integration to verify LoKI works.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.eedf_solver import run_eedf

def test_loki_minimal():
    """Minimal test: call LoKI with simple Argon input."""
    
    config = {
        'eedf': {
            'enabled': True,
            'backend': 'loki',
            # Binary path auto-detected from external/LoKI-B-cpp/build/app/loki
        }
    }
    
    request = {
        'gas': {
            'species': ['Ar'],
            'fractions': [1.0],
        },
        'field': {
            'type': 'uniform',
            'value': 100.0,  # 100 Td
        },
        'pressure': 1.0,      # Pa
        'temperature': 300.0, # K
        'grid': {
            'emin': 0.01,
            'emax': 30.0,
            'points': 200,
        },
        'options': {},
    }
    
    print("Testing LoKI-B adapter...")
    print(f"Request: {request}")
    
    try:
        result = run_eedf(config, request)
        print(f"\n✓ Success!")
        print(f"  Energy grid points: {len(result['energy_grid'])}")
        print(f"  EEDF points: {len(result['eedf'])}")
        print(f"  Diagnostics keys: {list(result['diagnostics'].keys())}")
        
        if result['energy_grid'] and result['eedf']:
            import numpy as np
            mean_energy = np.average(result['energy_grid'], weights=result['eedf'])
            print(f"  Mean electron energy: {mean_energy:.3f} eV")
        
        return True
        
    except Exception as e:
        print(f"\n✗ Failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    success = test_loki_minimal()
    sys.exit(0 if success else 1)
