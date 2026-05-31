import os
import pandas as pd
import numpy as np
from .predictor import DemandPredictor
from ..database.db_manager import DatabaseManager

class InventoryRecommender:
    def __init__(self):
        self.predictor = DemandPredictor()
        self.db = DatabaseManager()
        
    def get_historical_metrics(self, store, dept):
        """Fetches historical sales statistics to calculate safety stock parameters."""
        # Use database to calculate stats
        sales_df = self.db.load_historical_sales(store=store, dept=dept, limit=1000)
        
        if len(sales_df) == 0:
            # Fallback values if store-dept is not in historical data
            return {
                "mean_weekly_sales": 15000.0,
                "std_weekly_sales": 3000.0
            }
            
        return {
            "mean_weekly_sales": sales_df['weekly_sales'].mean(),
            "std_weekly_sales": sales_df['weekly_sales'].std() if len(sales_df) > 1 else 0.0
        }

    def generate_recommendation(self, store, dept, current_stock, lead_time_weeks=2, service_level=0.95, horizon_days=30):
        """
        Calculates demand forecast, safety stock, reorder point, and returns a dict with recommendations.
        """
        # 1. Fetch Forecast
        forecast_df = self.predictor.forecast_demand(store, dept, horizon_days)
        expected_demand = forecast_df['Forecast'].sum()
        num_weeks = len(forecast_df)
        
        # 2. Fetch Historical Stats for Safety Stock
        hist_stats = self.get_historical_metrics(store, dept)
        std_sales = hist_stats["std_weekly_sales"]
        mean_sales = hist_stats["mean_weekly_sales"]
        
        # Service level multiplier (Z-score)
        # 90% -> 1.28, 95% -> 1.645, 99% -> 2.33
        z_scores = {0.90: 1.28, 0.95: 1.645, 0.99: 2.33}
        z = z_scores.get(service_level, 1.645)
        
        # Safety Stock formula: Z * std_dev * sqrt(lead_time)
        # Note: Lead time is in weeks, std_dev is weekly
        safety_stock = z * std_sales * np.sqrt(lead_time_weeks)
        if pd.isna(safety_stock) or safety_stock == 0:
            # Fallback safety stock if no std dev is found
            safety_stock = 0.2 * mean_sales * np.sqrt(lead_time_weeks)
            
        # 3. Calculate Reorder Point (ROP)
        # ROP = (Average Weekly Sales * Lead Time Weeks) + Safety Stock
        weekly_demand = expected_demand / num_weeks
        reorder_point = (weekly_demand * lead_time_weeks) + safety_stock
        
        # Target Stock Level (Order-up-to level)
        # Target = Expected Demand + Safety Stock
        target_stock = expected_demand + safety_stock
        
        # 4. Determine Alerts & Actions
        reorder_qty = 0
        rec_type = "OK_OPTIMAL"
        recommendation_text = "Inventory level is optimal. No action needed."
        excess_stock = 0
        estimated_cost = 0.0
        
        # Simulating cost per unit (e.g. $10 average cost)
        unit_cost = 10.0
        
        if current_stock < reorder_point:
            rec_type = "LOW_STOCK_REORDER"
            reorder_qty = int(np.ceil(target_stock - current_stock))
            estimated_cost = reorder_qty * unit_cost
            recommendation_text = f"CRITICAL: Stock is below reorder point ({int(reorder_point)} units). Reorder {reorder_qty} units immediately."
        elif current_stock > (expected_demand + safety_stock * 2):
            rec_type = "OVERSTOCK_LIQUIDATE"
            excess_stock = int(current_stock - target_stock)
            recommendation_text = f"WARNING: Overstock detected. Excess inventory of {excess_stock} units. Consider promotional discounts or distribution shift."
            estimated_cost = excess_stock * 1.5 # Holding penalty
            
        result = {
            "store": store,
            "dept": dept,
            "current_stock": int(current_stock),
            "expected_demand": int(expected_demand),
            "safety_stock": int(safety_stock),
            "reorder_point": int(reorder_point),
            "target_stock": int(target_stock),
            "recommendation_type": rec_type,
            "recommended_quantity": reorder_qty,
            "excess_stock": excess_stock,
            "estimated_cost": float(estimated_cost),
            "recommendation_text": recommendation_text,
            "forecast_df": forecast_df
        }
        
        # Save to Recommendation History database
        try:
            self.db.save_recommendation(
                store=store,
                dept=dept,
                current_stock=int(current_stock),
                forecasted_demand=int(expected_demand),
                rec_type=rec_type,
                quantity=reorder_qty,
                cost=float(estimated_cost)
            )
        except Exception as e:
            print(f"Error saving recommendation to DB: {e}")
            
        return result

if __name__ == "__main__":
    recommender = InventoryRecommender()
    rec = recommender.generate_recommendation(1, 1, 150, lead_time_weeks=2, service_level=0.95, horizon_days=30)
    print("Recommendation Type:", rec["recommendation_type"])
    print("Quantity:", rec["recommended_quantity"])
    print("ROP:", rec["reorder_point"])
    print("Text:", rec["recommendation_text"])
