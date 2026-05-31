import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from dashboard.mappings import get_store_label, get_dept_label

import datetime as _dt

def _safe_date(val, fallback):
    """Convert val to a real datetime.date; return fallback on any error."""
    if val is None:
        return fallback
    try:
        parsed = pd.to_datetime(val)
        if pd.isna(parsed):
            return fallback
        return parsed.date()
    except Exception:
        return fallback

def get_filter_options(_db):
    """Fetches unique stores, departments, and date ranges from DB for filters."""
    _fallback_min = _dt.date(2010, 2, 5)
    _fallback_max = _dt.date(2012, 10, 26)
    stores = list(range(1, 46))
    depts  = list(range(1, 100))
    min_date = _fallback_min
    max_date = _fallback_max
    try:
        conn   = _db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM sales_data")
        cnt = cursor.fetchone()[0]
        if cnt > 0:
            cursor.execute("SELECT DISTINCT store FROM sales_data ORDER BY store")
            stores = [row[0] for row in cursor.fetchall()]
            cursor.execute("SELECT DISTINCT dept FROM sales_data ORDER BY dept")
            depts  = [row[0] for row in cursor.fetchall()]
            cursor.execute("SELECT MIN(date), MAX(date) FROM sales_data")
            raw_min, raw_max = cursor.fetchone()
            min_date = _safe_date(raw_min, _fallback_min)
            max_date = _safe_date(raw_max, _fallback_max)
        conn.close()
    except Exception as e:
        print(f"Error fetching filter options: {e}")
    # Final safety: ensure they are real date objects
    if not isinstance(min_date, _dt.date):
        min_date = _fallback_min
    if not isinstance(max_date, _dt.date):
        max_date = _fallback_max
    return stores, depts, min_date, max_date

