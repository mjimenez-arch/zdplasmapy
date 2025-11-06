# tests/test_parser.py (Self-Contained Version)

import unittest
import sys
import os
import numpy as np

# --- Path Hack: Add the project's root directory to the Python path ---
# This allows the test script to find and import the main project modules.
# It calculates the path to the parent directory ('../') and adds it to the front
# of the list of places Python looks for modules.
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

# Now that the path is set, we can import our modules
from model_parser import load_input_file
from global_model import GlobalModel

# --- Test Class using the 'unittest' framework ---

class TestStoichiometryParser(unittest.TestCase):
    
    # This is a special method that runs once before all tests in this class
    @classmethod
    def setUpClass(cls):
        """Loads the Oxygen model once for all tests."""
        print("\n--- Setting up tests: Loading Oxygen Model ---")
        try:
            model_definition = load_input_file('input_models/oxygen.py')
            cls.model = GlobalModel(model_definition)
        except FileNotFoundError:
            # unittest.TestCase.fail() is how you force a test to fail
            cls.fail("Could not find the Oxygen input file: 'input_models/oxygen.py'")

    def test_oxygen_species_loaded(self):
        """Checks if the species list was loaded correctly."""
        expected_species = ['O2', 'O2+', 'O', 'O+', 'O-', 'e']
        # self.assertEqual is the unittest way of writing 'assert a == b'
        self.assertEqual(self.model.species, expected_species)
        self.assertEqual(self.model.num_species, 6)

    def test_oxygen_ionization_stoichiometry(self):
        """
        Checks the stoichiometry for the main ionization reaction:
        e + O2 -> O2+ + 2e (Reaction #1)
        """
        reaction_index = 1
        net_matrix = self.model.stoich_matrix_net
        
        idx_O2 = self.model.species.index('O2')
        idx_O2_plus = self.model.species.index('O2+')
        idx_e = self.model.species.index('e')

        self.assertEqual(net_matrix[reaction_index, idx_O2], -1.0)
        self.assertEqual(net_matrix[reaction_index, idx_O2_plus], 1.0)
        self.assertEqual(net_matrix[reaction_index, idx_e], 1.0)

    def test_oxygen_dissociative_attachment_stoichiometry(self):
        """
        Checks the stoichiometry for dissociative attachment:
        e + O2 -> O + O- (Reaction #2)
        """
        reaction_index = 2
        net_matrix = self.model.stoich_matrix_net

        idx_O2 = self.model.species.index('O2')
        idx_O = self.model.species.index('O')
        idx_O_minus = self.model.species.index('O-')
        idx_e = self.model.species.index('e')

        self.assertEqual(net_matrix[reaction_index, idx_O2], -1.0)
        self.assertEqual(net_matrix[reaction_index, idx_O], 1.0)
        self.assertEqual(net_matrix[reaction_index, idx_O_minus], 1.0)
        self.assertEqual(net_matrix[reaction_index, idx_e], -1.0)

# This allows the script to be run directly from the command line
if __name__ == '__main__':
    unittest.main()