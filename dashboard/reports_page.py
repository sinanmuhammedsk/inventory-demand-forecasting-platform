import streamlit as st
import pandas as pd
import io
import os
from ..models.train import train_and_evaluate
import subprocess

def render_reports_page(db):
    st.markdown("<h1 style='text-align: center; color: #FFC220; margin-bottom: 5px;'>Reports & Administrative Panel</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #94A3B8; font-size:1.05rem;'>Download business reports, inspect database audit logs, and manage machine learning models</p>", unsafe_allow_html=True)
    st.markdown("---")
    
    tab1, tab2, tab3 = st.tabs(["Export Reports", "Database Audit Logs", "Model Management"])
    
    with tab1:
        st.subheader("Generate Business Reports")
        st.write("Generate and download tabular reports summarizing forecasting results and inventory recommendation audits.")
        
        # 1. Forecast Report
        st.markdown("#### 1. Demand Forecasts Summary Report")
        conn = db.get_connection()
        try:
            forecasts_df = pd.read_sql("SELECT store, dept, forecast_date, horizon_days, forecast_value, lower_ci, upper_ci, run_timestamp FROM forecast_results ORDER BY run_timestamp DESC", conn)
        except Exception:
            forecasts_df = pd.DataFrame()
        finally:
            conn.close()
            
        if not forecasts_df.empty:
            st.info(f"Database contains {len(forecasts_df):,} logged forecasting runs.")
            
            # Format exports
            csv_forecasts = forecasts_df.to_csv(index=False).encode('utf-8')
            
            # Excel export
            towrite = io.BytesIO()
            with pd.ExcelWriter(towrite, engine='openpyxl') as writer:
                forecasts_df.to_excel(writer, index=False, sheet_name='Forecast_Results')
            towrite.seek(0)
            excel_forecasts = towrite.read()
            
            col1, col2 = st.columns(2)
            with col1:
                st.download_button(
                    label="Download Forecast Report (CSV)",
                    data=csv_forecasts,
                    file_name="demand_forecasts_report.csv",
                    mime="text/csv"
                )
            with col2:
                st.download_button(
                    label="Download Forecast Report (Excel)",
                    data=excel_forecasts,
                    file_name="demand_forecasts_report.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
        else:
            st.warning("No forecasting runs logged in the database yet. Run forecasts in the Forecasting tab first.")
            
        # 2. Inventory Recommendations Log Report
        st.markdown("#### 2. Inventory Replenishment Audit Report")
        recs_df = db.get_recommendation_history(limit=5000)
        
        if not recs_df.empty:
            st.info(f"Database contains {len(recs_df):,} logged inventory recommendation records.")
            
            csv_recs = recs_df.to_csv(index=False).encode('utf-8')
            
            towrite_recs = io.BytesIO()
            with pd.ExcelWriter(towrite_recs, engine='openpyxl') as writer:
                recs_df.to_excel(writer, index=False, sheet_name='Replenishment_Audit')
            towrite_recs.seek(0)
            excel_recs = towrite_recs.read()
            
            col_r1, col_r2 = st.columns(2)
            with col_r1:
                st.download_button(
                    label="Download Replenishment Report (CSV)",
                    data=csv_recs,
                    file_name="inventory_replenishment_report.csv",
                    mime="text/csv"
                )
            with col_r2:
                st.download_button(
                    label="Download Replenishment Report (Excel)",
                    data=excel_recs,
                    file_name="inventory_replenishment_report.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
        else:
            st.warning("No inventory recommendations logged in the database yet. Generate recommendations in the Recommendations tab first.")
            
    with tab2:
        st.subheader("System Activity & Database Logs (Audit Trail)")
        st.write("This table displays real-time logging of user activity, navigation events, and database write transactions.")
        
        # Pull activity logs
        logs_df = db.get_activity_logs(limit=100)
        
        if not logs_df.empty:
            # Format columns
            logs_disp = logs_df.copy()
            logs_disp.columns = ["User", "Action Performed", "Page Visited", "Meta Details", "Timestamp"]
            st.dataframe(logs_disp, use_container_width=True)
            
            # Export logs
            csv_logs = logs_df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="Download Activity Logs (CSV)",
                data=csv_logs,
                file_name="database_audit_logs.csv",
                mime="text/csv"
            )
        else:
            st.info("No activity logs found in the database. Interaction history will appear here once you navigate the app.")
            
    with tab3:
        st.subheader("Model Retraining Dashboard")
        st.write("Trigger on-demand training of the forecasting models (Linear Regression, Random Forest, and XGBoost) on the preprocessed analytical dataset.")
        
        # Load current model comparison metrics
        metrics_csv = r"d:\forecast\reports\model_comparison.csv"
        if os.path.exists(metrics_csv):
            st.markdown("##### Current Saved Model Metrics")
            metrics_df = pd.read_csv(metrics_csv)
            
            # Highlight best metrics with a theme-appropriate dark green
            st.dataframe(
                metrics_df.style.highlight_min(axis=0, subset=['Val_RMSE', 'Val_MAE'], color='#064E3B')
                                  .highlight_max(axis=0, subset=['Val_R2'], color='#064E3B'), 
                use_container_width=True
            )
        else:
            st.info("No trained models or comparison sheets detected on disk.")
            
        st.markdown("##### Retrain Pipeline")
        st.warning("Retraining will run chronological validation on Scikit‑Learn and XGBoost, select the model with the lowest validation RMSE, retrain it on the full set, and overwrite `models/best_model.joblib`.")
        
        if st.button("Execute Pipeline Retraining", type="primary"):
            with st.spinner("Executing model training pipeline (Chronological CV)…"):
                try:
                    # Run the training script as a subprocess to capture its console output
                    result = subprocess.run(
                        ["python", "d:/forecast/models/train.py"],
                        capture_output=True,
                        text=True,
                        cwd="d:/forecast",
                        timeout=300,
                    )
                    output = result.stdout + ("\n--- ERRORS ---\n" + result.stderr if result.stderr else "")
                    # Show the raw output in an expandable panel
                    with st.expander("🔍 Retraining Output (click to expand)"):
                        st.code(output, language="text")
                    if result.returncode == 0:
                        st.success("Model retraining completed successfully!")
                        # Log retraining activity
                        db.log_activity("admin", "Triggered ML model retraining successfully", "Reports Panel")
                        # Reload metrics table to reflect new results
                        st.rerun()
                    else:
                        st.error(f"Retraining failed with exit code {result.returncode}. See output above.")
                except Exception as e:
                    st.error(f"Error during retraining: {e}")
                    db.log_activity("admin", f"ML model retraining failed: {e}", "Reports Panel")
