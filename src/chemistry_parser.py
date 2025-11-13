# src/chemistry_parser.py

import yaml
import math

def _build_lambda(expr_str, safe_globals):
    """
    Converts a string expression into a callable lambda function.
    Handles shortcuts: 'Te' -> p['Te_eV'], 'Tg' -> p['Tg_K']
    
    Args:
        expr_str: String expression like "4.7e-8 * Te**0.5"
        safe_globals: Safe namespace for eval
        
    Returns:
        Callable lambda function that takes parameter dict 'p'
    """
    if isinstance(expr_str, (int, float)):
        # It's already a number, return constant function
        return lambda p: expr_str
    
    # Replace shortcuts
    processed = expr_str.replace('Te', "p['Te_eV']").replace('Tg', "p['Tg_K']")
    
    # Build lambda
    code_str = f"lambda p: {processed}"
    return eval(code_str, safe_globals)


def load_chemistry(chemistry_path):
    """
    Loads chemistry.yml and returns species list and reaction list.
    
    Args:
        chemistry_path: Path to chemistry.yml file
        
    Returns:
        tuple: (species_list, reactions_list, mass_dict)
    """
    with open(chemistry_path, 'r') as f:
        chem = yaml.safe_load(f)
    
    # Safe environment for eval
    safe_globals = {
        '__builtins__': None,
        'exp': math.exp,
        'sqrt': math.sqrt,
        'log': math.log,
        'math': math
    }
    
    # Parse species
    species_list = []
    mass_dict = {'mass': {}}  # Nested dict for p['mass']['O2'] style access
    
    for sp in chem['species']:
        name = sp['name']
        species_list.append(name)
        
        # Store masses in kg
        mass_amu = sp['mass_amu']
        mass_kg = mass_amu * 1.66054e-27
        
        # Create keys without special characters for easy access
        clean_name = name.replace('+', '').replace('-', '')
        mass_dict[f'mass_{clean_name}'] = mass_kg
        mass_dict[f'mass_{clean_name}_amu'] = mass_amu
        
        # Also add to nested dict for p['mass']['O2'] style
        mass_dict['mass'][clean_name] = mass_kg
    
    # Parse reactions
    reactions_list = []
    
    for rxn in chem['reactions']:
        # Build callable functions for rate and energy
        rate_func = _build_lambda(rxn['rate_coeff'], safe_globals)
        energy_func = _build_lambda(rxn['energy_loss'], safe_globals)
        
        reactions_list.append({
            'formula': rxn['formula'],
            'rate_coeff_func': rate_func,
            'energy_loss_func': energy_func,
            'type': rxn.get('type', 'volume'),
            'reference': rxn.get('reference', '')
        })
    
    return species_list, reactions_list, mass_dict
