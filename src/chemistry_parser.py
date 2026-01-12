"""
Chemistry file parser for zdplasmapy.
Loads species, reactions, and cross-section data from YAML files.
"""

import yaml
import os
import ast
import re
import numpy as np


def _validate_ast(tree, safe_globals):
    """
    Validate AST to ensure expression is safe before eval.
    Raises ValueError if expression contains dangerous patterns.
    
    Allowed patterns:
    - Arithmetic: BinOp, UnaryOp with +, -, *, /, **, etc.
    - Constants: Constant (numbers, True/False/None)
    - Comparisons: Compare (<, >, ==, etc.)
    - Parameter access: Name 'p', Subscript on 'p' (p['key'], p['x']['y']), 
                        Attribute on 'p' (p.get), Call on p.get
    - Whitelisted names: Functions/constants from safe_globals
    - Whitelisted functions: Calls to functions in safe_globals
    
    Blocked patterns:
    - Import/ImportFrom
    - Attribute access (except p.get)
    - Call to non-whitelisted functions
    - Subscript on non-p variables
    - Undefined Name references
    """
    for node in ast.walk(tree):
        # Block imports
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            raise ValueError(f"Import statements not allowed in expressions")
        
        # Block dangerous function calls
        if isinstance(node, ast.Call):
            # Whitelist: Call to Name or Attribute
            if isinstance(node.func, ast.Name):
                # Must be in safe_globals
                if node.func.id not in safe_globals:
                    raise ValueError(f"Function '{node.func.id}' not in safe globals")
            elif isinstance(node.func, ast.Attribute):
                # Only allow p.get() pattern
                if isinstance(node.func.value, ast.Name) and node.func.value.id == 'p' and node.func.attr == 'get':
                    # p.get(...) is allowed
                    pass
                else:
                    raise ValueError(f"Attribute call not allowed")
            else:
                raise ValueError(f"Complex function calls not allowed")
        
        # Block attribute access (except p.get which is handled in Call)
        if isinstance(node, ast.Attribute):
            # p.get is only allowed as part of Call, not standalone
            if not (isinstance(node.value, ast.Name) and node.value.id == 'p' and node.attr == 'get'):
                raise ValueError(f"Attribute access not allowed")
        
        # Block subscript on non-p variables
        if isinstance(node, ast.Subscript):
            # Only allow p[...] at the root of subscript chain
            base = node.value
            while isinstance(base, ast.Subscript):
                base = base.value
            if isinstance(base, ast.Name):
                if base.id != 'p':
                    raise ValueError(f"Subscript access to '{base.id}' not allowed (only 'p' allowed)")
            elif not isinstance(base, ast.Name):
                raise ValueError(f"Subscript access to non-Name not allowed")
        
        # Block undefined Name references
        if isinstance(node, ast.Name):
            # Allowed: 'p' or names in safe_globals or common parameter shorthands
            if node.id == 'p':
                pass  # Parameter access is allowed
            elif node.id in safe_globals:
                pass  # Function/constant in safe_globals
            elif node.id in ('Te', 'Tg', 'Te_eV', 'Tg_K'):
                # Common parameter name shorthands - passed as p dict keys
                pass
            elif node.id not in ('None', 'True', 'False'):
                raise ValueError(f"Name '{node.id}' not defined")


def _replace_shorthands(expr_str):
    """
    Replace parameter shorthands with proper p dict access.
    Uses regex to avoid replacing inside string literals.
    
    Replacements:
    - Te -> p['Te_eV']
    - Tg -> p.get('Tg_K', p.get('Th_K', 300))
    
    Only replaces whole word boundaries to avoid replacing inside strings.
    """
    # Replace Te with p['Te_eV'] but only as whole word
    expr_str = re.sub(r'\bTe\b', "p['Te_eV']", expr_str)
    # Replace Tg with p.get('Tg_K', p.get('Th_K', 300)) but only as whole word
    expr_str = re.sub(r'\bTg\b', "p.get('Tg_K', p.get('Th_K', 300))", expr_str)
    return expr_str


