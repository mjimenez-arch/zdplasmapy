# global_model.py (Final Version with Integrated Stoichiometry Test)

import numpy as np
import os
from scipy.integrate import solve_ivp
import matplotlib.pyplot as plt
import re

class GlobalModel:
    def __init__(self, model_definition, debug=False):
        self.mdef = model_definition
        self.species = self.mdef['species']
        self.num_species = len(self.species)
        
        self.const = {
            'q_e': 1.6022e-19, 'kb': 1.3807e-23,
            'm_e': 9.11e-31, 'm_proton': 1.67e-27,
        }
        
        # The stoichiometric matrices are built here, using the correct parser
        self.stoich_matrix_net, self.stoich_matrix_left = self._create_stoich_matrices()
        
        self.results = None
        self.debug = debug
        self.debug_step_counter = 0
        
        # EEDF integration attributes
        self.eedf_enabled = self.mdef.get('eedf', {}).get('enabled', False)
        if self.debug:
            print(f"DEBUG: EEDF Enabled: {self.eedf_enabled}")
            print(f"DEBUG: EEDF Config: {self.mdef.get('eedf', {})}")
        self.eedf_backend = self.mdef.get('eedf', {}).get('backend', 'loki')
        self.eedf_timestamps = self.mdef.get('eedf', {}).get('timestamps', [])
        self.eedf_results = {}

        # --- NEW: RUN THE STOICHIOMETRY TEST ON INITIALIZATION IF DEBUG IS ON ---
        if self.debug:
            self._run_and_save_stoichiometry_test("stoichiometry_report.txt")

   # In global_model.py

    def _parse_formula(self, formula_part):
        """
        A new, robust parser for reaction formulas. This version uses ' + ' as an
        unambiguous delimiter, correctly handling species with charge signs.
        """
        stoich_vector = np.zeros(self.num_species)
        
        # Sort species by length, longest first.
        sorted_species = sorted(self.species, key=len, reverse=True)
        
        # --- THE CORRECTED LINE ---
        # Split the formula on ' + ' to correctly separate species.
        terms = [s.strip() for s in formula_part.split(' + ')]
        # --- END OF CORRECTION ---
        
        for term in terms:
            if not term: continue
            
            found_match = False
            for species_name in sorted_species:
                if term.endswith(species_name):
                    coeff_str = term[:-len(species_name)].strip()
                    if not coeff_str:
                        coeff = 1.0
                    else:
                        try:
                            coeff = float(coeff_str)
                        except ValueError:
                            continue
                    
                    idx = self.species.index(species_name)
                    stoich_vector[idx] += coeff
                    found_match = True
                    break 
            
            if not found_match:
                print(f"WARNING: Could not parse term '{term}' in formula part '{formula_part}'. It may not be a valid species.")

        return stoich_vector

    def _create_stoich_matrices(self):
        # ... (This function remains unchanged)
        num_reactions = len(self.mdef['reactions'])
        left_matrix = np.zeros((num_reactions, self.num_species))
        right_matrix = np.zeros((num_reactions, self.num_species))
        for i, reaction in enumerate(self.mdef['reactions']):
            formula = reaction['formula']
            reactants_str, products_str = formula.split('->')
            left_matrix[i, :] = self._parse_formula(reactants_str)
            right_matrix[i, :] = self._parse_formula(products_str)
        net_matrix = right_matrix - left_matrix
        return net_matrix, left_matrix

    def _run_and_save_stoichiometry_test(self, output_filename):
        """
        NEW: Builds a string report of the stoichiometry and saves it to a file.
        """
        print(f"--- Running stoichiometry test... Saving report to '{output_filename}' ---")
        
        report_lines = []
        
        # Header
        header = f"{'#':<3} | {'Reaction Formula':<35} |"
        for s in self.species:
            header += f" {s:<5} |"
        report_lines.append(header)
        report_lines.append("=" * len(header))
        
        # Rows
        for i, reaction in enumerate(self.mdef['reactions']):
            formula = reaction['formula']
            row_str = f"{i:<3} | {formula:<35} |"
            for j in range(len(self.species)):
                coeff = self.stoich_matrix_net[i, j]
                if coeff == 0:
                    row_str += f" {'-':<5} |"
                else:
                    row_str += f" {coeff:<+5.1f} |"
            report_lines.append(row_str)
        
        # Write the report to the file
        try:
            with open(output_filename, 'w') as f:
                f.write("\n".join(report_lines))
            print("--- Stoichiometry report successfully saved. ---")
        except IOError as e:
            print(f"!!! ERROR: Could not write stoichiometry report file. {e} !!!")

    def _get_eedf_rate_coefficient(self, reaction, t):
        """
        Retrieve EEDF-calculated rate coefficient for a specific reaction.
        Uses the result from the nearest past timestamp.
        """
        if not self.eedf_results:
            return 0.0
            
        # Find the most recent timestamp <= t
        # (Assuming eedf_results are populated in order)
        valid_ts = [ts for ts in self.eedf_results.keys() if ts <= t + 1e-9]
        if not valid_ts:
            return 0.0
            
        current_ts = max(valid_ts)
        result = self.eedf_results[current_ts]
        
        # Look up rate by process ID (defined in chemistry.yml reactions_eedf)
        # The reaction object should have a 'process' field if it's an EEDF reaction
        process_id = reaction.get('process')
        if not process_id:
            # Fallback attempts to match formula if process ID is missing (risky)
            return 0.0
            
        rate_coeffs = result.get('rate_coefficients', {})
        
        # Direct match
        if process_id in rate_coeffs:
            return rate_coeffs[process_id]
            
        # Debug / Warning
        if self.debug and self.debug_step_counter % 100 == 0:
             print(f"Warning: Process '{process_id}' not found in EEDF results. Available: {list(rate_coeffs.keys())}")
             
        return 0.0

    def _ode_system(self, t, y):
        # --- Enforce Physical Boundaries ---
        densities = np.maximum(y[:-1], 1e-10)
        electron_energy_density = max(y[-1], 1e-10)
        ne_density = densities[self.species.index('e')]
        Te_eV = (2.0 / 3.0) * electron_energy_density / ne_density

        # ... (Debug printing code remains the same) ...
        if self.debug and self.debug_step_counter < 5:
            print(f"\n--- Solver Step {self.debug_step_counter}, Time t = {t:.3e} ---")
            for i, species in enumerate(self.species): print(f"  y[{i}] ({self.species[i]:<5}): {y[i]: 0.3e}")
            print(f"  y[{self.num_species}] (Energy): {y[-1]: 0.3e}")
            print(f"  Calculated Te_eV = {Te_eV:.3e}")

        # --- Build Parameter Dictionary ---
        Y_vec = [0] + list(densities)
        params = {
            'Te_eV': Te_eV, 'densities': densities, 'Y': Y_vec, 't': t,
            'na': np.sum(densities), 'constants': self.const
        }
        # Add geometry and constant_data BEFORE calling declarations_func
        params.update(self.mdef['geometry'])
        params.update(self.mdef['constant_data'])
        
        # Compute derived geometry if not present
        if 'volume' not in params:
            R = params.get('radius_m') or params.get('R')
            L = params.get('length_m') or params.get('L')
            if R and L:
                params['volume'] = np.pi * (R**2) * L
                params['area'] = 2 * np.pi * (R**2) + 2 * np.pi * R * L
        
        # Add common aliases that chemistry functions expect
        if 'Th_K' in params and 'Tg_K' not in params:
            params['Tg_K'] = params['Th_K']  # Tg_K is alias for gas temperature
        
        try:
            declared_params = self.mdef['declarations_func'](params)
            params.update(declared_params)
        except (ValueError, ZeroDivisionError) as e: return np.full_like(y, np.nan)

        # --- EEDF logic: call backend at specified timestamps ---
        if self.eedf_enabled:
            eedf_opts = self.mdef.get('eedf', {}).get('options', {}) or {}
            for ts in self.eedf_timestamps:
                # Debug print for t=0 or close calls
                # if self.debug and self.debug_step_counter < 3:
                #      print(f"DEBUG: Checking EEDF trigger t={t}, ts={ts}, diff={abs(t-ts)}")
                
                if abs(t - ts) < 1e-9 and ts not in self.eedf_results:
                    if self.debug: print(f"DEBUG: TRIGGERING EEDF at t={t}")
                    
                    # Compute fractions for NEUTRAL species only (LoKI-B expects background gas)
                    neutral_indices = []
                    neutral_species = []
                    neutral_densities = []
                    
                    for idx, sp in enumerate(self.species):
                        # Simple heuristic: neutral if no +, no -, and not 'e'
                        if '+' not in sp and '-' not in sp and sp != 'e':
                            neutral_indices.append(idx)
                            neutral_species.append(sp)
                            neutral_densities.append(densities[idx])
                    
                    total_neutral = sum(neutral_densities)
                    if total_neutral > 1e-10:
                        # Filter out trace species (< 1ppm) to avoid LoKI-B parser issues with missing XS or tiny numbers
                        fractions = []
                        valid_species = []
                        
                        for d, sp in zip(neutral_densities, neutral_species):
                            frac = d / total_neutral
                            if frac > 1e-6:
                                fractions.append(frac)
                                valid_species.append(sp)
                        
                        # Re-normalize
                        f_sum = sum(fractions)
                        if f_sum > 0:
                            fractions = [f / f_sum for f in fractions]
                        else:
                             # Should not happen given total check, but fallback
                             valid_species = [neutral_species[0]]
                             fractions = [1.0]
                    else:
                        # Fallback to dominant species or first neutral
                        valid_species = [neutral_species[0]]
                        fractions = [1.0]

                    # Prepare EEDF request with reaction cross-section info and user options
                    request = {
                        'gas': {'species': valid_species, 'fractions': fractions},
                        'field': {
                            'type': 'uniform',
                            'value': eedf_opts.get('reduced_field_td', 100.0),
                        },
                        'pressure': params.get('gasPressure', 133.32),
                        'temperature': params.get('Th_K', 300.0),
                        'grid': {
                            'emin': eedf_opts.get('grid', {}).get('emin_eV', 0.01),
                            'emax': eedf_opts.get('grid', {}).get('emax_eV', 30.0),
                            'points': eedf_opts.get('grid', {}).get('points', 200),
                        },
                        'options': {
                            'reactions': self.mdef['reactions'],
                            'physics': eedf_opts.get('physics', {}),
                            'numerics': eedf_opts.get('numerics', {}),
                        },
                    }
                    from src.eedf_solver import run_eedf
                    if self.debug:
                        import os
                        print(f"DEBUG: CWD = {os.getcwd()}")
                        print(f"DEBUG: EEDF Output Path check = {os.path.abspath('output/eedf')}")
                        
                    result = run_eedf(self.mdef, request)
                    self.eedf_results[ts] = result
                    
                    # Debug output for EEDF results
                    if self.debug:
                        print("\n=== EEDF Results at t={:.3e} s ===".format(ts))
                        rate_coeffs = result.get('rate_coefficients', {})
                        if rate_coeffs:
                            print("Rate Coefficients from LoKI-B:")
                            for key, val in rate_coeffs.items():
                                print(f"  {key:50s}: {val:.3e} m³/s")
                        else:
                            print("  WARNING: No rate coefficients found in EEDF output!")
                        
                        # Show power balance if available
                        pb = result.get('diagnostics', {}).get('power_balance', {})
                        if pb:
                            print("\nPower Balance from LoKI-B:")
                            for key, val in pb.items():
                                print(f"  {key}: {val}")
                        print("="*60 + "\n")

        # --- Chemical Rate Calculation ---
        num_reactions = len(self.mdef['reactions'])
        reaction_rates = np.zeros(num_reactions)
        for i, reaction in enumerate(self.mdef['reactions']):
            # Use EEDF rate coefficient if available
            if reaction.get('use_eedf', False) and self.eedf_results:
                k = self._get_eedf_rate_coefficient(reaction, t)
            else:
                k = reaction['rate_coeff_func'](params)
            
            rate = k
            reactants = self.stoich_matrix_left[i, :]
            for j in range(self.num_species):
                if reactants[j] > 0: rate *= densities[j] ** reactants[j]
            reaction_rates[i] = rate

        # --- Particle Balance Equations (Chemical Part) ---
        dY_dt = np.zeros(self.num_species)
        for i in range(self.num_species): dY_dt[i] = np.sum(reaction_rates * self.stoich_matrix_net[:, i])

        # --- PLASIMO-style Pressure-Controlled Mass Flow Physics ---
        if 'flow_parameters' in self.mdef:
            fp = self.mdef['flow_parameters']
            
            rho = 0.0
            p_current = 0.0
            e_idx = self.species.index('e')

            # --- THE CORRECTED LOOP ---
            for i, s_name in enumerate(self.species):
                # Check if the species is an electron
                if i == e_idx:
                    mass_i = self.const['m_e']
                    p_current += densities[i] * self.const['kb'] * (Te_eV * self.const['q_e'] / self.const['kb'])
                else: # It's a heavy particle
                    # Build the key for the constant_data dictionary
                    mass_key = f'mass_{s_name.replace("+","").replace("-","")}'
                    if mass_key not in self.mdef['constant_data']:
                        raise KeyError(f"Mass for species '{s_name}' not found in constant_data. Please define '{mass_key}'.")
                    mass_i = self.mdef['constant_data'][mass_key]
                    p_current += densities[i] * self.const['kb'] * self.mdef['constant_data']['Th_K']
                
                rho += densities[i] * mass_i
            # --- END OF CORRECTION ---

            p_target = fp['target_pressure_Pa']
            p_ratio = p_current / p_target if p_target > 0 else 1.0
            Q_in_tot_kg_per_s = fp['total_mass_flow_kg_s']
            
            if rho > 0:
                vA_div_V = (Q_in_tot_kg_per_s / rho) * p_ratio / self.mdef['geometry']['volume']
            else:
                vA_div_V = 0

            # Apply pumping loss to ALL species (including ions and electrons)
            for i in range(self.num_species):
                dY_dt[i] -= densities[i] * vA_div_V
            
            # Add inflow source for the feedstock gases
            for i in range(len(fp['inflow_species_indices'])):
                idx = fp['inflow_species_indices'][i]
                mass_key = f'mass_{self.species[idx]}'
                mass_i = self.mdef['constant_data'][mass_key]
                inflow_rate = fp['inflow_mass_kg_s'][i] / mass_i / self.mdef['geometry']['volume']
                dY_dt[idx] += inflow_rate
        
        # --- Power Balance Equation ---
        # ... (The rest of the function remains unchanged and correct)
        if 'power_input_func' in self.mdef:
            power_W = self.mdef['power_input_func'](t, params['volume'])
        else:
            power_W = self.mdef.get('constant_data', {}).get('power_input_W', 0.0)
        Q_abs = power_W / self.const['q_e'] / params['volume']
        
        Q_loss = 0.0
        if self.debug and self.debug_step_counter < 5:
            print("\n  Power Loss Calculation (Q_loss):")
            print("  -------------------------------------------------------------------------")
            print("  # | Rate Coeff (k) | Rate (R)     | E_loss (eV)  | Q_loss_i (R*E) | Reaction")
            print("  -------------------------------------------------------------------------")

        for i, reaction in enumerate(self.mdef['reactions']):
            energy_loss = reaction['energy_loss_func'](params)
            q_loss_i = reaction_rates[i] * energy_loss
            Q_loss += q_loss_i
            if self.debug and self.debug_step_counter < 5:
                k_val = reaction['rate_coeff_func'](params)
                print(f"  {i:<2}| {k_val: 1.2e}       | {reaction_rates[i]: 1.2e}   | {energy_loss: 1.2e}    | {q_loss_i: 1.2e}     | {reaction['formula']}")

        dE_dt = Q_abs - Q_loss
        if self.debug and self.debug_step_counter < 5:
            print("  -------------------------------------------------------------------------")
            print(f"  Q_abs = {Q_abs: 1.2e}, Total Q_loss = {Q_loss: 1.2e}")
            print(f"  -> d(Energy)/dt = {dE_dt:.3e}")
            print("-"*(len(str(t))+25))
            print("-"*(len(str(t))+25))
        self.debug_step_counter += 1
        
        derivatives = np.append(dY_dt, dE_dt)
        if not np.all(np.isfinite(derivatives)):
            print("\nCRITICAL ERROR: A calculated derivative is NaN or Inf!")
        return derivatives
    
    # ... (The get_initial_conditions, run, and plot_results methods remain unchanged) ...
    def get_initial_conditions(self):
        iv = self.mdef['initial_values']
        Th_K = self.mdef['constant_data']['Th_K']
        Te_eV_init = iv.get('Te_eV', 2.0)
        Te_K_init = Te_eV_init * self.const['q_e'] / self.const['kb']
        p_Pa = iv.get('p', iv.get('pressure', 10.0))
        y0 = np.zeros(self.num_species)
        partial_pressure_of_minors = 0.0
        e_idx = self.species.index('e')
        for i, species in enumerate(self.species):
            if i == 0: continue
            if species in iv: y0[i] = iv[species]
            if i == e_idx: partial_pressure_of_minors += y0[i] * self.const['kb'] * Te_K_init
            else: partial_pressure_of_minors += y0[i] * self.const['kb'] * Th_K
        pressure_for_background_gas = p_Pa - partial_pressure_of_minors
        if pressure_for_background_gas < 0:
             raise ValueError("Sum of partial pressures of seed species is > total pressure.")
        y0[0] = pressure_for_background_gas / (self.const['kb'] * Th_K)
        ne_init = y0[e_idx]
        electron_energy_density_init = (3.0 / 2.0) * ne_init * Te_eV_init
        return np.append(y0, electron_energy_density_init)

    def run(self):
        y0_final = self.get_initial_conditions()
        if self.debug:
            print("\n" + "="*50)
            print("INITIAL CONDITIONS (at t=0) PASSED TO SOLVER")
            print("="*50)
            np.set_printoptions(formatter={'float': '{: 0.3e}'.format})
            for i, species in enumerate(self.species): print(f"  y[{i}] ({species:<5}): {y0_final[i]: 0.3e}")
            print(f"  y[{self.num_species}] (Energy): {y0_final[-1]: 0.3e}")
            print("="*50 + "\n")
        t_start = self.mdef['time_settings']['t_start']
        t_end = self.mdef['time_settings']['t_end']
        print("Starting ODE integration...")
        self.results = solve_ivp(
            self._ode_system, [t_start, t_end], y0_final,
            method='BDF', dense_output=True, rtol=1e-6, atol=1e-8
        )
        print("Integration finished.")
        print(self.results.message)

    def _calculate_Te_from_results(self, y):
        """
        Calculate electron temperature from simulation results.
        
        Args:
            y: State vector from simulation results
            
        Returns:
            tuple: (Te_eV, Te_K) - Electron temperature in eV and Kelvin
        """
        ne = y[self.species.index('e'), :] + 1e-10
        electron_energy_density = y[-1, :]
        Te_eV = (2.0/3.0) * electron_energy_density / ne
        Te_K = Te_eV * self.const['q_e'] / self.const['kb']
        return Te_eV, Te_K

    def save_results_txt(self, output_filename):
        """
        Save simulation results to a text file in gnuplot-compatible format.
        
        Args:
            output_filename (str): Path to output text file
        """
        if self.results is None or not self.results.success:
            print("No valid results to save. Simulation may have failed.")
            return
        
        t, y = self.results.t, self.results.y
        
        # Calculate Te from energy density
        Te_eV, _ = self._calculate_Te_from_results(y)
        
        with open(output_filename, 'w') as f:
            # Header with column names
            f.write("# Global Model Results\n")
            f.write(f"# Time(s)")
            for species in self.species:
                f.write(f"\t{species}(m^-3)")
            f.write(f"\tTe(eV)\n")
            
            # Data rows
            for i in range(len(t)):
                f.write(f"{t[i]:.6e}")
                for j in range(len(self.species)):
                    f.write(f"\t{y[j, i]:.6e}")
                f.write(f"\t{Te_eV[i]:.6e}\n")
        
        print(f"Results successfully saved to '{output_filename}'")

    def plot_results(self, case_name=None, output_filename=None, return_figure=False):
        """
        Generates and displays, saves, or returns plots of the simulation results.

        Args:
            case_name (str, optional): Name of the case for the plot title.
            output_filename (str, optional): Saves the plot to this file path.
            return_figure (bool, optional): If True, returns the matplotlib figure
                object instead of showing or saving it. Useful for embedding in GUIs.
        """
        if self.results is None or not self.results.success:
            print("No valid results to plot. Simulation may have failed.")
            if return_figure: return None
            return

        t, y = self.results.t, self.results.y
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 9))
        
        # Use case_name for title
        if case_name:
            fig.suptitle(f'Global Model Results: {case_name}', fontsize=16)
        else:
            fig.suptitle('Global Model Results', fontsize=16)

        for i, species in enumerate(self.species): ax1.plot(t, y[i, :], label=species)
        ax1.set_yscale('log'); ax1.set_title('Species Densities'); ax1.set_xlabel('Time (s)')
        ax1.set_ylabel('Density (m⁻³)'); ax1.set_ylim(bottom=1e8); ax1.legend()
        ax1.grid(True, which="both", ls="--")

        _, Te_K = self._calculate_Te_from_results(y)
        
        ax2.plot(t, Te_K)
        ax2.set_title('Electron Temperature'); ax2.set_xlabel('Time (s)')
        ax2.set_ylabel('Temperature (K)'); ax2.grid(True); ax2.set_ylim(bottom=0)

        fig.tight_layout(rect=[0, 0, 1, 0.96])

        # --- NEW LOGIC ---
        if return_figure:
            return fig # Return the figure object for Streamlit to use
        elif output_filename:
            fig.savefig(output_filename, dpi=150)
            print(f"Plot successfully saved to '{output_filename}'")
        else:
            plt.show() # Default behavior is to show on screen