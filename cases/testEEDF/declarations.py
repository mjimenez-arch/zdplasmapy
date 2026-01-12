# cases/testEEDF/declarations.py
# Oxygen plasma with EEDF-based rate coefficients
# Based on Chung 1999 model structure

import math


def case_declarations(params):
    """
    Calculate transport parameters (wall loss rates, sheath potential).
    Uses grouped parameter structure: constants, variables, geometry, species.
    
    Args:
        params (dict): Grouped parameters with keys:
            - constants: Physical constants (m_e, q_e, etc.)
            - variables: State variables (Te_eV, Th_eV, na, etc.)
            - geometry: Geometry parameters (Reff, volume, etc.)
            - species: Species-specific constants (mass_*, sigma_*)
    
    Returns:
        dict: Transport parameters for wall reactions
    """
    # Unpack grouped parameters
    constants = params.get('constants', {})
    variables = params.get('variables', {})
    geometry = params.get('geometry', {})
    species = params.get('species', {})
    
    Te_eV = variables.get('Te_eV', 1.0)
    Th_eV = variables.get('Th_eV', 0.03)
    na = variables.get('na', 1e20)
    
    # Species-specific parameters
    mass_O = species.get('mass_O', 16.0 * 1.67e-27)
    mass_O2 = species.get('mass_O2', 32.0 * 1.67e-27)
    sigma_mi = species.get('sigma_mi', 5e-19)
    
    # Geometry
    Reff = geometry.get('Reff', 0.01)
    
    # Physical constants
    m_e = constants.get('m_e', 9.10938e-31)
    q_e = constants.get('q_e', 1.60218e-19)
    
    declarations = {}
    epsilon = 1e-20
    
    # Ion diffusion coefficient (ambipolar approximation)
    if na > epsilon and sigma_mi > 0:
        Dion = (2.0/3.0) / (na * sigma_mi) * math.sqrt(Th_eV * q_e / (math.pi * mass_O2))
    else:
        Dion = 0.0
    
    # Effective diffusion (ambipolar correction)
    if Th_eV > 0:
        Deff = (1.0 + Te_eV / Th_eV) * Dion
    else:
        Deff = Dion
    
    # Wall loss rates (diffusion / Reff^2)
    if Reff**2 > epsilon:
        declarations['Oplus_loss'] = Deff / Reff**2
        declarations['O2plus_loss'] = Deff / Reff**2
        declarations['Oloss'] = Dion / Reff**2
    else:
        declarations['Oplus_loss'] = 0.0
        declarations['O2plus_loss'] = 0.0
        declarations['Oloss'] = 0.0
    
    # Sheath potential (Bohm criterion for O+)
    mass_ratio = mass_O / (2.0 * math.pi * m_e)
    if mass_ratio > 0:
        Vs_Oplus = (Te_eV / 2.0) * math.log(mass_ratio)
    else:
        Vs_Oplus = 0.0
    
    # Sheath potential for O2+
    mass_ratio_O2 = mass_O2 / (2.0 * math.pi * m_e)
    if mass_ratio_O2 > 0:
        Vs_O2plus = (Te_eV / 2.0) * math.log(mass_ratio_O2)
    else:
        Vs_O2plus = 0.0
    
    declarations['Vs_Oplus'] = Vs_Oplus
    declarations['Vs_O2plus'] = Vs_O2plus
    
    return declarations
