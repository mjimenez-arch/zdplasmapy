
import unittest
import os
import yaml
import tempfile
import shutil
from src.species_properties import SpeciesMassParser
from src.chemistry_parser import load_chemistry
from src.util import build_model_definition

class TestNewFeatures(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        
        # Create a dummy periodicTable.csv in test dir for isolation
        self.csv_path = os.path.join(self.test_dir, "periodicTable.csv")
        with open(self.csv_path, "w") as f:
            f.write("Source: Test\nDate: Today\n\n")
            f.write("Atomic Number,Symbol,Name,Atomic Mass (amu)\n")
            f.write("7,N,Nitrogen,14.007\n")
            f.write("8,O,Oxygen,15.999\n")
            f.write("1,H,Hydrogen,1.008\n")

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_species_mass_parser(self):
        parser = SpeciesMassParser(self.csv_path)
        
        # Test basic elements
        self.assertAlmostEqual(parser.get_mass("N"), 14.007, places=3)
        self.assertAlmostEqual(parser.get_mass("O"), 15.999, places=3)
        
        # Test molecules
        self.assertAlmostEqual(parser.get_mass("N2"), 2 * 14.007, places=3)
        self.assertAlmostEqual(parser.get_mass("H2O"), 2 * 1.008 + 15.999, places=3)
        
        # Test ions (mass should be same as neutral approx)
        self.assertAlmostEqual(parser.get_mass("N2+"), 2 * 14.007, places=3)
        self.assertAlmostEqual(parser.get_mass("O-"), 15.999, places=3)
        
        # Test compact brackets
        self.assertAlmostEqual(parser.get_mass("N2[v1]"), 2 * 14.007, places=3)
        self.assertAlmostEqual(parser.get_mass("O2[a1]"), 2 * 15.999, places=3)
        
        # Test Electron
        self.assertAlmostEqual(parser.get_mass("e"), 0.00054858, places=6)

    def test_compact_chemistry_loading(self):
        """Test loading chemistry with compact species list (strings)."""
        chem_content = {
            'species': ['N2', 'N', 'e'], # No mass_amu objects
            'reactions': [
                {'formula': 'e + N2 -> e + N + N', 'rate_coeff': '1e-12', 'energy_loss': '0.0'}
            ]
        }
        
        chem_path = os.path.join(self.test_dir, "chem_compact.yml")
        with open(chem_path, 'w') as f:
            yaml.dump(chem_content, f)
            
        # We need to hack the parser to look at OUR csv, but the parser instantiates its own.
        # Since we can't easily inject the csv path into load_chemistry without changing signature,
        # we strictly rely on the project's real CSV being present.
        # Ideally we would mock SpeciesMassParser or pass path.
        # For this integration test, we'll rely on the real one which we know exists.
        
        # BUT, load_chemistry imports SpeciesMassParser inside the function? No at module level.
        # Wait, I modified chemistry_parser to import inside? No, let's check.
        # Actually I added the import inside load_chemistry in my previous edit?
        # Yes: "    # Initialize Mass Parser / from .species_properties import SpeciesMassParser"
        
        # So it uses the default path.
        # Let's hope the real CSV covers N and O (it does).
        
        species, reactions, mass_dict = load_chemistry(chem_path)
        
        self.assertIn('N2', species)
        self.assertIn('N', species)
        self.assertIn('e', species)
        
        # Check masses were auto-populated
        # N2 mass ~ 28.014 * 1.66e-27
        self.assertGreater(mass_dict['mass']['N2'], 0.0)
        self.assertAlmostEqual(mass_dict['mass']['N2'] / 1.66054e-27, 28.014, delta=0.1)

    def test_modular_chemistry_config(self):
        """Test build_model_definition merging multiple chemistry files."""
        # Create 2 chemistry files
        chem1 = {
            'species': ['N2', 'e'],
            'reactions': [{'formula': 'e + N2 -> e + N2', 'rate_coeff': '1.0', 'energy_loss': '0'}]
        }
        chem2 = {
            'species': ['O2', 'e'], # 'e' is duplicate
            'reactions': [{'formula': 'e + O2 -> e + O2', 'rate_coeff': '2.0', 'energy_loss': '0'}]
        }
        
        p1 = os.path.join(self.test_dir, "chem1.yml")
        p2 = os.path.join(self.test_dir, "chem2.yml")
        
        with open(p1, 'w') as f: yaml.dump(chem1, f)
        with open(p2, 'w') as f: yaml.dump(chem2, f)
        
        # Create config
        config = {
            'name': 'Test Modular Config',
            'chemistry': {
                'files': ['chem1.yml', 'chem2.yml']
            },
            'parameters': {
                'pressure_Pa': 100.0,
                'power_W': 500.0,
                'gas_temp_K': 300.0,
                'time_end_s': 1.0e-3
            },
            'geometry': {
                'type': 'cylindrical',
                'radius_m': 0.1,
                'length_m': 0.2
            },
            'initial_conditions': {
                'Te_eV': 1.0,
                'species_densities': {
                    'N2': 1e20,
                    'O2': 1e19,
                    'e': 1e15
                }
            },
            'transport_model': 'declarations'
        }
        config_path = os.path.join(self.test_dir, "config.yml")
        with open(config_path, 'w') as f: yaml.dump(config, f)
        
        # We need a dummy declarations.py because build_model_definition tries to load it
        with open(os.path.join(self.test_dir, "declarations.py"), "w") as f:
            f.write("def case_declarations(p): return {}\n")
            
        # Run builder
        model_def = build_model_definition(config_path)
        
        # Check merge
        sp = model_def['species']
        rx = model_def['reactions']
        
        self.assertIn('N2', sp)
        self.assertIn('O2', sp)
        self.assertIn('e', sp)
        self.assertEqual(len(sp), 3) # N2, e, O2 (duplicates merged)
        
        self.assertEqual(len(rx), 2) # 1 from each file

if __name__ == '__main__':
    unittest.main()