def render_analytics_page(db):
    st.markdown("<h1 style='text-align: center; color: #FFC220; margin-bottom: 5px;'>Exploratory Data & Market Analytics</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #94A3B8; font-size:1.05rem;'>Drill down into retail trends, analyze macroeconomic factors, and examine correlations</p>", unsafe_allow_html=True)
    st.markdown("---")

    # 1. Get options (no cache – always read live from DB)
    stores, depts, min_date, max_date = get_filter_options(db)

    # 2. Filters layout
    st.markdown("#### Filter Analytics View")
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        selected_store = st.selectbox(
            "Select Store",
            [None] + stores,
            format_func=lambda x: "All Stores" if x is None else get_store_label(x)
        )

    with col2:
        selected_dept = st.selectbox(
            "Select Department",
            [None] + depts,
            format_func=lambda x: "All Departments" if x is None else get_dept_label(x)
        )

    with col3:
        date_range = st.date_input(
            "Select Date Range", 
            value=[min_date, max_date], 
            min_value=min_date, 
            max_value=max_date
        )
        
    with col4:
        holiday_filter = st.selectbox(
            "Holiday Period", 
            ["All Weeks", "Holidays Only", "Non-Holidays Only"]
        )
        
    if isinstance(date_range, list) or isinstance(date_range, tuple):
        if len(date_range) == 2:
            start_date, end_date = date_range
        else:
            start_date = date_range[0]
            end_date = max_date
    else:
        start_date = date_range
        end_date = max_date
        
    # Load and filter data from DB
    conn = db.get_connection()
    try:
        where_clauses = ["date >= ?", "date <= ?"]
        params = [start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d")]
        
        if selected_store is not None:
            where_clauses.append("store = ?")
            params.append(selected_store)
            
        if selected_dept is not None:
            where_clauses.append("dept = ?")
            params.append(selected_dept)
            
        if holiday_filter == "Holidays Only":
            where_clauses.append("is_holiday = 1")
        elif holiday_filter == "Non-Holidays Only":
            where_clauses.append("is_holiday = 0")
            
        where_str = " WHERE " + " AND ".join(where_clauses)
        
        query = f"SELECT store, dept, date, weekly_sales, is_holiday FROM sales_data {where_str} ORDER BY date ASC"
        if db.db_mode == "MYSQL":
            query = query.replace("?", "%s")
        df = pd.read_sql(query, conn, params=params)
        df['date'] = pd.to_datetime(df['date'])
        
        # Load external features to join for economic analysis
        import os
        raw_features_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "..",
            "dataset",
            "raw",
            "features.csv",
        )
        if os.path.exists(raw_features_path):
            try:
                features_df = pd.read_csv(raw_features_path)
                if 'Date' in features_df.columns:
                    features_df['Date'] = pd.to_datetime(features_df['Date'])
                # Aggregated features by store & date for economy
                econ_df = pd.merge(df, features_df, left_on=['store', 'date'], right_on=['Store', 'Date'], how='left')
            except Exception as e:
                st.warning(f"Failed to load features.csv: {e}. Economy analysis will be skipped.")
                econ_df = df.copy()
        else:
            st.warning("features.csv not found; economy analysis will be skipped.")
            econ_df = df.copy()
        
    except Exception as e:
        st.error(f"Error executing analytics query: {e}")
        econ_df = pd.DataFrame()
    finally:
        conn.close()
        
    if econ_df.empty:
        st.warning("No records found for the selected filters. Please expand your filter options.")
        return
        
    # Visualizations
    st.markdown("---")
    
    # 1. Sales Trend
    st.subheader("Sales Volume Trend")
    trend_type = st.radio("Aggregate Sales By:", ["Weekly", "Monthly"], horizontal=True)
    
    if trend_type == "Weekly":
        trend_df = econ_df.groupby('date')['weekly_sales'].sum().reset_index()
        fig_trend = px.line(
            trend_df, 
            x='date', 
            y='weekly_sales', 
            labels={'weekly_sales': 'Total Sales ($)', 'date': 'Week'}, 
            template='plotly_dark'
        )
    else:
        econ_df['Month_Year'] = econ_df['date'].dt.to_period('M')
        trend_df = econ_df.groupby('Month_Year')['weekly_sales'].sum().reset_index()
        trend_df['Month_Year'] = trend_df['Month_Year'].dt.to_timestamp()
        fig_trend = px.line(
            trend_df, 
            x='Month_Year', 
            y='weekly_sales', 
            labels={'weekly_sales': 'Total Sales ($)', 'Month_Year': 'Month'}, 
            template='plotly_dark'
        )
        
    fig_trend.update_traces(line=dict(color='#0071CE', width=2.5))
    fig_trend.update_layout(
        margin=dict(l=20, r=20, t=10, b=20), 
        height=300, 
        xaxis_title=None,
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        yaxis=dict(gridcolor='#334155'),
        xaxis=dict(gridcolor='#334155')
    )
    st.plotly_chart(fig_trend, use_container_width=True)
    
    # 2. Economy Impact Row
    st.subheader("Macroeconomic Indicators vs. Weekly Sales")
    econ_col1, econ_col2, econ_col3 = st.columns(3)
    
    # Aggregating sales by store and date for macro correlations
    econ_agg = econ_df.groupby(['store', 'date', 'CPI', 'Unemployment', 'Fuel_Price'])['weekly_sales'].sum().reset_index()
    
    with econ_col1:
        st.markdown("##### CPI vs Sales")
        fig_cpi = px.scatter(
            econ_agg, x='CPI', y='weekly_sales', trendline='ols', 
            trendline_color_override='#FFC220', opacity=0.4, 
            labels={'weekly_sales': 'Weekly Sales ($)'}, template='plotly_dark',
            color_discrete_sequence=['#0071CE']
        )
        fig_cpi.update_layout(
            margin=dict(l=10, r=10, t=10, b=10), 
            height=250,
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            yaxis=dict(gridcolor='#334155'),
            xaxis=dict(gridcolor='#334155')
        )
        st.plotly_chart(fig_cpi, use_container_width=True)
        
    with econ_col2:
        st.markdown("##### Unemployment Rate vs Sales")
        fig_un = px.scatter(
            econ_agg, x='Unemployment', y='weekly_sales', trendline='ols', 
            trendline_color_override='#FFC220', opacity=0.4, 
            labels={'weekly_sales': 'Weekly Sales ($)', 'Unemployment': 'Unemployment (%)'}, template='plotly_dark',
            color_discrete_sequence=['#0071CE']
        )
        fig_un.update_layout(
            margin=dict(l=10, r=10, t=10, b=10), 
            height=250,
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            yaxis=dict(gridcolor='#334155'),
            xaxis=dict(gridcolor='#334155')
        )
        st.plotly_chart(fig_un, use_container_width=True)
        
    with econ_col3:
        st.markdown("##### Fuel Price vs Sales")
        fig_fuel = px.scatter(
            econ_agg, x='Fuel_Price', y='weekly_sales', trendline='ols', 
            trendline_color_override='#FFC220', opacity=0.4, 
            labels={'weekly_sales': 'Weekly Sales ($)', 'Fuel_Price': 'Fuel Price ($)'}, template='plotly_dark',
            color_discrete_sequence=['#0071CE']
        )
        fig_fuel.update_layout(
            margin=dict(l=10, r=10, t=10, b=10), 
            height=250,
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            yaxis=dict(gridcolor='#334155'),
            xaxis=dict(gridcolor='#334155')
        )
        st.plotly_chart(fig_fuel, use_container_width=True)
        
    # 3. Correlation Analysis & Holidays Impact
    corr_col1, corr_col2 = st.columns(2)
    
    with corr_col1:
        st.subheader("Holiday Sales Impact")
        
        # Resolve potential holiday column merge name duplication
        is_holiday_col = 'is_holiday_x' if 'is_holiday_x' in econ_df.columns else 'is_holiday'
        
        fig_box = px.box(
            econ_df, 
            x=is_holiday_col, 
            y='weekly_sales',
            color=is_holiday_col,
            color_discrete_map={0: '#0071CE', 1: '#FFC220'},
            labels={'weekly_sales': 'Weekly Sales ($)', is_holiday_col: 'Holiday status'},
            category_orders={is_holiday_col: [0, 1]},
            template='plotly_dark'
        )
        fig_box.update_layout(
            margin=dict(l=20, r=20, t=10, b=20),
            height=300,
            showlegend=False,
            xaxis=dict(tickvals=[0, 1], ticktext=["Regular Week", "Holiday Week"], gridcolor='#334155'),
            yaxis=dict(gridcolor='#334155'),
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)'
        )
        st.plotly_chart(fig_box, use_container_width=True)
        
    with corr_col2:
        st.subheader("Correlation Heatmap")
        corr_vars = ['weekly_sales', 'Temperature', 'Fuel_Price', 'CPI', 'Unemployment']
        corr_vars = [v for v in corr_vars if v in econ_df.columns]
        
        if len(corr_vars) >= 2:
            corr_mat = econ_df[corr_vars].corr()
            
            fig_heatmap = go.Figure(data=go.Heatmap(
                z=corr_mat.values,
                x=corr_mat.columns,
                y=corr_mat.index,
                colorscale='RdBu_r',
                zmin=-1, zmax=1,
                text=np.round(corr_mat.values, 3),
                texttemplate="%{text}",
                showscale=True
            ))
            fig_heatmap.update_layout(
                margin=dict(l=20, r=20, t=10, b=20),
                height=300,
                template='plotly_dark',
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)'
            )
            st.plotly_chart(fig_heatmap, use_container_width=True)
        else:
            st.info("Insufficient variables for correlation analysis.")
