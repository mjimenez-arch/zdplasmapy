# src/chemistry.py

class Species:
    """A simple class to hold data about a single species."""
    def __init__(self, name, mass_amu=0.0):
        self.name = name
        self.mass_amu = mass_amu

class Reaction:
    """A class to hold data about a single reaction, including its compiled functions."""
    def __init__(self, formula, rate_coeff_func, energy_loss_func, type, reference):
        self.formula = formula
        self.rate_coeff_func = rate_coeff_func
        self.energy_loss_func = energy_loss_func
        self.type = type
        self.reference = reference