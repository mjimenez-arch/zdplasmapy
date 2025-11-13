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
    config_dir = os.path.dirname(config_path)
    chemistry_file = config['chemistry']['file']
    config['chemistry']['absolute_path'] = os.path.join(config_dir, chemistry_file)
    
    return config