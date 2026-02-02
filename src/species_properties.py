
import csv
import re
import os
import logging

logger = logging.getLogger(__name__)

class SpeciesMassParser:
    def __init__(self, csv_path=None):
        self.atom_masses = {}
        if csv_path is None:
            # Default to project data directory
            base_dir = os.path.dirname(__file__)
            csv_path = os.path.join(base_dir, "..", "data", "periodicTable.csv")
        
        self._load_periodic_table(csv_path)

    def _load_periodic_table(self, csv_path):
        if not os.path.exists(csv_path):
            logger.error(f"Periodic table CSV not found at {csv_path}")
            return

        with open(csv_path, 'r') as f:
            # Skip comments and metadata lines
            lines = [l for l in f if not l.startswith('Source') and not l.startswith('Date') and l.strip()]
            reader = csv.DictReader(lines)
            
            for row in reader:
                if 'Symbol' not in row: continue
                symbol = row['Symbol'].strip()
                try:
                    if not row['Atomic Mass (amu)']: continue
                    mass = float(row['Atomic Mass (amu)'])
                    self.atom_masses[symbol] = mass
                except ValueError:
                    continue

    def get_mass(self, formula):
        """
        Calculate mass in AMU for a chemical formula.
        Returns None if formula cannot be parsed.
        """
        # 0. Electron
        if formula == 'e': return 0.00054858
        
        # 1. Strip properties inside [] (e.g., N2[v1] -> N2)
        base = re.sub(r'\[.*?\]', '', formula)
        
        # 2. Strip charge (+, -, 2+, etc at end)
        # Handle N2+ case (charge is just appended)
        if base.endswith('+') or base.endswith('-'): 
            base = base[:-1]
        
        # Handle explicit charge like O2-
        base = re.sub(r'[+-]\d*$', '', base)
        
        # 3. Parse atoms (e.g., N2 -> N:2)
        matches = re.findall(r'([A-Z][a-z]*)(\d*)', base)
        
        if not matches:
             # Fallback: maybe it's just a raw atom name not in regex?
             # But our regex expects Capitalized symbols.
             return None

        total_mass = 0.0
        for atom, count in matches:
            if atom == 'e': continue 
            if atom == 'M': continue # Generic third body?
            
            n = int(count) if count else 1
            if atom in self.atom_masses:
                total_mass += self.atom_masses[atom] * n
            else:
                logger.warning(f"Atomic mass for element '{atom}' not found (formula: {formula}).")
                return None
        
        return total_mass
