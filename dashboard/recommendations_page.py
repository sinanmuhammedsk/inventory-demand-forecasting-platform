import streamlit as st
import pandas as pd
import numpy as np
from models.recommender import InventoryRecommender
from dashboard.mappings import get_store_label, get_dept_label, STORE_CITIES, DEPT_NAMES

@st.cache_resource
def get_recommender():
    return InventoryRecommender()

def render_recommendations_page(db):
    st.markdown("<h1 style='text-align: center; color: #FFC220; margin-bottom: 5px;'>Inventory Replenishment & Stock Optimization</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #94A3B8; font-size:1.05rem;'>Calculate reorder points, determine safety stock levels, and identify inventory risks</p>", unsafe_allow_html=True)
    st.markdown("---")
    
    recommender = get_recommender()
    
    # Load unique store-dept lists
    conn = db.get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT DISTINCT store FROM sales_data ORDER BY store")
        stores = [row[0] for row in cursor.fetchall()]
        cursor.execute("SELECT DISTINCT dept FROM sales_data ORDER BY dept")
        depts = [row[0] for row in cursor.fetchall()]
    except Exception as e:
        stores = list(range(1, 46))
        depts = list(range(1, 100))
    finally:
        conn.close()
        
    st.markdown("### 1. Interactive Single Store-Department Replenishment Calculator")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        store_sel = st.selectbox("Select Store", stores, index=0, format_func=get_store_label)
        lead_time = st.slider("Supplier Lead Time (Weeks)", min_value=1, max_value=4, value=2)
        
    with col2:
        dept_sel = st.selectbox("Select Department", depts, index=0, format_func=get_dept_label)
        service_level = st.selectbox("Target Service Level", [0.90, 0.95, 0.99], index=1, format_func=lambda x: f"{x*100:.0f}%")
        
    # Get historical metrics to pre-populate a realistic current stock
    hist_stats = recommender.get_historical_metrics(store_sel, dept_sel)
    mean_sales = hist_stats["mean_weekly_sales"]
    
    # Realistic default current stock
    default_stock = int(np.ceil(mean_sales * 1.2)) if mean_sales > 0 else 1000
    
    with col3:
        current_stock = st.number_input("Current Stock Level (Units)", min_value=0, value=default_stock, step=50)
        horizon = st.selectbox("Planning Horizon", [7, 30, 90], index=1, format_func=lambda x: f"{x} Days")
        
    if st.button("Generate & Save Optimization Metrics", type="primary"):
        # Calculate
        rec = recommender.generate_recommendation(
            store=store_sel,
            dept=dept_sel,
            current_stock=current_stock,
            lead_time_weeks=lead_time,
            service_level=service_level,
            horizon_days=horizon
        )
        
        # Log activity and save to DB
        db.log_activity("admin", f"Run & Save recommendation: Store {store_sel}, Dept {dept_sel}, Stock {current_stock}", "Recommendations")
        db.save_recommendation(
            store=store_sel,
            dept=dept_sel,
            current_stock=int(current_stock),
            forecasted_demand=rec["expected_demand"],
            rec_type=rec["recommendation_type"],
            quantity=rec["recommended_quantity"],
            cost=rec["estimated_cost"]
        )
        st.success("Recommendation saved to database successfully.")
        
        # Style Alert cards for Dark Theme
        st.markdown("<br>", unsafe_allow_html=True)
        rec_type = rec["recommendation_type"]
        
        if rec_type == "LOW_STOCK_REORDER":
            alert_title = "CRITICAL ALERT: LOW STOCK / STOCKOUT RISK"
            alert_color = "#F87171" # Light red
            alert_bg = "#441515"    # Dark red
            alert_border = "#991B1B"
        elif rec_type == "OVERSTOCK_LIQUIDATE":
            alert_title = "WARNING: OVERSTOCK DETECTED"
            alert_color = "#FBBF24" # Light amber
            alert_bg = "#3B2510"    # Dark amber
            alert_border = "#92400E"
        else:
            alert_title = "SYSTEM STATUS: OPTIMAL"
            alert_color = "#34D399" # Light green
            alert_bg = "#063D27"    # Dark green
            alert_border = "#065F46"
            
        st.markdown(
            f"""
            <div style="background-color: {alert_bg}; border: 1px solid {alert_border}; border-left: 6px solid {alert_color}; border-radius: 8px; padding: 20px; margin-bottom: 25px;">
                <h4 style="color: {alert_color}; margin-top: 0; margin-bottom: 8px; font-weight: 700; letter-spacing: 0.5px;">{alert_title}</h4>
                <p style="color: #F8FAFC; font-weight: 500; font-size: 1.05rem; margin-bottom: 0;">{rec['recommendation_text']}</p>
            </div>
            """,
            unsafe_allow_html=True
        )
        
        # Details Columns
        st.markdown("#### Replenishment Formulas & Safety Metrics")
        d_col1, d_col2, d_col3, d_col4 = st.columns(4)
        
        with d_col1:
            st.metric("Expected Demand", f"{rec['expected_demand']:,} units")
            st.caption("Aggregated demand over horizon")
            
        with d_col2:
            st.metric("Safety Stock (SS)", f"{rec['safety_stock']:,} units")
            st.caption("Buffer stock to prevent stockouts")
            
        with d_col3:
            st.metric("Reorder Point (ROP)", f"{rec['reorder_point']:,} units")
            st.caption("Reorder triggered when current stock < ROP")
            
        with d_col4:
            st.metric("Recommended Reorder", f"{rec['recommended_quantity']:,} units")
            st.caption("Replenish to Target Stock Level")
            
        st.markdown("---")
        
        # Details summary table
        st.markdown("#### Technical Parameters Sheet")
        summary_data = {
            "Parameter": [
                "Store ID", "Department ID", "Current Stock (Units)", 
                "Forecasted Horizon Demand (Units)", "Safety Stock (Units)", 
                "Reorder Point (ROP)", "Order-Up-To Target Stock (Units)", 
                "Recommended Reorder (Units)", "Estimated Reorder Cost / Holding Penalty ($)"
            ],
            "Value": [
                f"{get_store_label(rec['store'])}", f"{get_dept_label(rec['dept'])}", f"{rec['current_stock']:,}", 
                f"{rec['expected_demand']:,}", f"{rec['safety_stock']:,}", 
                f"{rec['reorder_point']:,}", f"{rec['target_stock']:,}", 
                f"{rec['recommended_quantity']:,}", f"${rec['estimated_cost']:,.2f}"
            ]
        }
        st.table(pd.DataFrame(summary_data))
        
    st.markdown("---")
    
    # 2. General Inventory Risk Overview
    st.markdown("### 2. Simulated Multi-Department Inventory Audit Trail")
    st.markdown("<p style='color: #94A3B8;'>Current replenishment status and recommendation flags for top departments in Store 1 (HQ)</p>", unsafe_allow_html=True)
    
    audit_depts = [1, 2, 3, 4, 8, 9, 13]
    audit_data = []
    
    with st.spinner("Compiling multi-department audit trail..."):
        for d in audit_depts:
            h_metrics = recommender.get_historical_metrics(1, d)
            m_sales = h_metrics["mean_weekly_sales"]
            
            if d == 1:
                sim_stock = int(m_sales * 0.4)
            elif d == 2:
                sim_stock = int(m_sales * 3.5)
            elif d == 8:
                sim_stock = int(m_sales * 0.2)
            else:
                sim_stock = int(m_sales * 1.3)
                
            sim_stock = max(50, sim_stock)
            
            try:
                forecast_df = recommender.predictor.forecast_demand(1, d, 30)
                exp_dem = forecast_df['Forecast'].sum()
                num_w = len(forecast_df)
                std_s = h_metrics["std_weekly_sales"]
                if pd.isna(std_s) or std_s == 0:
                    std_s = 0.2 * m_sales
                ss = 1.645 * std_s * np.sqrt(2)
                rop = (exp_dem/num_w * 2) + ss
                target = exp_dem + ss
                
                req_qty = 0
                r_type = "OPTIMAL"
                if sim_stock < rop:
                    r_type = "LOW STOCK / REORDER"
                    req_qty = int(np.ceil(target - sim_stock))
                elif sim_stock > (exp_dem + ss * 2):
                    r_type = "OVERSTOCK / EXCESS"
                    
                store_label = f"Store #{1} ({STORE_CITIES.get(1, 'Unknown')})"
                dept_label = f"Dept #{d} ({DEPT_NAMES.get(d, 'General')})"
                
                audit_data.append({
                    "Store": store_label,
                    "Department": dept_label,
                    "Current Stock": sim_stock,
                    "Avg Weekly Sales": int(m_sales),
                    "Expected Demand (30D)": int(exp_dem),
                    "Reorder Point (ROP)": int(rop),
                    "Status": r_type,
                    "Recommended Order": req_qty
                })
            except Exception:
                pass
                
    if audit_data:
        audit_df = pd.DataFrame(audit_data)
        
        # Color coding cell function styled for dark mode
        def style_status(val):
            if val == "LOW STOCK / REORDER":
                return 'background-color: #7F1D1D; color: #FCA5A5; font-weight: bold; border: 1px solid #991B1B;'
            elif val == "OVERSTOCK / EXCESS":
                return 'background-color: #78350F; color: #FCD34D; font-weight: bold; border: 1px solid #92400E;'
            else:
                return 'background-color: #064E3B; color: #A7F3D0; font-weight: bold; border: 1px solid #065F46;'
                
        st.dataframe(audit_df.style.map(style_status, subset=['Status']).format({
            "Current Stock": "{:,}",
            "Avg Weekly Sales": "${:,}",
            "Expected Demand (30D)": "${:,}",
            "Reorder Point (ROP)": "{:,}",
            "Recommended Order": "{:,}"
        }), width='stretch')
