"""
app.py - Streamlit UI for zdplasmapy
Simple wrapper around main.py logic with case selection UI.
"""
import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
import os
from src.case_utils import discover_cases, get_case_config_path
from src.util import build_model_definition
from src.global_model import GlobalModel


def main():
    st.set_page_config(page_title="zdplasmapy", layout="wide")
    st.title("zdplasmapy: 0D Plasma Chemistry Simulation")
    
    # --- Sidebar: Case Selection ---
    st.sidebar.header("📁 Case Selection")
    
    # Discover available cases
    available_cases = discover_cases('cases')
    
    if not available_cases:
        st.sidebar.error("No cases found in 'cases/' folder")
        st.error("No valid cases detected. Please add a case folder with config.yml")
        return
    
    # Case selector
    default_idx = 0
    if 'ashida1995' in available_cases:
        default_idx = available_cases.index('ashida1995')
    
    selected_case = st.sidebar.selectbox(
        "Select Case",
        options=available_cases,
        index=default_idx
    )
    
    # Manual override
    manual_path = st.sidebar.text_input(
        "Or enter custom config path:",
        placeholder="cases/my_case/config.yml"
    )
    
    # Determine config path
    if manual_path.strip():
        config_path = manual_path.strip()
    else:
        config_path = get_case_config_path(selected_case, 'cases')
    
    st.sidebar.info(f"**Using:** `{config_path}`")
    
    # --- Main Content ---
    st.markdown("""
    Interactive global model for low-temperature plasma chemistry.
    Select a case from the sidebar and click 'Run Simulation'.
    """)
    
    # --- Run Button ---
    if st.button("🚀 Run Simulation", type="primary"):
        try:
            with st.spinner(f"Loading model from {config_path}..."):
                model_def = build_model_definition(config_path)
            
            with st.spinner("Running simulation..."):
                # Use the exact same pattern as main.py
                gm = GlobalModel(model_definition=model_def, debug=False)
                gm.run()
            
            st.success("✓ Simulation complete!")
            
            # --- Plot Results ---
            st.subheader(f"📊 Results: {selected_case}")
            
            # Use GlobalModel's built-in plot method
            if hasattr(gm, 'plot_results'):
                fig = gm.plot_results(return_figure=True)
                if fig:
                    st.pyplot(fig)
                else:
                    st.error("Plot generation failed")
            else:
                st.error("GlobalModel doesn't have plot_results method")
            
            # --- Data Table ---
            with st.expander(f"📋 View Final State - {selected_case}"):
                if gm.results and gm.results.success:
                    final_idx = -1
                    t_final = gm.results.t[final_idx]
                    y_final = gm.results.y[:, final_idx]
                    
                    # Calculate final Te
                    ne_final = y_final[gm.species.index('e')]
                    energy_final = y_final[-1]
                    Te_final = (2.0/3.0) * energy_final / ne_final if ne_final > 0 else 0
                    
                    final_state = {
                        'Species': gm.species,
                        'Density (m⁻³)': [f"{y_final[i]:.3e}" for i in range(len(gm.species))],
                    }
                    st.table(final_state)
                    st.write(f"Final time: {t_final:.3e} s")
                    st.write(f"Final Te: {Te_final:.3f} eV")
                else:
                    st.error("No valid results available")
        
        except Exception as e:
            st.error(f"❌ Simulation failed: {e}")
            st.exception(e)
    
    # --- Footer ---
    st.sidebar.markdown("---")
    st.sidebar.markdown("**zdplasmapy** v0.2")
    st.sidebar.markdown("[GitHub](https://github.com/mjimenez-arch/zdplasmapy)")


if __name__ == "__main__":
    main()
