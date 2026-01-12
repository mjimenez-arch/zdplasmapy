# main.py — cleaned version

import os
import matplotlib
matplotlib.use('Agg')

import sys
from src.config_parser import load_config
from src.chemistry_parser import load_chemistry
from src.global_model import GlobalModel
from src.transport_models import DECLARATIONS_FUNCS
from src.util import load_key_aliases, map_keys, compute_geometry, build_model_definition
from pathlib import Path


def main(config_path):
    """
    Main entry point for running the global plasma model using a YAML config.
    """
    try:
        model_definition = build_model_definition(config_path)
    except Exception as e:
        print(f"Error building model definition: {e}")
        return

    model = GlobalModel(model_definition, debug=True)
    model.run()
    # Extract case name from config path
    case_name = Path(config_path).parent.name
    output_filename = f"{case_name}_results.png"
    model.plot_results(case_name, output_filename)


if __name__ == "__main__":
    # Allow passing YAML file as command-line arg
    config_path = sys.argv[1] if len(sys.argv) > 1 else "cases/ashida1995/config.yml"

    if not os.path.isfile(config_path):
        print(f"Error: Config file not found: {config_path}")
        print("Usage: python main.py [path/to/config.yml]")
        sys.exit(1)

    print(f"Using config: {config_path}\n")
    main(config_path)
