# src/config_loader.py

import yaml
import os

def load_config(config_path):
    """
    Loads the main config.yml file and returns a dictionary with all settings.
    
    Args:
        config_path: Path to config.yml file
        
    Returns:
        dict: Configuration dictionary
    """
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    # Resolve chemistry file path relative to config file location
    # Parse EEDF section if present (allow under root or additional_parameters)
    eedf_config = config.get('eedf') or config.get('additional_parameters', {}).get('eedf', {})
    config['eedf'] = {
        'enabled': bool(eedf_config.get('enabled', False)),
        'backend': eedf_config.get('backend', 'loki'),
        'timestamps': eedf_config.get('timestamps', []),
        'options': eedf_config.get('options', {}),
    }