def _build_lambda(expr_str, safe_globals):
    """
    Build a lambda function from string expression with AST validation.
    
    Args:
        expr_str: String expression (e.g., "2.0 * Te + 3") or numeric constant
        safe_globals: Dictionary of safe functions/constants to use
    
    Returns:
        Lambda function that takes params dict 'p' and returns computed value
        
    Raises:
        ValueError: If expression contains unsafe patterns
        SyntaxError: If expression is not valid Python
    """
    # Handle numeric constants
    if isinstance(expr_str, (int, float)):
        return lambda p: float(expr_str)
    
    expr = expr_str.strip()
    
    # Apply common shorthands: Te -> p['Te_eV'], Tg -> p.get('Tg_K', ...)
    # Use regex to only replace whole word boundaries
    expr = _replace_shorthands(expr)
    
    # Parse expression as AST
    try:
        tree = ast.parse(f"lambda p: {expr}", mode='eval')
    except SyntaxError as e:
        raise SyntaxError(f"Invalid expression syntax: {e}")
    
    # Validate AST for safety
    _validate_ast(tree, safe_globals)
    
    # If validation passes, eval is safe
    # Use safe_globals as both globals and locals, so functions are accessible
    return eval(f"lambda p: {expr}", safe_globals)


# Public alias for testing
build_lambda = _build_lambda


def load_chemistry(chemistry_path):
    """
    Load chemistry file (YAML format) and return species list, reactions, and masses.
    Supports both standard reactions and EEDF cross-section reactions.
    
    Args:
        chemistry_path: Path to chemistry.yml file
        
    Returns:
        tuple: (species_list, reactions_list, mass_dict)
    """
    with open(chemistry_path, 'r') as f:
        chem = yaml.safe_load(f)
    
    import os
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    
    # Parse species
    species_list = []
    mass_dict = {'mass': {}}
    for sp in chem['species']:
        name = sp['name']
        mass_amu = sp['mass_amu']
        species_list.append(name)
        # Mass keys: strip charge symbols for lookup
        clean_name = name.replace('+', '').replace('-', '')
        mass_dict['mass'][clean_name] = mass_amu * 1.66054e-27  # Convert to kg
    
    # Safe globals for lambda eval
    safe_globals = {
        'exp': np.exp,
        'log': np.log,
        'sqrt': np.sqrt,
        'abs': abs,
        'min': min,
        'max': max,
        'np': np,
    }
    
    def _build_lambda_with_shorthand(expr, safe_globals):
        """Build a callable from a string expression or number, with Te/Tg shorthand."""
        if isinstance(expr, (int, float)):
            return lambda p: float(expr)
        elif isinstance(expr, str):
            # Use module-level validated _build_lambda (already does shorthand replacement)
            return _build_lambda(expr, safe_globals)
        else:
            raise ValueError(f"Invalid expression type: {type(expr)}")
    
    reactions_list = []
    
    # Process EEDF reactions first (if present)
    if 'reactions_eedf' in chem:
        eedf_section = chem['reactions_eedf']
        cs_file = eedf_section['file']
        # Resolve path relative to project root
        if not os.path.isabs(cs_file):
            cs_file = os.path.join(project_root, cs_file)
        
        for eedf_rxn in eedf_section.get('reactions', []):
            formula = eedf_rxn['formula']
            process = eedf_rxn['process']
            energy_loss = eedf_rxn.get('energy_loss', 0.0)
            rxn_type = eedf_rxn.get('type', 'volume')
            
            # Build dummy lambda for EEDF (will be replaced at runtime)
            rate_func = lambda p: 0.0  # Placeholder
            energy_func = _build_lambda_with_shorthand(energy_loss, safe_globals)
            
            reactions_list.append({
                'formula': formula,
                'rate_coeff': 'eedf',
                'rate_coeff_func': rate_func,
                'energy_loss_func': energy_func,
                'type': rxn_type,
                'reference': eedf_section.get('reference', ''),
                'use_eedf': True,
                'cross_section': cs_file,
                'process_id': process,
            })
    
    # Process standard reactions
    for rxn in chem.get('reactions', []):
        rate_coeff = rxn['rate_coeff']
        rate_func = _build_lambda(rate_coeff, safe_globals)
        energy_func = _build_lambda(rxn['energy_loss'], safe_globals)
        
        reactions_list.append({
            'formula': rxn['formula'],
            'rate_coeff': rate_coeff,
            'rate_coeff_func': rate_func,
            'energy_loss_func': energy_func,
            'type': rxn.get('type', 'volume'),
            'reference': rxn.get('reference', ''),
            'use_eedf': False,
        })
    
    return species_list, reactions_list, mass_dict
