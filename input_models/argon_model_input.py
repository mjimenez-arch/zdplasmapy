# argon_model_input.py (Final Corrected Version)

import math

def get_model_definition():
    species = ['Ar', 'Ar_4s', 'Ar_4p', 'Ar+', 'e']
    reactions = [
        {'formula': 'Ar + e -> Ar + e', 'rate_coeff_func': lambda p: 1.84e-8*p['Te_eV']**1.5, 'energy_loss_func': lambda p: (3/2)*p['Te_eV']*(2*p['constants']['m_e']/p['mass_Ar']), 'type': 'V'},
        {'formula': 'Ar + e -> Ar_4s + e', 'rate_coeff_func': lambda p: (5e-15*p['Te_eV']**0.74*math.exp(-11.56/p['Te_eV'])) if p['Te_eV']>0 else 0.0, 'energy_loss_func': lambda p: 11.56, 'type': 'V'},
        {'formula': 'Ar_4s + e -> Ar + e', 'rate_coeff_func': lambda p: 4.3e-16*p['Te_eV']**0.74, 'energy_loss_func': lambda p: -11.56, 'type': 'V'},
        {'formula': 'Ar + e -> Ar_4p + e', 'rate_coeff_func': lambda p: (1.4e-14*p['Te_eV']**0.71*math.exp(-13.2/p['Te_eV'])) if p['Te_eV']>0 else 0.0, 'energy_loss_func': lambda p: 13.2, 'type': 'V'},
        {'formula': 'Ar_4p + e -> Ar + e', 'rate_coeff_func': lambda p: 3.9e-16*p['Te_eV']**0.71, 'energy_loss_func': lambda p: -13.2, 'type': 'V'},
        {'formula': 'Ar_4s + e -> Ar_4p + e','rate_coeff_func': lambda p: (8.9e-13*p['Te_eV']**0.51*math.exp(-1.59/p['Te_eV'])) if p['Te_eV']>0 else 0.0, 'energy_loss_func': lambda p: 1.59, 'type': 'V'},
        {'formula': 'Ar_4p + e -> Ar_4s + e','rate_coeff_func': lambda p: 3.0e-13*p['Te_eV']**0.51, 'energy_loss_func': lambda p: -1.59, 'type': 'V'},
        {'formula': 'Ar + e -> Ar+ + 2e', 'rate_coeff_func': lambda p: (2.9e-14*p['Te_eV']**0.68*math.exp(-15.759/p['Te_eV'])) if p['Te_eV']>0 else 0.0, 'energy_loss_func': lambda p: 15.759, 'type': 'V'},
        {'formula': 'Ar_4s + e -> Ar+ + 2e','rate_coeff_func': lambda p: (6.8e-15*p['Te_eV']**0.67*math.exp(-4.2/p['Te_eV'])) if p['Te_eV']>0 else 0.0, 'energy_loss_func': lambda p: 4.2, 'type': 'V'},
        {'formula': 'Ar_4p + e -> Ar+ + 2e','rate_coeff_func': lambda p: (1.8e-13*p['Te_eV']**0.61*math.exp(-2.61/p['Te_eV'])) if p['Te_eV']>0 else 0.0, 'energy_loss_func': lambda p: 2.61, 'type': 'V'},
        # Wall Reactions
        {'formula': 'Ar+ -> Ar', 'rate_coeff_func': lambda p: p.get('Loss_Ar_plus', 0.0), 'energy_loss_func': lambda p: 2*p.get('Vs',0.0)+p['Te_eV']/2, 'type': 'W'},
        {'formula': 'Ar_4s -> Ar', 'rate_coeff_func': lambda p: p.get('Loss_Ar_4s', 0.0), 'energy_loss_func': lambda p: 0.0, 'type': 'W'},
        {'formula': 'Ar_4p -> Ar', 'rate_coeff_func': lambda p: p.get('Loss_Ar_4p', 0.0), 'energy_loss_func': lambda p: 0.0, 'type': 'W'},
    ]
    initial_values = {
        'pressure': 133.0, 'Ar_4s': 1e12, 'Ar_4p': 1e11, 'Ar+': 1e14, 'e': 1e14, 'Te_eV': 3.0,
    }
    time_settings = {'t_start': 0.0, 't_end': 0.1}
    geometry = {'L': 0.20, 'R': 0.003}
    geometry['volume'] = math.pi * geometry['R']**2 * geometry['L']
    geometry['Reff'] = 1/math.sqrt((math.pi/geometry['L'])**2 + (2.405/geometry['R'])**2)
    constant_data = {
        'Th_K': 500, 'sigma': 1.25e-20,
    }
    constant_data['Th_eV'] = constant_data['Th_K'] * 1.3807e-23 / 1.6022e-19 # kb/q_e
    constant_data['mass_Ar'] = 39.95 * 1.67e-27 # m_proton
    
    def power_input_func(t, volume): return 40.0

    def calculate_declarations(p):
        Te_eV, Th_eV, na, sigma, mass_Ar, Reff, const = \
        p['Te_eV'], p['Th_eV'], p['na'], p['sigma'], p['mass_Ar'], p['Reff'], p['constants']
        declarations = {}
        epsilon = 1e-20
        Dion = (2/3)/(na*sigma)*math.sqrt(Th_eV*const['q_e']/(math.pi*mass_Ar)) if na > epsilon else 0
        Deff = (1+Te_eV/Th_eV)*Dion

        if Reff**2 > epsilon:
            declarations['Loss_Ar_plus'] = Deff/Reff**2
            declarations['Loss_Ar_4s'] = Dion/Reff**2
            declarations['Loss_Ar_4p'] = Dion/Reff**2
        else:
            declarations.update({'Loss_Ar_plus': 0, 'Loss_Ar_4s': 0, 'Loss_Ar_4p': 0})
        
        mass_ratio = mass_Ar/(2*math.pi*const['m_e'])
        declarations['Vs'] = (Te_eV/2)*math.log(mass_ratio) if mass_ratio > 0 else 0
        return declarations

    model = {
        'constants': None, 'species': species, 'reactions': reactions,
        'initial_values': initial_values, 'time_settings': time_settings,
        'geometry': geometry, 'constant_data': constant_data,
        'power_input_func': power_input_func, 'declarations_func': calculate_declarations,
    }
    return model