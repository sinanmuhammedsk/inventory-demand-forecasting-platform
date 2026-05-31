import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from ..models.predictor import DemandPredictor
from dashboard.mappings import get_store_label, get_dept_label
import io

@st.cache_resource
def get_predictor():
    return DemandPredictor()

def render_forecasting_page(db):
    st.markdown("<h1 style='text-align: center; color: #FFC220; margin-bottom: 5px;'>Predictive Demand Forecasting Engine</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #94A3B8; font-size:1.05rem;'>Generate future sales forecasts using the optimized Random Forest ensemble model</p>", unsafe_allow_html=True)
    st.markdown("---")
    
    # Initialize Predictor
    predictor = get_predictor()
    
    # Load unique store-dept lists for selectboxes
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
        
    # Controls layout
    st.markdown("#### Forecast Parameters")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        store_sel = st.selectbox(
            "Select Target Store", 
            stores, 
            index=0, 
            format_func=get_store_label
        )
        
    with col2:
        dept_sel = st.selectbox(
            "Select Target Department", 
            depts, 
            index=0, 
            format_func=get_dept_label
        )
        
    with col3:
        horizon_sel = st.selectbox(
            "Forecast Horizon", 
            ["7 Days (1 Week)", "30 Days (4 Weeks)", "90 Days (13 Weeks)"], 
            index=1
        )
        
    # Map horizon selection to days
    horizon_days = 30
    if horizon_sel == "7 Days (1 Week)":
        horizon_days = 7
    elif horizon_sel == "90 Days (13 Weeks)":
        horizon_days = 90
        
    # Button to run forecast
    if st.button("Generate Forecast", type="primary"):
        with st.spinner("Executing machine learning pipeline..."):
            try:
                # Log activity in DB
                db.log_activity(
                    user_name="admin", 
                    action_performed=f"Run forecast: Store {store_sel}, Dept {dept_sel}, Horizon {horizon_sel}",
                    page_visited="Forecasting"
                )
                
                # Get Forecast
                forecast_df = predictor.forecast_demand(store_sel, dept_sel, horizon_days)
                
                # Retrieve last 12 weeks of historical sales for context
                hist_df = db.load_historical_sales(store=store_sel, dept=dept_sel, limit=12)
                hist_df = hist_df.sort_values('date').reset_index(drop=True)
                hist_df['date'] = pd.to_datetime(hist_df['date'])
                
                # Calculate aggregated forecast metrics
                total_forecast = forecast_df['Forecast'].sum()
                avg_forecast = forecast_df['Forecast'].mean()
                
                # Save forecasting results to DB for history
                for _, row in forecast_df.iterrows():
                    db.save_forecast_results(
                        store=store_sel,
                        dept=dept_sel,
                        forecast_date=row['Date'],
                        horizon_days=horizon_days,
                        forecast_value=row['Forecast'],
                        lower_ci=row['Lower_CI'],
                        upper_ci=row['Upper_CI']
                    )
                
                # Render metrics
                st.markdown("<br>", unsafe_allow_html=True)
                col_m1, col_m2, col_m3 = st.columns(3)
                
                with col_m1:
                    st.metric("Total Forecasted Demand", f"${total_forecast:,.2f}")
                with col_m2:
                    st.metric("Avg Weekly Forecasted Sales", f"${avg_forecast:,.2f}")
                with col_m3:
                    st.metric("Model In-Use", f"{predictor.model_package.get('model_name', 'Random Forest')}")
                    
                st.markdown("---")
                
                # Render Forecasting Plot
                st.subheader("Historical Sales & Future Forecast Trend")
                
                fig = go.Figure()
                
                # Plot Historical Line - Styled in Walmart Blue
                fig.add_trace(go.Scatter(
                    x=hist_df['date'],
                    y=hist_df['weekly_sales'],
                    name='Historical Sales',
                    mode='lines+markers',
                    line=dict(color='#0071CE', width=3),
                    marker=dict(size=6)
                ))
                
                # Plot Forecast Line - Styled in Walmart Spark Yellow
                last_hist = hist_df.iloc[-1]
                connect_date = [last_hist['date']] + forecast_df['Date'].tolist()
                connect_sales = [last_hist['weekly_sales']] + forecast_df['Forecast'].tolist()
                
                fig.add_trace(go.Scatter(
                    x=connect_date,
                    y=connect_sales,
                    name='Forecast',
                    mode='lines+markers',
                    line=dict(color='#FFC220', width=3, dash='dash'),
                    marker=dict(size=6, symbol='diamond')
                ))
                
                # Plot Confidence Interval Bounds - Styled in soft yellow transparent fill
                lower_ci_list = [last_hist['weekly_sales']] + forecast_df['Lower_CI'].tolist()
                upper_ci_list = [last_hist['weekly_sales']] + forecast_df['Upper_CI'].tolist()
                
                fig.add_trace(go.Scatter(
                    x=connect_date + connect_date[::-1],
                    y=upper_ci_list + lower_ci_list[::-1],
                    fill='toself',
                    fillcolor='rgba(255, 194, 32, 0.12)',
                    line=dict(color='rgba(255,255,255,0)'),
                    hoverinfo="skip",
                    showlegend=True,
                    name='95% Confidence Interval'
                ))
                
                fig.update_layout(
                    xaxis_title='Timeline',
                    yaxis_title='Sales ($)',
                    template='plotly_dark',
                    height=400,
                    margin=dict(l=20, r=20, t=10, b=20),
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)',
                    yaxis=dict(gridcolor='#334155'),
                    xaxis=dict(gridcolor='#334155'),
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                )
                st.plotly_chart(fig, use_container_width=True)
                
                # Forecast Table and Downloads
                st.subheader("Forecast Data Points Table")
                disp_df = forecast_df.copy()
                disp_df['Date'] = disp_df['Date'].dt.strftime('%Y-%m-%d')
                disp_df.columns = ['Date', 'Forecasted Sales ($)', 'Lower Confidence Limit ($)', 'Upper Confidence Limit ($)']
                
                st.dataframe(disp_df.style.format({
                    'Forecasted Sales ($)': '${:,.2f}',
                    'Lower Confidence Limit ($)': '${:,.2f}',
                    'Upper Confidence Limit ($)': '${:,.2f}'
                }), use_container_width=True)
                
                # Export options
                csv_buffer = io.StringIO()
                forecast_df.to_csv(csv_buffer, index=False)
                csv_bytes = csv_buffer.getvalue().encode('utf-8')
                
                st.download_button(
                    label="Download Forecast (CSV)",
                    data=csv_bytes,
                    file_name=f"forecast_store_{store_sel}_dept_{dept_sel}_{horizon_days}_days.csv",
                    mime="text/csv"
                )
                
            except Exception as e:
                st.error(f"Error generating forecast: {e}")
                st.exception(e)
    else:
        st.info("Select Store, Department, and Horizon, then click 'Generate Forecast' to see results.")
