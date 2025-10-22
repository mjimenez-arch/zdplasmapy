# main.py (Final Version with Model Selection)

from model_parser import load_input_file
from global_model import GlobalModel

def main():
    """
    Main function to run the global plasma model.
    Change the filename here to switch between models.
    """
    # --- CHOOSE YOUR MODEL ---
    input_filename = 'input_models/final_model_input.py' # Oxygen Model
    # input_filename = 'input_models/argon_model_input.py'   # Argon Model
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
    model = GlobalModel(model_definition, debug=True)
    model.run()

    # Plot the results
    model.plot_results()

if __name__ == '__main__':
    main()