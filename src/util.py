import importlib.util
import os
from src.config_parser import load_config
from src.chemistry_parser import load_chemistry
from src.transport_models import DECLARATIONS_FUNCS
from src.case_utils import group_parameters

def build_model_definition(config_path):
    """
    Loads config, chemistry, geometry, and builds the model_definition dict for GlobalModel.
    """
    try:
        print(f"Loading configuration from: {config_path}")
        config = load_config(config_path)
    except Exception as e:
        print(f"Error loading config: {e}")
        raise

    # --- Load and merge all chemistry files ---
    all_species = []
    all_reactions = []
    all_masses = {}
    for chem_path in config['chemistry_files']:
        print(f"Loading chemistry: {chem_path}")
        species, reactions, mass_dict = load_chemistry(chem_path)
        for s in species:
            if s not in all_species:
                all_species.append(s)
        all_reactions.extend(reactions)
        all_masses.update(mass_dict)

    print(f"Loaded species: {all_species}")
    print(f"Loaded {len(all_reactions)} reactions.")

    # --- Process geometry and compute derived values using util.py ---
    geometry_complete = compute_geometry(config.get('geometry', {}))

    # --- Build constant_data with all aliases ---
    params = config.get('parameters', {})
    gas_temp = params.get('gas_temp_K', 300.0)
    power = params.get('power_W', 0.0)
    constant_data = dict(all_masses)
    constant_data.update({
        'Th_K': gas_temp,
        'Tg_K': gas_temp,
        'Th_eV': gas_temp * 1.3807e-23 / 1.6022e-19,  # Convert K to eV
        'power_input_W': power,
    })
    for key, value in params.items():
        if key not in constant_data:
            constant_data[key] = value

    # --- Load declarations function ---
    # Two modes:
    # 1. transport_model: "declarations" -> use declarations.py from case folder
    # 2. transport_model: "<name>" -> use registered class from DECLARATIONS_FUNCS
    
    case_folder = os.path.dirname(config_path)
    transport_model = config.get('transport_model', 'declarations')
    
    if transport_model == 'declarations':
        # Load from declarations.py in case folder
        decl_path = os.path.join(case_folder, 'declarations.py')
        if not os.path.isfile(decl_path):
            raise FileNotFoundError(f"transport_model='declarations' but {decl_path} not found")
        spec = importlib.util.spec_from_file_location("case_declarations", decl_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        declarations_func = getattr(module, 'case_declarations')
        print(f"  ✓ Using custom declarations.py from: {decl_path}")
    else:
        # Load from registered transport model class
        if transport_model not in DECLARATIONS_FUNCS:
            raise ValueError(f"transport_model '{transport_model}' not found in registry. Available: {list(DECLARATIONS_FUNCS.keys())}")
        declarations_func = DECLARATIONS_FUNCS[transport_model]
        print(f"  ✓ Using registered transport class: '{transport_model}'")

    # --- Wrap declarations_func to provide grouped parameters ---
    def wrapped_declarations_func(flat_params):
        """Wrapper that converts flat params to grouped structure before calling declarations."""
        # Build physical constants dict
        phys_constants = {
            'm_e': 9.10938e-31,
            'q_e': 1.60218e-19,
            'k_B': 1.38065e-23,
            'epsilon_0': 8.85419e-12,
        }
        
        # Group parameters
        grouped = group_parameters(
            flat_params,
            all_species,
            geometry_complete,
            phys_constants
        )
        
        # Call the actual declarations function with grouped params
        return declarations_func(grouped)
    
    model_definition = {
        'species': all_species,
        'reactions': all_reactions,
        'geometry': geometry_complete,
        'constant_data': constant_data,
        'initial_values': {
            **config.get('initial_conditions', {}),
            **config.get('initial_conditions', {}).get('species_densities', {})
        },
        'time_settings': {
            't_start': 0.0,
            't_end': config.get('parameters', {}).get('time_end_s', 1.0)
        },
        'declarations_func': wrapped_declarations_func,
    }
    return model_definition
import yaml
import os

def load_key_aliases(path):
    with open(path, 'r') as f:
        return yaml.safe_load(f)

def map_keys(input_dict, aliases):
    output = {}
    for internal_key, alias_list in aliases.items():
        for alias in alias_list:
            if alias in input_dict:
                output[internal_key] = input_dict[alias]
                break
    return output

def compute_geometry(geometry):
    geometry_type = geometry.get('type', 'cylindrical')
    if geometry_type == 'cylindrical':
        R = geometry.get('radius_m') or geometry.get('R')
        L = geometry.get('length_m') or geometry.get('L')
        if R is None or L is None:
            raise ValueError(f"Cylindrical geometry requires radius_m and length_m, got: R={R}, L={L}")
        return {
            'type': 'cylindrical',
            'R': R,
            'L': L,
            'radius_m': R,
            'length_m': L,
            'volume': 3.14159265359 * (R**2) * L,
            'area': 2 * 3.14159265359 * (R**2) + 2 * 3.14159265359 * R * L
        }
    elif geometry_type == 'parallel_plate':
        area = geometry.get('area_m2') or geometry.get('area')
        gap = geometry.get('gap_m') or geometry.get('d')
        if area is None or gap is None:
            raise ValueError(f"Parallel plate geometry requires area_m2 and gap_m, got: area={area}, gap={gap}")
        return {
            'type': 'parallel_plate',
            'area': area,
            'area_m2': area,
            'gap_m': gap,
            'd': gap,
            'volume': area * gap,
            'R': None,
            'L': gap
        }
    else:
        raise ValueError(f"Unknown geometry type: {geometry_type}. Supported: 'cylindrical', 'parallel_plate'")