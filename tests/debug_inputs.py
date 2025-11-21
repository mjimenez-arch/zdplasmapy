# debug_inputs.py

#import numpy as np
from model_parser import load_input_file
from src.global_model import GlobalModel

def debug_stoichiometry(input_filename):
    """
    Loads a model input file, calculates the stoichiometric matrices,
    and prints them in a readable format for verification.
    """
    print(f"\n--- Running Stoichiometry Debugger for: {input_filename} ---\n")
    
    try:
        model_definition = load_input_file(input_filename)
        # We only need a minimal definition to build the model for this test
        # So we can pass a dummy 'debug=False'
        model = GlobalModel(model_definition, debug=False)
    except Exception as e:
        print("!!! ERROR: Failed to load or initialize the model. Please check the input file.")
        print(f"   -> {e}")
        return

    species = model.species
    reactions = model.mdef['reactions']
    net_matrix = model.stoich_matrix_net
    
    # --- Print the Stoichiometry Table ---
    
    # Header
    header = f"{'#':<3} | {'Reaction Formula':<35} |"
    for s in species:
        header += f" {s:<5} |"
    print(header)
    print("=" * len(header))
    
    # Rows
    for i, reaction in enumerate(reactions):
        formula = reaction['formula']
        row_str = f"{i:<3} | {formula:<35} |"
        for j in range(len(species)):
            coeff = net_matrix[i, j]
            # Format the coefficient for nice alignment
            if coeff == 0:
                row_str += f" {'-':<5} |"
            else:
                row_str += f" {coeff:<+5.1f} |" # Show sign, 1 decimal place
        print(row_str)
        
    print("\n--- Stoichiometry check complete. ---\n")


if __name__ == '__main__':
    # --- CHOOSE WHICH FILE TO DEBUG ---
    
    file_to_debug = 'final_model_input.py' # Oxygen Model
    #file_to_debug = 'argon_model_input.py'   # Argon Model
    
    debug_stoichiometry(file_to_debug)