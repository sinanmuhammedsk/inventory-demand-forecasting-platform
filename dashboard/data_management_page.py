import streamlit as st
import os
import sys

# Ensure the project root is on the import path for the conversion script
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

def render_data_management_page(db):
    """Provides a simple UI to regenerate the Parquet version of the dataset.
    This is useful when the underlying CSV has been updated.
    """
    st.markdown("<h2 style='color:#0071CE'>Data Management</h2>", unsafe_allow_html=True)
    st.info("Regenerate the Parquet cache for the analytical dataset. This speeds up future seeding.")
    if st.button("🔄 Regenerate Parquet Dataset", type="primary"):
        with st.spinner("Converting CSV to Parquet…"):
            try:
                # Import the conversion function directly
                from scripts.convert_to_parquet import main as convert_main
                convert_main()
                st.success("✅ Parquet file regenerated successfully.")
            except Exception as e:
                st.error(f"❌ Failed to regenerate Parquet: {e}")
