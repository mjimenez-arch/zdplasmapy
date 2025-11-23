# src/chemistry_parser.py

import yaml
import math
import re
import ast

# Atomic masses in amu (from NIST)
ATOMIC_MASSES = {
    'H': 1.008,
    'He': 4.0026,
    'C': 12.011,
    'N': 14.007,
    'O': 15.999,
    'F': 18.998,
    'Ne': 20.180,
    'Ar': 39.948,
    'Kr': 83.798,
    'Xe': 131.29,
    'Cl': 35.45,
    'Br': 79.904,
    'I': 126.90,
    'e': 5.48579909e-4,  # electron
}

def calculate_mass_from_formula(species_name):
    """
    Automatically calculate molecular mass from species name.
    Examples:
        'O2' -> 2*15.999 = 31.998 amu
        'Ar' -> 39.948 amu
        'O2+' -> 31.998 amu (charge doesn't affect mass)
        'Ar_4s' -> 39.948 amu (excited state notation ignored)
        'e' -> 5.48579909e-4 amu
    
    Returns:
        float: mass in amu, or None if cannot parse
    """
    # Remove charge and state notation
    clean_name = species_name.replace('+', '').replace('-', '')
    clean_name = re.sub(r'_\d+[spdf]', '', clean_name)  # Remove _4s, _4p, etc.
    
    # Special case: electron
    if clean_name == 'e':
        return ATOMIC_MASSES['e']
    
    # Parse chemical formula: e.g., 'O2' -> {'O': 2}, 'Ar' -> {'Ar': 1}
    # Pattern: Element (uppercase + optional lowercase) followed by optional number
    pattern = r'([A-Z][a-z]?)(\d*)'
    matches = re.findall(pattern, clean_name)
    
    if not matches:
        return None
    
    total_mass = 0.0
    for element, count_str in matches:
        if element not in ATOMIC_MASSES:
            return None  # Unknown element
        count = int(count_str) if count_str else 1
        total_mass += ATOMIC_MASSES[element] * count
    
    return total_mass


def _build_lambda(expr_str, safe_globals):
    """Convert a rate/energy expression string into a callable without raw eval.

    **Shortcut Mappings** (applied before parsing):
      - 'Te' → "p['Te_eV']"  (electron temperature in eV)
      - 'Tg' → "p['Tg_K']"   (gas temperature in Kelvin)
    
    This allows chemistry.yml to use physics notation:
      rate_coeff: "1.5e-9 * Te**0.5"
    instead of:
      rate_coeff: "1.5e-9 * p['Te_eV']**0.5"

    **Supported syntax** (after shortcut replacement):
      - numeric literals (int/float, scientific notation)
      - arithmetic ops: + - * / ** and parentheses
      - parameter access: p['key'], p['nested']['key'], p.get('key', default)
      - whitelisted math functions: exp, sqrt, log (as exp(...) or math.exp(...))

    **Rejected** (security):
      - imports, attribute chains (except p.get), comprehensions, lambda, 
        arbitrary function calls, access to __builtins__ or other globals

    Args:
        expr_str: Expression string or numeric constant
        safe_globals: Legacy parameter (unused; kept for compatibility)

    Returns:
        Callable that takes parameter dict 'p' and returns numeric result
    """
    if isinstance(expr_str, (int, float)):
        return lambda p: expr_str

    # Apply shortcuts first (order matters: longer names first to avoid partial replacement)
    # NOTE: If your expression already contains p['Te_eV'], don't also use 'Te' - it will double-replace
    processed = expr_str.replace('Te', "p['Te_eV']").replace('Tg', "p['Tg_K']")

    # Whitelisted math function names
    allowed_func_names = {"exp": math.exp, "sqrt": math.sqrt, "log": math.log}

    # Parse expression into AST
    try:
        tree = ast.parse(processed, mode='eval')
    except SyntaxError as e:
        raise ValueError(f"Invalid expression syntax: {expr_str}. {e}") from e

    # NOTE: ast.Num/Str deprecated -> use ast.Constant. We intentionally
    # exclude comprehensions, lambda, etc.
    # ast.Attribute is allowed for p.get() and math.<func>() but validated strictly below.
    allowed_nodes = (
        ast.Expression, ast.BinOp, ast.UnaryOp, ast.Pow,
        ast.Add, ast.Sub, ast.Mult, ast.Div, ast.USub,
        ast.Constant, ast.Name, ast.Load,
        ast.Subscript, ast.Call, ast.Attribute,
        ast.Tuple, ast.List
    )

    def _validate(node, parent=None):
        if not isinstance(node, allowed_nodes):
            raise ValueError(f"Disallowed syntax: {type(node).__name__}")
        # Restrict Name usage
        if isinstance(node, ast.Name) and node.id not in {"p", "math"} and node.id not in allowed_func_names:
            raise ValueError(f"Disallowed name: {node.id}")
        # Restrict Attribute: only allowed as func in Call nodes (p.get, math.exp)
        if isinstance(node, ast.Attribute) and (not isinstance(parent, ast.Call) or parent.func != node):
            raise ValueError("Attribute access only allowed in function calls (p.get, math.func)")
        # Restrict Call usage
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Attribute):
                # Allow p.get() for safe dict access with defaults
                if isinstance(node.func.value, ast.Name) and node.func.value.id == 'p' and node.func.attr == 'get':
                    pass  # Allow p.get(key, default)
                # Only allow math.<func> where func in whitelist
                elif isinstance(node.func.value, ast.Name) and node.func.value.id == 'math':
                    if node.func.attr not in allowed_func_names:
                        raise ValueError(f"math.{node.func.attr} not whitelisted")
                else:
                    # Show what was attempted for debugging
                    try:
                        culprit = ast.unparse(node.func)
                    except:
                        culprit = f"{type(node.func.value).__name__}.{node.func.attr}"
                    raise ValueError(f"Only p.get() and math.<func>() calls allowed, got: {culprit}")
            elif isinstance(node.func, ast.Name):
                if node.func.id not in allowed_func_names:
                    raise ValueError(f"Function {node.func.id} not whitelisted")
            else:
                raise ValueError("Unsupported callable form")
        # Restrict Subscript: only p['key'] with string key
        if isinstance(node, ast.Subscript):
            # Allow chained subscripts originating from p (e.g. p['mass']['O2'])
            root = node.value
            while isinstance(root, ast.Subscript):
                root = root.value
            if not (isinstance(root, ast.Name) and root.id == 'p'):
                raise ValueError("Only p[...] chained subscripts allowed")
            # Keys must be simple string or Constant
            # (We rely on later failure if key dynamic computation attempted.)
        for child in ast.iter_child_nodes(node):
            _validate(child, parent=node)

    _validate(tree)

    code_obj = compile(tree, '<expr>', 'eval')

    def _fn(p):
        # Execution context: provide whitelisted math funcs + p
        local_ctx = {**allowed_func_names, 'p': p, 'math': math}
        return eval(code_obj, {'__builtins__': {}}, local_ctx)

    return _fn


