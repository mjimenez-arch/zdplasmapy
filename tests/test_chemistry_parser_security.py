import unittest
import math

from src.chemistry_parser import build_lambda as _build_lambda


class TestChemistryParserSecurity(unittest.TestCase):
    def setUp(self):
        self.safe_globals = {
            '__builtins__': None,
            'exp': math.exp,
            'sqrt': math.sqrt,
            'log': math.log,
            'math': math
        }

    def test_simple_expression(self):
        fn = _build_lambda("2.0 * Te + 3", self.safe_globals)
        value = fn({'Te_eV': 5.0, 'Tg_K': 300.0})
        self.assertEqual(value, 2.0 * 5.0 + 3)

    def test_math_function_whitelist(self):
        fn = _build_lambda("exp(Te/10.0)", self.safe_globals)
        v = fn({'Te_eV': 2.0, 'Tg_K': 300.0})
        self.assertAlmostEqual(v, math.exp(0.2))

    def test_reject_import(self):
        with self.assertRaises(ValueError):
            _build_lambda("__import__('os').system('echo hi')", self.safe_globals)

    def test_reject_attribute_chain(self):
        with self.assertRaises(ValueError):
            _build_lambda("math.__dict__", self.safe_globals)

    def test_reject_undefined_name(self):
        with self.assertRaises(ValueError):
            _build_lambda("badname + 2", self.safe_globals)

    def test_reject_non_p_subscript(self):
        with self.assertRaises(ValueError):
            _build_lambda("other['Te_eV']", self.safe_globals)

    def test_chained_subscripts_allowed(self):
        # Should allow p['mass']['O2'] style access
        fn = _build_lambda("p['mass']['O2'] + Te", self.safe_globals)
        val = fn({'mass': {'O2': 2.0}, 'Te_eV': 3.0, 'Tg_K': 300.0})
        self.assertEqual(val, 5.0)

    def test_p_get_allowed(self):
        # Should allow p.get(key, default) for optional parameters
        fn = _build_lambda("p.get('alpha', 0.5) * Te", self.safe_globals)
        val = fn({'Te_eV': 4.0, 'Tg_K': 300.0})
        self.assertEqual(val, 2.0)  # Uses default 0.5


if __name__ == '__main__':
    unittest.main()