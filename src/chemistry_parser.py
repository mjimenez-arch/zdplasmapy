# src/chemistry_parser.py

import yaml
import math
import re

# Atomic masses in amu (from NIST)
ATOMIC_MASSES = {
    'H': 1.008,
    'He': 4.0026,
    'C': 12.011,
    'N': 14.007,
    'O': 15.999,
    'F': 18.998,
    'Ne': 20.180,
    'Ar': 39.948,
    'Kr': 83.798,
    'Xe': 131.29,
    'Cl': 35.45,
    'Br': 79.904,
    'I': 126.90,
    'e': 5.48579909e-4,  # electron
}

def calculate_mass_from_formula(species_name):
    """
    Automatically calculate molecular mass from species name.
    Examples:
        'O2' -> 2*15.999 = 31.998 amu
        'Ar' -> 39.948 amu
        'O2+' -> 31.998 amu (charge doesn't affect mass)
        'Ar_4s' -> 39.948 amu (excited state notation ignored)
        'e' -> 5.48579909e-4 amu
    
    Returns:
        float: mass in amu, or None if cannot parse
    """
    # Remove charge and state notation
    clean_name = species_name.replace('+', '').replace('-', '')
    clean_name = re.sub(r'_\d+[spdf]', '', clean_name)  # Remove _4s, _4p, etc.
    
    # Special case: electron
    if clean_name == 'e':
        return ATOMIC_MASSES['e']
    
    # Parse chemical formula: e.g., 'O2' -> {'O': 2}, 'Ar' -> {'Ar': 1}
    # Pattern: Element (uppercase + optional lowercase) followed by optional number
    pattern = r'([A-Z][a-z]?)(\d*)'
    matches = re.findall(pattern, clean_name)
    
    if not matches:
        return None
    
    total_mass = 0.0
    for element, count_str in matches:
        if element not in ATOMIC_MASSES:
            return None  # Unknown element
        count = int(count_str) if count_str else 1
        total_mass += ATOMIC_MASSES[element] * count
    
    return total_mass


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
        
        # Get mass: use provided mass_amu if available, otherwise calculate
        if 'mass_amu' in sp:
            mass_amu = sp['mass_amu']
        else:
            mass_amu = calculate_mass_from_formula(name)
            if mass_amu is None:
                raise ValueError(f"Cannot auto-calculate mass for species '{name}'. "
                                 f"Please provide 'mass_amu' explicitly or use standard chemical notation.")
        
        # Store masses in kg
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
