# model_parser.py

import importlib.util

def load_input_file(filepath):
    """
    Loads a model definition from a Python file.

    Args:
        filepath (str): The path to the Python input file.

    Returns:
        A dictionary containing the model definition.
    """
    spec = importlib.util.spec_from_file_location("model_input", filepath)
    input_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(input_module)
    
    # Assumes the file contains a function named 'get_model_definition'
    model_definition = input_module.get_model_definition()
    
    return model_definition