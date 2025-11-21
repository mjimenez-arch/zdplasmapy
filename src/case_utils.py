# src/case_utils.py
"""
Utilities for discovering and managing case folders.
"""
import os

def discover_cases(cases_dir='cases'):
    """
    Discover all valid case folders in the cases/ directory.
    A valid case has a config.yml file.
    
    Returns:
        list: List of case names (subdirectory names)
    """
    if not os.path.isdir(cases_dir):
        return []
    
    cases = []
    for entry in os.listdir(cases_dir):
        case_path = os.path.join(cases_dir, entry)
        if os.path.isdir(case_path):
            config_path = os.path.join(case_path, 'config.yml')
            if os.path.isfile(config_path):
                cases.append(entry)
    
    return sorted(cases)


def get_case_config_path(case_name, cases_dir='cases'):
    """
    Get the full path to a case's config.yml file.
    
    Args:
        case_name (str): Name of the case folder
        cases_dir (str): Base cases directory
    
    Returns:
        str: Full path to config.yml
    """
    return os.path.join(cases_dir, case_name, 'config.yml')


def group_parameters(params, species_list, geometry_dict, constants_dict):
    """
    Group flat parameter dictionary into structured groups for cleaner access.
    
    Args:
        params (dict): Flat parameter dictionary
        species_list (list): List of species names
        geometry_dict (dict): Geometry parameters
        constants_dict (dict): Physical constants
    
    Returns:
        dict: Grouped parameters with keys: constants, variables, geometry, species
    """
    # Extract known variable keys
    variable_keys = ['Te_eV', 'Th_eV', 'na', 'ne', 'Ti_eV', 'Tg_K', 'Th_K']
    
    # Extract known species-specific keys (mass, sigma, etc.)
    species_keys = {}
    for key in params.keys():
        if key.startswith('mass_') or key.startswith('sigma_'):
            species_keys[key] = params[key]
    
    # Also add geometry parameters that might be in params but should be in geometry
    for key in ['R', 'L', 'radius_m', 'length_m', 'Reff', 'volume', 'area']:
        if key in params:
            geometry_dict[key] = params[key]
    
    grouped = {
        'constants': constants_dict.copy(),
        'variables': {k: params[k] for k in variable_keys if k in params},
        'geometry': geometry_dict.copy(),
        'species': species_keys.copy()
    }
    
    # Add any remaining params to variables (fallback)
    for key, value in params.items():
        if key not in variable_keys and key not in species_keys and key not in constants_dict and key not in ['R', 'L', 'radius_m', 'length_m', 'Reff', 'volume', 'area']:
            grouped['variables'][key] = value
    
    return grouped
