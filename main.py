# main.py (YAML-based Version)

import os
from src.build_model_dict import build_model_definition
from src.global_model import GlobalModel

def main():
    """
    Main function to run the global plasma model using YAML configuration files.
    Automatically generates the output plot filename based on the case folder name.
    """
    # --- CHOOSE YOUR CASE ---
    # Path to the config.yml file for the case you want to run
    # Uncomment the case you want to run:
    
    config_path = 'cases/chung_1999_o2_icp/config.yml'
    # config_path = 'cases/another_case/config.yml'
    # config_path = 'cases/my_case/config.yml'
    
    # --- AUTOMATICALLY GENERATE OUTPUT FILENAME ---
    # Extract the case folder name (e.g., "chung_1999_o2_icp")
    case_folder = os.path.basename(os.path.dirname(config_path))
    output_plot_filename = f"{case_folder}_results.svg"
    
    try:
        print(f"Loading configuration from: {config_path}")
        model_definition = build_model_definition(config_path)
        print(f"Model loaded: {model_definition['name']}")
    except FileNotFoundError:
        print(f"Error: Config file '{config_path}' not found.")
        return
    except Exception as e:
        print(f"An error occurred while loading the model: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Create and run the model
    # The 'debug' flag can be toggled to show/hide detailed console output
    print("\nInitializing model...")
    model = GlobalModel(model_definition, debug=False)
    
    print("Running simulation...")
    model.run()
    
    # --- SAVE THE PLOT TO THE AUTOMATICALLY GENERATED FILENAME ---
    print(f"\nGenerating output plot: {output_plot_filename}")
    model.plot_results(output_filename=output_plot_filename)
    print(f"Done! Results saved to '{output_plot_filename}'")

if __name__ == '__main__':
    main()