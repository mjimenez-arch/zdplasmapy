# --- Declarations function registry for model-specific or default logic ---
def declarations_default(params):
    """
    Default declarations function: returns an empty dict.
    """
    return {}

# Registry mapping model names to their declarations functions
DECLARATIONS_FUNCS = {
    'default': declarations_default,
    # Add model-specific functions here, e.g.:
    # 'chung_1999': declarations_chung1999,
}
# src/transport_models.py

import yaml
import os

# Registry for available transport models
TRANSPORT_MODELS = {}

def register_transport_model(name):
    def decorator(cls):
        TRANSPORT_MODELS[name] = cls
        return cls
    return decorator

def load_transport_data(yaml_path):
    """Load static transport data from a YAML file (optional)."""
    if not os.path.isfile(yaml_path):
        return {}
    with open(yaml_path, 'r') as f:
        return yaml.safe_load(f)

def get_transport_model(name):
    """Return the transport model class for the given name."""
    if name not in TRANSPORT_MODELS:
        raise ValueError(f"Transport model '{name}' not found.")
    return TRANSPORT_MODELS[name]

# Example: Python-based transport model
@register_transport_model("chung_1999")
class Chung1999_ICPCylindrical:
    def __init__(self, geometry, params, static_data=None):
        self.geometry = geometry
        self.params = params
        self.static_data = static_data or {}

    def compute(self, state):
        # Example: compute wall loss, Bohm velocity, etc.
        # Use self.static_data for any tabulated/empirical values
        # Use self.params for case-specific overrides
        # Use self.geometry for geometry-dependent calculations
        return {
            'Oplus_loss': 0.0,  # Replace with real formula
            'O2plus_loss': 0.0,
            # Add more as needed
        }

# Example usage in your pipeline:
# transport_data = load_transport_data('transport.yml')
# model_cls = get_transport_model(config['transport_model'])
# transport_model = model_cls(config['geometry'], config['parameters'], static_data=transport_data.get(config['transport_model'], {}))
# transport_results = transport_model.compute(state)