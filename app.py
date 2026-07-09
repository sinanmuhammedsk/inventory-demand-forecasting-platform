import streamlit as st
# Data Management UI removed; handled in backend
import os
from database.db_manager import DatabaseManager
from dashboard.dashboard_page import render_dashboard_page
from dashboard.analytics_page import render_analytics_page
from dashboard.forecasting_page import render_forecasting_page
from dashboard.recommendations_page import render_recommendations_page
from dashboard.reports_page import render_reports_page
from dashboard.about_page import render_about_page

# Set page config
st.set_page_config(
    page_title="Walmart Inventory Analytics & Demand Forecasting",
    page_icon="✵",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Global CSS styling to ensure styling consistency
st.markdown("""
<style>
/* Main Layout Adjustments */
.block-container {
    padding-top: 1.5rem;
    padding-bottom: 1.5rem;
    background-color: #FFFFFF !important;
    color: #0F172A !important;
}
/* KPI metric styling adjustments */
div[data-testid="stMetricValue"] {
    font-size: 1.8rem;
    font-weight: 700;
    color: #0F172A !important;
}
/* Primary buttons styling */
div.stButton > button:first-child {
    background-color: #0071CE !important;
    color: #FFFFFF !important;
    border: 1px solid #0071CE !important;
    border-radius: 6px !important;
    padding: 0.5rem 1rem !important;
    font-weight: 600 !important;
    transition: all 0.3s ease !important;
}
div.stButton > button:first-child:hover {
    background-color: #FFC220 !important;
    color: #0F172A !important;
    border-color: #FFC220 !important;
    box-shadow: 0 4px 12px rgba(255, 194, 32, 0.3) !important;
    transform: translateY(-1px) !important;
}
/* Horizontal divider override */
hr {
    margin-top: 1rem !important;
    margin-bottom: 1rem !important;
    border-color: #E5E7EB !important;
}
</style>
""", unsafe_allow_html=True)


# Initialize Database Manager
import os
import sys

# Ensure project root on sys.path for direct script imports
# Ensure project root is on sys.path for imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Import seed function for auto‑seeding on fresh deployments
from database.seed_data import seed

# Initialize Database Manager
if "db" not in st.session_state:
    db = DatabaseManager()
    db.init_db()
    # Ensure data is present – seed if sales_data empty
    with st.spinner("Ensuring database is seeded (may take a few minutes)…"):
        try:
            conn = db.get_connection()
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM sales_data")
            cnt = cur.fetchone()[0]
            conn.close()
            if cnt == 0:
                seed()
        except Exception as e:
            st.warning(f"Seeding verification failed ({e}); attempting seed.")
            seed()
    st.session_state.db = db
    # Debug: log row count after potential seeding
    try:
        conn_dbg = db.get_connection()
        cur_dbg = conn_dbg.cursor()
        cur_dbg.execute("SELECT COUNT(*) FROM sales_data")
        rows = cur_dbg.fetchone()[0]
        print(f"DEBUG: sales_data rows after seed = {rows}")
        conn_dbg.close()
    except Exception as e:
        print(f"DEBUG: failed to count rows ({e})")
else:
    db = st.session_state.db

# Sidebar Navigation Panel with Walmart Spark logo and branding
st.sidebar.markdown(
    """
    <div style="text-align: center; margin-bottom: 25px; padding-top: 10px;">
        <h2 style="color: #0071CE; margin-bottom: 0px; font-size:1.6rem; font-weight: 800; letter-spacing: 0.5px;">
            Walmart <span style="color: #FFC220;">✵</span>
        </h2>
        <div style="color: #0F172A; font-weight: 700; font-size: 0.85rem; margin-top: 2px; letter-spacing: 1px; text-transform: uppercase;">
            Inventory Analytics
        </div>
        <span style="background-color: #0071CE25; color: #0071CE; border: 1px solid #0071CE50; padding: 3px 8px; border-radius: 4px; font-size: 0.7rem; font-weight: bold; text-transform: uppercase; display: inline-block; margin-top: 8px;">
            Enterprise BI
        </span>
    </div>
    """,
    unsafe_allow_html=True,
)

# Custom CSS to ensure headings show a pointer cursor on hover
st.markdown(
    """
    <style>
    /* Headings (e.g., Forecast Parameters, Filter Analytics View) */
    h4:hover { cursor: pointer; }
    /* Streamlit expander summary */
    details summary:hover { cursor: pointer; }
    /* Fallback for any expander header element */
    [data-testid="stExpanderHeader"]:hover { cursor: pointer; }
    /* BaseWeb select dropdown arrow and its container */
    div[data-baseweb="select"] svg,
    div[data-baseweb="select"] [role="button"],
    div[data-baseweb="select"] * {
        cursor: pointer !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

navigation_options = [
    "Executive Dashboard",
    "Market Analytics",
    "Demand Forecasting",
    "Inventory Optimization",
    "System Reports",
    "About System"
]

selected_nav = st.sidebar.radio("Navigation Menu", navigation_options, index=0)

st.sidebar.markdown("---")

# Database status indicator styled for light theme
db_color = "#10B981" if db.db_mode == "MYSQL" else "#3B82F6"
st.sidebar.markdown(
    f"""
    <div style="background-color: #F3F4F6; border: 1px solid #D1D5DB; border-radius: 8px; padding: 12px; text-align: center; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);">
        <span style="font-size: 0.75rem; color: #0F172A; font-weight: 600; text-transform: uppercase; display: block; margin-bottom: 6px; letter-spacing: 0.5px;">System Engine</span>
        <span style="background-color: {db_color}20; color: #0F172A; border: 1px solid {db_color}50; padding: 3px 8px; border-radius: 4px; font-size: 0.75rem; font-weight: bold; display: inline-block;">DB Mode: {db.db_mode}</span>
    </div>
    """,
    unsafe_allow_html=True,
)

st.sidebar.markdown(
    """
    <div style="text-align: center; margin-top: 60px; font-size: 0.7rem; color: #64748B; font-weight: 500;">
        Demand Forecasting System v1.0.0<br>
        Developed for Portfolio Showcase
    </div>
    """,
    unsafe_allow_html=True
)

# Page Navigation Activity Logging
if "current_page" not in st.session_state:
    st.session_state.current_page = None

if st.session_state.current_page != selected_nav:
    try:
        db.log_activity(
            user_name="admin",
            action_performed=f"Navigated to page: {selected_nav}",
            page_visited=selected_nav
        )
    except Exception as e:
        print(f"Error logging navigation event: {e}")
    st.session_state.current_page = selected_nav

# Render respective page components
if selected_nav == "Executive Dashboard":
    render_dashboard_page(db)
elif selected_nav == "Market Analytics":
    render_analytics_page(db)
elif selected_nav == "Demand Forecasting":
    render_forecasting_page(db)
elif selected_nav == "Inventory Optimization":
    render_recommendations_page(db)
elif selected_nav == "System Reports":
    render_reports_page(db)
elif selected_nav == "About System":
    render_about_page(db)
