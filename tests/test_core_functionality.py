import unittest
import os
from src.config_parser import load_config

class TestConfigParser(unittest.TestCase):
    def setUp(self):
        self.good_config = os.path.join("cases", "chung1999", "config.yml")
        self.bad_config = os.path.join("cases", "chung1999", "missing.yml")

    def test_load_good_config(self):
        config = load_config(self.good_config)
        self.assertIn('chemistry_files', config)
        self.assertIsInstance(config['chemistry_files'], list)
        self.assertGreaterEqual(len(config['chemistry_files']), 1)
        self.assertIn('transport_model', config)

    def test_missing_file(self):
        with self.assertRaises(FileNotFoundError):
            load_config(self.bad_config)

    def test_missing_field(self):
        # Create a minimal config missing a required field
        import tempfile, yaml
        import jsonschema
        with tempfile.NamedTemporaryFile('w+', delete=False, suffix='.yml') as tf:
            yaml.dump({'name': 'test', 'chemistry_file': 'chemistry.yml'}, tf)
            tf.flush()
            tf.close()
            with self.assertRaises(jsonschema.exceptions.ValidationError):
                load_config(tf.name)
        os.unlink(tf.name)

if __name__ == "__main__":
    unittest.main()
