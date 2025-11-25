"""
test_parser.py - Tests for chemistry parsing and stoichiometry
"""
import unittest
import os
from src.global_model import GlobalModel
from src.chemistry_parser import load_chemistry


class TestChemistryParser(unittest.TestCase):
    """Test chemistry file parsing and species order."""

    def test_oxygen_chemistry_loads(self):
        """Test that oxygen chemistry file loads successfully."""
        chem_file = 'cases/chung1999/chemistry.yml'
        if not os.path.exists(chem_file):
            self.skipTest(f"Chemistry file {chem_file} not found")
        
        species, reactions, masses = load_chemistry(chem_file)
        
        # Check that we got data back
        self.assertIsInstance(species, list)
        self.assertIsInstance(reactions, list)
        self.assertIsInstance(masses, dict)
        self.assertGreater(len(species), 0)
        self.assertGreater(len(reactions), 0)

    def test_oxygen_species_order(self):
        """Test that oxygen chemistry has expected species."""
        chem_file = 'cases/chung1999/chemistry.yml'
        if not os.path.exists(chem_file):
            self.skipTest(f"Chemistry file {chem_file} not found")
        
        species, reactions, masses = load_chemistry(chem_file)
        
        # Check electron is present
        self.assertIn('e', species, "Electron species 'e' must be in species list")
        
        # Check at least some oxygen species
        has_oxygen = any('O' in s for s in species)
        self.assertTrue(has_oxygen, "Should have oxygen-containing species")


class TestStoichiometry(unittest.TestCase):
    """Test stoichiometry matrix construction."""

    def test_stoichiometry_matrix_shape(self):
        """Test that stoichiometry matrices have correct dimensions."""
        chem_file = 'cases/chung1999/chemistry.yml'
        if not os.path.exists(chem_file):
            self.skipTest(f"Chemistry file {chem_file} not found")
        
        species, reactions, masses = load_chemistry(chem_file)
        
        # Build minimal model definition
        model_def = {
            'species': species,
            'reactions': reactions,
            'geometry': {'volume': 1.0},
            'constant_data': masses,
            'initial_values': {'Te_eV': 2.0, 'e': 1e12},
            'time_settings': {'t_start': 0, 't_end': 1e-6},
            'declarations_func': lambda p: {}
        }
        
        gm = GlobalModel(model_def)
        
        # Check matrix dimensions
        self.assertEqual(gm.stoich_matrix_net.shape, (len(reactions), len(species)))
        self.assertEqual(gm.stoich_matrix_left.shape, (len(reactions), len(species)))

    def test_charge_conservation(self):
        """Test that gas-phase reactions conserve charge (skip wall reactions)."""
        chem_file = 'cases/chung1999/chemistry.yml'
        if not os.path.exists(chem_file):
            self.skipTest(f"Chemistry file {chem_file} not found")
        
        species, reactions, masses = load_chemistry(chem_file)
        
        model_def = {
            'species': species,
            'reactions': reactions,
            'geometry': {'volume': 1.0},
            'constant_data': masses,
            'initial_values': {'Te_eV': 2.0, 'e': 1e12},
            'time_settings': {'t_start': 0, 't_end': 1e-6},
            'declarations_func': lambda p: {}
        }
        
        gm = GlobalModel(model_def)
        
        # Define charge for each species
        charges = {}
        for sp in species:
            if '+' in sp:
                charges[sp] = sp.count('+')
            elif '-' in sp:
                charges[sp] = -sp.count('-')
            elif sp == 'e':
                charges[sp] = -1
            else:
                charges[sp] = 0
        
        # Check gas-phase reactions conserve charge (skip wall reactions)
        for i, rxn in enumerate(reactions):
            formula = rxn['formula']
            # Skip wall recombination reactions (single reactant -> product without electrons)
            if '->' in formula:
                left, right = formula.split('->')
                # Wall reactions typically have form "Ion+ -> Neutral" (no electrons involved)
                if '+' not in right and 'e' not in right and '+' in left:
                    continue  # Skip wall reaction
            
            charge_change = 0
            for j, sp in enumerate(species):
                charge_change += gm.stoich_matrix_net[i, j] * charges[sp]
            
            self.assertAlmostEqual(
                charge_change, 0.0, places=10,
                msg=f"Reaction {i} ({rxn['formula']}) does not conserve charge"
            )


if __name__ == '__main__':
    unittest.main()
