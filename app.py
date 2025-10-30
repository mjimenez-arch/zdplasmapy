# app.py

import streamlit as st
import os
import glob
from model_parser import load_input_file
from global_model import GlobalModel

# --- Page Configuration (must be the first Streamlit command) ---
st.set_page_config(
    page_title="zdplasmapy Global Model",
    layout="wide"
)

# --- Main App Logic ---

# Title of the app
st.title("zdplasmapy: A 0D Global Plasma Model")

# --- Sidebar for User Controls ---
st.sidebar.header("Simulation Controls")

# Find all available input model "recipes" in the input_models folder
input_files_path = 'input_models/*.py'
# Use glob to find all files matching the pattern
available_models = glob.glob(input_files_path)
# Clean up the names for display in the dropdown
model_names = {os.path.basename(f): f for f in available_models}

# Create a dropdown menu to select the model
selected_model_name = st.sidebar.selectbox(
    "Choose a Plasma Model:",
    options=list(model_names.keys())
)

# A button to trigger the simulation
run_button = st.sidebar.button("Run Simulation")


# --- Main Panel for Displaying Results ---

# Use Streamlit's session state to store the results, so they don't disappear
if 'simulation_results' not in st.session_state:
    st.session_state['simulation_results'] = None

# This block runs ONLY when the "Run Simulation" button is clicked
if run_button:
    # Get the full path to the selected model file
    input_filename = model_names[selected_model_name]
    
    # Use a spinner to show that the simulation is in progress
    with st.spinner(f"Running simulation for '{selected_model_name}'... Please wait."):
        try:
            # 1. Load the model definition
            model_definition = load_input_file(input_filename)
            
            # 2. Create and run the model instance
            model = GlobalModel(model_definition, debug=False) # Debug is off for the app
            model.run()
            
            # 3. Store the results in the session state
            if model.results.success:
                st.session_state['simulation_results'] = model.results
                st.session_state['model_instance'] = model # Also save the model instance
                st.success(f"Simulation finished successfully! ({model.results.message})")
            else:
                st.session_state['simulation_results'] = None
                st.error(f"Simulation failed! ({model.results.message})")

        except Exception as e:
            st.error(f"An error occurred during the simulation: {e}")
            st.session_state['simulation_results'] = None

# This block displays the plot if results are available
if st.session_state['simulation_results']:
    st.header("Simulation Results")
    
    # Get the saved model instance and results
    model = st.session_state['model_instance']
    results = st.session_state['simulation_results']
    
    # Generate the plot figure using the model's plot_results logic
    # We will capture the figure object instead of showing it directly
    fig = model.plot_results(return_figure=True) # A small modification to plot_results is needed
    
    # Display the plot in the Streamlit app
    st.pyplot(fig)
else:
    st.info("Select a model from the sidebar and click 'Run Simulation' to see the results.")