def load_chemistry(chemistry_path):
    """
    Loads chemistry.yml and returns species list and reaction list.
    
    Args:
        chemistry_path: Path to chemistry.yml file
        
    Returns:
        tuple: (species_list, reactions_list, mass_dict)
    """
    with open(chemistry_path, 'r') as f:
        chem = yaml.safe_load(f)
    
    # Safe environment for eval
    safe_globals = {
        '__builtins__': None,
        'exp': math.exp,
        'sqrt': math.sqrt,
        'log': math.log,
        'math': math
    }
    
    # Parse species
    species_list = []
    mass_dict = {'mass': {}}  # Nested dict for p['mass']['O2'] style access
    
    for sp in chem['species']:
        name = sp['name']
        species_list.append(name)
        
        # Get mass: use provided mass_amu if available, otherwise calculate
        if 'mass_amu' in sp:
            mass_amu = sp['mass_amu']
        else:
            mass_amu = calculate_mass_from_formula(name)
            if mass_amu is None:
                raise ValueError(f"Cannot auto-calculate mass for species '{name}'. "
                                 f"Please provide 'mass_amu' explicitly or use standard chemical notation.")
        
        # Store masses in kg
        mass_kg = mass_amu * 1.66054e-27
        
        # Create keys without special characters for easy access
        clean_name = name.replace('+', '').replace('-', '')
        mass_dict[f'mass_{clean_name}'] = mass_kg
        mass_dict[f'mass_{clean_name}_amu'] = mass_amu
        
        # Also add to nested dict for p['mass']['O2'] style
        mass_dict['mass'][clean_name] = mass_kg
    
    # Parse reactions
    reactions_list = []
    
    for rxn in chem['reactions']:
        # Build callable functions for rate and energy
        rate_func = _build_lambda(rxn['rate_coeff'], safe_globals)
        energy_func = _build_lambda(rxn['energy_loss'], safe_globals)
        
        reactions_list.append({
            'formula': rxn['formula'],
            'rate_coeff_func': rate_func,
            'energy_loss_func': energy_func,
            'type': rxn.get('type', 'volume'),
            'reference': rxn.get('reference', '')
        })
    
    return species_list, reactions_list, mass_dict
