# final_model_input.py (Final Corrected Version)

import math

def get_model_definition():
    species = ['O2', 'O2+', 'O', 'O+', 'O-', 'e']
    reactions = [
        # Volume Reactions
        {'formula': 'e + O2 -> e + O2', 'rate_coeff_func': lambda p: 4.7E-8*p['Te_eV']**0.5, 'energy_loss_func': lambda p: (3/2)*p['Te_eV']*(2*p['constants']['m_e']/p['mass_O2']), 'type': 'V'},
        {'formula': 'e + O2 -> O2+ + 2e', 'rate_coeff_func': lambda p: (9.0e-16*p['Te_eV']**2*math.exp(-12.6/p['Te_eV'])) if p['Te_eV']>0 else 0.0, 'energy_loss_func': lambda p: 12.6, 'type': 'V'},
        {'formula': 'e + O2 -> O + O-', 'rate_coeff_func': lambda p: (8.8e-17*math.exp(-4.4/p['Te_eV'])) if p['Te_eV']>0 else 0.0, 'energy_loss_func': lambda p: 4.4, 'type': 'V'},
        {'formula': 'O2+ + O- -> O2 + O', 'rate_coeff_func': lambda p: 1.5e-13*(300/p['Th_K'])**0.5, 'energy_loss_func': lambda p: 0.0, 'type': 'V'},
        {'formula': 'O- + O+ -> 2O', 'rate_coeff_func': lambda p: 2.5e-13*(300/p['Th_K'])**0.5, 'energy_loss_func': lambda p: 0.0, 'type': 'V'},
        {'formula': 'e + O- -> O + 2e', 'rate_coeff_func': lambda p: (2.0e-13*math.exp(-5.5/p['Te_eV'])) if p['Te_eV']>0 else 0.0, 'energy_loss_func': lambda p: 5.5, 'type': 'V'},
        {'formula': 'e + O2 -> O- + O+ + e','rate_coeff_func': lambda p: (7.1e-17*p['Te_eV']**0.5*math.exp(-17/p['Te_eV'])) if p['Te_eV']>0 else 0.0, 'energy_loss_func': lambda p: 4.4, 'type': 'V'},
        {'formula': 'e + O2 -> O + O+ + 2e','rate_coeff_func': lambda p: (5.3e-17*p['Te_eV']**0.9*math.exp(-20/p['Te_eV'])) if p['Te_eV']>0 else 0.0, 'energy_loss_func': lambda p: 4.4, 'type': 'V'},
        {'formula': 'e + O -> O+ + 2e', 'rate_coeff_func': lambda p: (9.0e-15*p['Te_eV']**0.7*math.exp(-13.6/p['Te_eV'])) if p['Te_eV']>0 else 0.0, 'energy_loss_func': lambda p: 13.6, 'type': 'V'},
        {'formula': 'O2 + e -> 2O + e', 'rate_coeff_func': lambda p: (4.2e-15*math.exp(-5.6/p['Te_eV'])) if p['Te_eV']>0 else 0.0, 'energy_loss_func': lambda p: 5.62, 'type': 'V'},
        # Wall Reactions
        {'formula': 'O+ -> O', 'rate_coeff_func': lambda p: p.get('Oplus_loss', 0.0), 'energy_loss_func': lambda p: p.get('Vs_Oplus', 0.0), 'type': 'W'},
        {'formula': 'O2+ -> O2', 'rate_coeff_func': lambda p: p.get('O2plus_loss', 0.0), 'energy_loss_func': lambda p: p.get('Vs_O2plus', 0.0), 'type': 'W'},
        {'formula': 'O -> 0.5O2', 'rate_coeff_func': lambda p: p.get('Oloss', 0.0), 'energy_loss_func': lambda p: 0.0, 'type': 'W'},
    ]
    initial_values = {
        'p': 5.5, 'O2+': 1e12, 'O': 1e13, 'O+': 1e12, 'O-': 1e11, 'e': 1e12, 'Te_eV': 2.5,
    }
    #time_settings = {'t_start': 0.0, 't_end': 0.1}
    time_settings = {'t_start': 0.0, 't_end': 1}
    
    geometry = {'L': 0.48, 'R': 0.15}
    geometry['volume'] = math.pi * geometry['R']**2 * geometry['L']
    geometry['area'] = 2 * math.pi * geometry['R']**2 + 2 * math.pi * geometry['R'] * geometry['L']
    constant_data = {
        'Th_K': 600, 'sigma_mi': 1e-18, 'power_input_W': 58,
    }
    constant_data['mass_O2'] = 32 * 1.67e-27 # m_proton
    constant_data['mass_O'] = 16 * 1.67e-27 # m_proton

    def calculate_declarations(p):
        Te_eV, Y, R, L, Area, Th_K, sigma_mi, mass_O, mass_O2, const = \
        p['Te_eV'], p['Y'], p['R'], p['L'], p['area'], p['Th_K'], p['sigma_mi'], p['mass_O'], p['mass_O2'], p['constants']
        
        declarations = {}
        epsilon = 1e-20
        vth_O = math.sqrt(const['kb'] * Th_K / mass_O)
        declarations['Oloss'] = 0.1 * (vth_O * Area) / (4 * p['volume'])
        ub_O = math.sqrt(const['q_e'] * Te_eV / mass_O) if Te_eV > 0 else 0
        ub_Oplus = ub_O
        ub_O2plus = math.sqrt(const['q_e'] * Te_eV / mass_O2) if Te_eV > 0 else 0

        if Te_eV <= 0:
            declarations.update({'Oplus_loss': 0, 'O2plus_loss': 0, 'Vs_Oplus': 0, 'Vs_O2plus': 0}); return declarations

        K_iz1 = (9.0e-15*Te_eV**0.7*math.exp(-13.6/Te_eV)) if Te_eV > 0 else 0
        n0 = Y[1] + Y[3]
        nu_iz = K_iz1 * n0
        lambda_i = 1/(n0*sigma_mi) if n0 > epsilon else 0
        a = (2*nu_iz*lambda_i)/(math.pi*ub_O) if ub_O > epsilon else 0.0

        alpha_aver = Y[5]/Y[6] if Y[6] > epsilon else 0.0
        l = L/2
        
        ul_denominator = sigma_mi*ub_O*n0*l
        ul_div_ubO = (4*vth_O*alpha_aver)/ul_denominator if ul_denominator > epsilon else 0.0
        
        hl = ((a+ul_div_ubO**3)/(1+a))**(1/3) if (1+a) > epsilon else 0
        hr = hl
        
        deff_denominator = 2*(R**2*hl + R*L*hr)
        deff = (R**2*L)/deff_denominator if deff_denominator > epsilon else float('inf')
            
        declarations['Oplus_loss'] = ub_Oplus/deff if deff > epsilon else 0.0
        declarations['O2plus_loss'] = ub_O2plus/deff if deff > epsilon else 0.0
        
        mass_ratio_O = mass_O/(2*math.pi*const['m_e'])
        mass_ratio_O2 = mass_O2/(2*math.pi*const['m_e'])
        
        declarations['Vs_Oplus'] = (Te_eV/2)*math.log(mass_ratio_O) if mass_ratio_O > 0 else 0
        declarations['Vs_O2plus'] = (Te_eV/2)*math.log(mass_ratio_O2) if mass_ratio_O2 > 0 else 0
        
        return declarations

    model = {
        'constants': None, 'species': species, 'reactions': reactions,
        'initial_values': initial_values, 'time_settings': time_settings,
        'geometry': geometry, 'constant_data': constant_data,
        'declarations_func': calculate_declarations,
    }
    return model