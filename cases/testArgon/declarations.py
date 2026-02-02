# cases/testArgon/declarations.py
# Argon plasma declarations - simpler physics than O2

import math


def case_declarations(params):
    """
    Calculate transport parameters for Argon plasma.
    Simplified model compared to O2 - mainly wall losses.
    """
    # This model is pure volume chemistry; no transport loss terms are needed.
    # Returning an empty dict leaves all declaration-driven rates at zero.
    # Reduced Electric Field: EN * sqrt(time/t0) * exp(-time/t0)
    # EN = 43 Td, t0 = 1 ms
    # params['t'] is time in seconds.
    
    # params might be flat or grouped.
    t = params.get('t')
    if t is None:
        t = params.get('variables', {}).get('t', 0.0)

    EN_peak = 43.0 # Td
    t0 = 1e-3 # s (1 ms)
    
    # Function: EN * sqrt(t/t0) * exp(-t/t0)
    # Peak is at t = 0.5 * t0. Max Value factor is ~0.4288.
    # Peak Reduced Field = 43 * 0.4288 ~= 18.44 Td.
    # The EEDF scan range (0-20 Td) is sufficient.
    if t0 > 0:
        # Avoid sqrt(negative) though t should be >= 0
        val = (t / t0)
        if val < 0: val = 0
        reduced_field = EN_peak * math.sqrt(val) * math.exp(-val)
        print(f"DEBUG: DECLARATIONS t={t:.2e}, val={val:.2f}, E/N={reduced_field:.2f}")
    else:
        reduced_field = 0.0
        
    return {
        'reduced_field_Td': reduced_field
    }
