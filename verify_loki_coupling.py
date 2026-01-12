
import os
import sys

# Add project root to path
sys.path.append(os.getcwd())

from src.eedf_solver import run_eedf
import pprint

def test_loki_coupling():
    print("=== Testing LoKI-B Integration (Standalone) ===")
    
    # mocked configuration (similar to what GlobalModel sends)
    model_definition = {
        'species': ['Ar', 'e'],
        'reactions': [
            # Dummy reaction
            {
                'equation': 'e + Ar -> e + Ar',
                'process': 'Elastic',
                'k_b': 0.0
            }
        ],
        'eedf': {
            'backend': 'loki',
            'options': {
                'reduced_field_td': 100.0,
                'numerics': {
                    'energy_grid': {
                        'emax_eV': 30.0,
                        'points': 200
                    }
                }
            }
        }
    }

    request = {
        'gas': {
            'species': ['Ar'],
            'fractions': [1.0]
        },
        'field': {
            'type': 'uniform',
            'value': 50.0 
        },
        'pressure': 133.32, 
        'temperature': 300.0,
        'grid': {
            'emin': 0.0,
            'emax': 30.0,
            'points': 200
        },
        'options': model_definition['eedf']['options']
    }
    
    print("Sending request to LoKI-B...")
    try:
        result = run_eedf(model_definition, request)
        
        print("\n=== SUCCESS: LoKI-B Execution Completed ===")
        print("Result Keys:", result.keys())
        
        if 'rate_coefficients' in result:
             print("\nRate Coefficients Retrieved:")
             pprint.pprint(result['rate_coefficients'])
        else:
             print("\nWARNING: No 'rate_coefficients' in result.")
             
        if 'mean_energy' in result:
             print(f"\nMean Electron Energy: {result['mean_energy']} eV")
             
        return True
        
    except Exception as e:
        print(f"\n=== FAILURE: LoKI-B Execution Failed ===")
        print(e)
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_loki_coupling()
