# main.py (New "Smart Naming" Version)

import os
from model_parser import load_input_file
from global_model import GlobalModel

def main():
    """
    Main function to run the global plasma model.
    This version automatically generates the output plot filename based on the input file.
    """
    # --- CHOOSE YOUR MODEL ---
    # The path is now relative to the 'input_models' sub-folder.
    # Uncomment the model you want to run:
    
    input_filename = 'input_models/oxygen_flow.py'
    # input_filename = 'input_models/oxygen.py'
    # input_filename = 'input_models/argon.py'
    
    # --- AUTOMATICALLY GENERATE OUTPUT FILENAME ---
    # This extracts the base name of the file without the extension (e.g., "oxygen")
    model_name = os.path.splitext(os.path.basename(input_filename))[0]
    output_plot_filename = f"{model_name}_results.svg"
    
    try:
        print(f"Loading model definition from: {input_filename}")
        model_definition = load_input_file(input_filename)
    except FileNotFoundError:
        print(f"Error: Input file '{input_filename}' not found.")
        return
    except Exception as e:
        print(f"An error occurred while loading the model definition: {e}")
        return

    # Create and run the model
    # The 'debug' flag can be toggled to show/hide detailed console output
    model = GlobalModel(model_definition, debug=False)
    model.run()

    # --- SAVE THE PLOT TO THE AUTOMATICALLY GENERATED FILENAME ---
    print(f"\nGenerating output plot...")
    model.plot_results(output_filename=output_plot_filename)

if __name__ == '__main__':
    main()