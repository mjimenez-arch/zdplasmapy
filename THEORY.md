# Theory and Implementation of the Global Model Engine

This document explains how the Python code in `global_model.py` translates a set of reaction formulas and rate coefficients into a system of Ordinary Differential Equations (ODEs) that can be solved numerically.

## 1. The Core Physical Model

The model is a **0D Global Model**, which means we assume the plasma is a spatially uniform "well-mixed reactor." We solve two fundamental conservation laws:

1.  **Particle Balance:** For each species `i` in the plasma, the rate of change of its density `n_i` is the sum of all creation rates minus the sum of all loss rates.
2.  **Power Balance:** The rate of change of the total electron energy density is the absorbed power from the external source minus the sum of all power loss channels.

## 2. The Particle Balance Equation

The particle balance equation for a single species `i` is written as:

$$
\frac{d n_i}{dt} = \sum_{j} (\text{Creation Rates})_j - \sum_{k} (\text{Loss Rates})_k
$$

Our code generalizes this using the concept of a **stoichiometric coefficient**. For a given reaction `j`, the net change of species `i` is described by its stoichiometric coefficient, `S_{ij}`.

### From Reaction Formula to Stoichiometric Matrix

The engine's first job is to parse the reaction formulas from the input file and build a **net stoichiometric matrix**, `S`.

Consider a generic reaction `j`:
`aA + bB -> cC + dD`

The `_parse_formula` and `_create_stoich_matrices` functions in `global_model.py` perform the following steps for each reaction `j`:

1.  **Create a "Left" (Reactant) Vector (`L_j`):** For the example above, this vector would have a value of `a` at the index for species `A`, `b` at the index for `B`, and 0 everywhere else.
2.  **Create a "Right" (Product) Vector (`R_j`):** This vector would have `c` at the index for `C`, `d` for `D`, and 0 elsewhere.
3.  **Calculate the Net Change Vector (`S_j`):** The net change for reaction `j` is simply `S_j = R_j - L_j`.

By stacking these row vectors `S_j` for all reactions, we form the **net stoichiometric matrix `S`**. The element `S_{ij}` represents the net number of particles of species `i` created (if positive) or destroyed (if negative) by one instance of reaction `j`.

### From Rate Coefficients to the Reaction Rate Vector

The **rate `R_j`** of a reaction `j` (in units of `m⁻³s⁻¹`) is calculated from the law of mass action. For our example `aA + bB -> cC + dD`, the rate is:

$$
R_j = k_j \cdot [A]^a \cdot [B]^b
$$

where `k_j` is the reaction rate coefficient (in units of `m³(a+b-1)s⁻¹`) and `[X]` is the density of species `X`.

The `_ode_system` function in `global_model.py` calculates a **reaction rate vector `R`** where each element `R_j` is computed as follows:

```python
# Simplified logic from _ode_system
rate = k_j # The rate coefficient from the input file
reactants = self.stoich_matrix_left[j, :]
for species_idx in range(num_species):
    if reactants[species_idx] > 0:
        rate *= densities[species_idx] ** reactants[species_idx]
reaction_rates[j] = rate
```

### Assembling the System of ODEs

With the stoichiometric matrix `S` and the reaction rate vector `R`, the complete system of ODEs for all `N` species densities can be expressed in a single, elegant matrix-vector product.

The rate of change of the density of species `i` is the sum of the rates of all reactions, each weighted by its stoichiometric coefficient for that species:

$$
\frac{d n_i}{dt} = \sum_{j=1}^{M} S_{ij} \cdot R_j
$$

In vector form, where **n** is the column vector of all species densities, this is:

$$
\frac{d \mathbf{n}}{dt} = \mathbf{S}^T \cdot \mathbf{R}
$$

The code implements this with the following lines in `_ode_system`:

```python
# dY_dt is the vector dn/dt
dY_dt = np.zeros(self.num_species)
for i in range(self.num_species):
    # This is a dot product of the i-th column of S^T with R
    dY_dt[i] = np.sum(reaction_rates * self.stoich_matrix_net[:, i])
```
This `dY_dt` vector is the first part of the system of derivatives that is passed to the ODE solver (`solve_ivp`).

## 3. The Power Balance Equation

The second part of the system is the power balance equation for the electrons. The variable being solved for is the **electron energy density**, `Uₑ`, defined as:

$$
U_e = \frac{3}{2} n_e k_B T_e = \frac{3}{2} n_e (q_e T_{eV})
$$

The ODE is:
$$
\frac{d U_e}{dt} = (P_{abs} / V) - P_{loss}
$$

### Power Absorption (`P_abs`)

The absorbed power `P_abs` is given in the input file in Watts (Joules/sec). The code converts this to an energy density rate in `eV·m⁻³s⁻¹`:

$$
Q_{abs} = \frac{P_{abs}}{V \cdot q_e}
$$

This is implemented as:
```python
power_W = self.mdef.get('constant_data', {}).get('power_input_W', 0.0)
Q_abs = power_W / self.const['q_e'] / params['volume']
```

### Power Loss (`P_loss`)

The total power loss `P_loss` (or `Q_loss` in the code) is the sum of the power lost in every reaction `j`. The power lost in a single reaction is the rate of that reaction multiplied by the energy lost per reaction, `ε_j`.

$$
P_{loss} = \sum_{j=1}^{M} R_j \cdot \varepsilon_j
$$

The `ε_j` values are provided in the input file. They represent different physical processes:
-   **Collisional Loss (`ε_coll`):** For inelastic collisions (ionization, excitation), `ε_j` is the threshold energy of the reaction in eV.
-   **Wall Loss (`ε_wall`):** For particles lost to the wall, `ε_j` is the average energy carried to the wall by each lost ion-electron pair. For example, for an ion `i`, this is often `ε_i ≈ 2 T_{eV} + 0.5 T_{eV} + V_s`, representing the kinetic energy of the electron, the ion, and the energy gained by the ion crossing the sheath potential `V_s`.

The code implements this summation in `_ode_system`:
```python
Q_loss = 0.0
for i, reaction in enumerate(self.mdef['reactions']):
    energy_loss = reaction['energy_loss_func'](params)
    q_loss_i = reaction_rates[i] * energy_loss
    Q_loss += q_loss_i
```

### Assembling the Final Derivative

The final derivative for the energy equation is `dE_dt = Q_abs - Q_loss`. This scalar value is appended to the `dY_dt` vector, forming the complete system of `N+1` derivatives that is returned to the `solve_ivp` function at every time step.
