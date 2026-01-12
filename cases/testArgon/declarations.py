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
    return {}
