# src/build_model_dict.py

from .config_loader import load_config
from .chemistry_parser import load_chemistry

def build_model_definition(config_path):
    """
    Builds the model_definition dictionary that GlobalModel expects.
    
    Args:
        config_path: Path to config.yml
        
    Returns:
        dict: Complete model definition for GlobalModel
    """
    # Load config
    config = load_config(config_path)
    
    # Load chemistry
    species, reactions, mass_dict = load_chemistry(config['chemistry']['absolute_path'])
    
    # Build the model definition dictionary
    model_def = {
        'name': config.get('name', 'Unnamed Model'),
        'description': config.get('description', ''),
        'species': species,
        'reactions': reactions,
        'geometry': {
            'type': config['geometry']['type'],
            'length': config['geometry']['length_m'],
            'radius': config['geometry']['radius_m'],
            'volume': 3.14159 * config['geometry']['radius_m']**2 * config['geometry']['length_m']
        },
        'constant_data': {
            'Th_K': config['parameters']['gas_temp_K'],
            'Tg_K': config['parameters']['gas_temp_K'],  # Same as Th_K for now
            'power_input_W': config['parameters']['power_W'],
            'mass': {},  # Nested mass dictionary for p['mass']['O2'] style access
            **mass_dict  # Add all mass data with mass_O2 style keys
        },
        'time_settings': {
            't_start': 0.0,
            't_end': config['parameters']['time_end_s']
        },
        'initial_values': {
            'Te_eV': config['initial_conditions']['Te_eV'],
            'pressure': config['parameters']['pressure_Pa'],
            **config['initial_conditions']['species_densities']
        },
        'transport_model': config.get('transport_model', 'none'),
        'declarations_func': lambda p: {}  # Empty for now, transport models will populate
    }
    
    return model_def
