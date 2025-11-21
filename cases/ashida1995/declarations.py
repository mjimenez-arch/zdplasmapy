# Custom transport and geometry for Ashida 1995 Argon Model
# Implements wall loss rates and sheath potential for cylindrical geometry

import math


def compute_geometry(config):
    """
    Compute derived geometry parameters from config.
    Returns a dict with volume, Reff, and any other geometry-related values.
    """
    L = config['geometry']['length_m']
    R = config['geometry']['radius_m']
    
    volume = math.pi * R**2 * L
    
    # Effective diffusion length for cylindrical geometry
    # Reff = 1 / sqrt((pi/L)^2 + (2.405/R)^2)
    Reff = 1.0 / math.sqrt((math.pi / L)**2 + (2.405 / R)**2)
    
    return {
        'volume': volume,
        'Reff': Reff,
        'L': L,
        'R': R
    }


def compute_constant_data(config):
    """
    Compute derived constant data from config.
    Returns a dict with mass_Ar, Th_eV, and other constants.
    """
    kb = 1.3807e-23  # J/K
    q_e = 1.6022e-19  # C
    m_proton = 1.67e-27  # kg
    
    Th_K = config['parameters']['gas_temp_K']
    Th_eV = Th_K * kb / q_e
    mass_Ar = 39.95 * m_proton
    
    # Get sigma from additional_parameters if available
    sigma = config.get('additional_parameters', {}).get('sigma', 1.25e-20)
    
    return {
        'Th_eV': Th_eV,
        'Th_K': Th_K,
        'Tg_K': Th_K,
        'mass_Ar': mass_Ar,
        'sigma': sigma
    }


def power_input_func(t, volume):
    """
    Power input function (constant 40 W in this case).
    """
    return 40.0


def case_declarations(params):
    """
    Calculate transport parameters (wall loss rates, sheath potential).
    
    This function is called at each time step to compute:
    - Ion and neutral diffusion coefficients
    - Wall loss rates for Ar+, Ar_4s, Ar_4p
    - Sheath potential Vs
    """
    constants = params.get('constants', {})
    variables = params.get('variables', {})
    geometry = params.get('geometry', {})
    species = params.get('species', {})

    Te_eV = variables.get('Te_eV', 0.0)
    Th_eV = variables.get('Th_eV', 0.0)
    na = variables.get('na', 0.0)
    sigma_mi = species.get('sigma_mi', 1.0)
    mass_Ar = species.get('mass_Ar', 39.95 * 1.67e-27)
    Reff = geometry.get('Reff', 1.0)
    m_e = constants.get('m_e', 9.11e-31)
    q_e = constants.get('q_e', 1.6022e-19)

    declarations = {}
    epsilon = 1e-20

    # Ion diffusion coefficient (ambipolar at low Te/Th)
    if na > epsilon:
        Dion = (2.0/3.0) / (na * sigma_mi) * math.sqrt(Th_eV * q_e / (math.pi * mass_Ar))
    else:
        Dion = 0.0

    # Effective diffusion (ambipolar correction)
    Deff = (1.0 + Te_eV / Th_eV) * Dion if Th_eV > 0 else 0.0

    # Wall loss rates (diffusion / Reff^2)
    if Reff**2 > epsilon:
        declarations['Loss_Ar_plus'] = Deff / Reff**2
        declarations['Loss_Ar_4s'] = Dion / Reff**2
        declarations['Loss_Ar_4p'] = Dion / Reff**2
    else:
        declarations['Loss_Ar_plus'] = 0.0
        declarations['Loss_Ar_4s'] = 0.0
        declarations['Loss_Ar_4p'] = 0.0

    # Sheath potential (Bohm criterion)
    mass_ratio = mass_Ar / (2.0 * math.pi * m_e)
    if mass_ratio > 0:
        declarations['Vs'] = (Te_eV / 2.0) * math.log(mass_ratio)
    else:
        declarations['Vs'] = 0.0

    return declarations

