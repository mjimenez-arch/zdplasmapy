"""
config_parser.py
Loader and validator for zdplasmapy publication-centric config.yml files.
Supports optional Jinja2 templating for macros/parameter sweeps.
"""
import os
import yaml
import json

try:
    from jinja2 import Environment, FileSystemLoader
    JINJA2_AVAILABLE = True
except ImportError:
    JINJA2_AVAILABLE = False

try:
    import jsonschema
    JSONSCHEMA_AVAILABLE = True
except ImportError:
    JSONSCHEMA_AVAILABLE = False


def load_schema():
    """Load the config schema from config_schema.json"""
    schema_path = os.path.join(os.path.dirname(__file__), 'config_schema.json')
    if not os.path.isfile(schema_path):
        return None
    with open(schema_path, 'r') as f:
        return json.load(f)


def validate_config_schema(config):
    """
    Validate config against JSON schema if jsonschema is available.
    Raises ValidationError if config is invalid.
    """
    if not JSONSCHEMA_AVAILABLE:
        print("Warning: jsonschema not installed. Skipping schema validation.")
        print("  Install with: pip install jsonschema")
        return
    
    schema = load_schema()
    if schema is None:
        print("Warning: config_schema.json not found. Skipping schema validation.")
        return
    
    try:
        jsonschema.validate(instance=config, schema=schema)
        print("  [OK] Config validation passed")
    except jsonschema.ValidationError as e:
        print(f"  ✗ Config validation failed:")
        print(f"    {e.message}")
        print(f"    Path: {' -> '.join(str(p) for p in e.path)}")
        raise


def load_config(config_path, use_jinja2=False, jinja_vars=None, validate=True):
    """
    Loads and validates a zdplasmapy config.yml file.
    If use_jinja2 is True, renders with Jinja2 before parsing YAML.
    Args:
        config_path (str): Path to config.yml
        use_jinja2 (bool): Whether to use Jinja2 templating
        jinja_vars (dict): Variables for Jinja2 rendering
    Returns:
        dict: Parsed config dictionary
    """
    if not os.path.isfile(config_path):
        raise FileNotFoundError(f"Config file not found: {config_path}")
    
    if use_jinja2:
        if not JINJA2_AVAILABLE:
            raise ImportError("Jinja2 not installed. Install with 'pip install jinja2'.")
        env = Environment(loader=FileSystemLoader(os.path.dirname(config_path)))
        template = env.get_template(os.path.basename(config_path))
        rendered = template.render(jinja_vars or {})
        config = yaml.safe_load(rendered)
    else:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
    
    # Convert scientific notation strings to floats in initial_conditions
    if 'initial_conditions' in config and 'species_densities' in config['initial_conditions']:
        densities = config['initial_conditions']['species_densities']
        for species, value in densities.items():
            if isinstance(value, str):
                try:
                    densities[species] = float(value)
                except ValueError:
                    pass  # Keep as string if not convertible
    
    # Validate against schema
    if validate:
        validate_config_schema(config)
    
    # --- Chemistry file(s) flexible loading ---
    # Accepts either:
    #   chemistry:
    #     file: "./chemistry.yml"
    #   chemistry:
    #     files:
    #       - "./chemistry1.yml"
    #       - "./chemistry2.yml"
    # Or legacy: chemistry_file: "./chemistry.yml"
    chem_files = []
    if 'chemistry' in config:
        chem_section = config['chemistry']
        if isinstance(chem_section, dict):
            if 'files' in chem_section:
                # List of files
                if not isinstance(chem_section['files'], list):
                    raise ValueError("'chemistry.files' must be a list of file paths.")
                chem_files = [os.path.join(os.path.dirname(config_path), f) for f in chem_section['files']]
            elif 'file' in chem_section:
                chem_files = [os.path.join(os.path.dirname(config_path), chem_section['file'])]
            else:
                raise ValueError("'chemistry' section must have 'file' or 'files'.")
        else:
            raise ValueError("'chemistry' section must be a dict.")
    elif 'chemistry_file' in config:
        chem_files = [os.path.join(os.path.dirname(config_path), config['chemistry_file'])]
    else:
        raise ValueError("Missing required chemistry file(s): use 'chemistry.file', 'chemistry.files', or 'chemistry_file'.")

    config['chemistry_files'] = chem_files

    # Validate transport_model
    if 'transport_model' not in config:
        raise ValueError("Missing required field in config: 'transport_model'")

    return config

# Example usage:
if __name__ == "__main__":
    # Example: load config.yml in a case folder
    config = load_config("../cases/chung_1999_o2_icp/config.yml")
    print("Loaded config:", config)
