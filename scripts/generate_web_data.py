import os
import json
import sqlite3
import pandas as pd
import numpy as np

# Define paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "database", "inventory_forecast.db")
STORES_CSV = os.path.join(BASE_DIR, "dataset", "raw", "stores.csv")
FEATURES_CSV = os.path.join(BASE_DIR, "dataset", "raw", "features.csv")
OUT_JSON = os.path.join(BASE_DIR, "web", "data_summary.json")

# Ensure output directory exists
os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)

# Complete Mappings from dashboard/mappings.py
STORE_CITIES = {
    1: "Bentonville, AR (HQ)",
    2: "Dallas, TX",
    3: "Chicago, IL",
    4: "Houston, TX",
    5: "Atlanta, GA",
    6: "Miami, FL",
    7: "Phoenix, AZ",
    8: "Los Angeles, CA",
    9: "San Antonio, TX",
    10: "San Diego, CA",
    11: "Philadelphia, PA",
    12: "San Jose, CA",
    13: "Austin, TX",
    14: "Jacksonville, FL",
    15: "Fort Worth, TX",
    16: "Columbus, OH",
    17: "Charlotte, NC",
    18: "San Francisco, CA",
    19: "Indianapolis, IN",
    20: "Seattle, WA",
    21: "Denver, CO",
    22: "Boston, MA",
    23: "El Paso, TX",
    24: "Nashville, TN",
    25: "Detroit, MI",
    26: "Oklahoma City, OK",
    27: "Portland, OR",
    28: "Las Vegas, NV",
    29: "Memphis, TN",
    30: "Louisville, KY",
    31: "Baltimore, MD",
    32: "Milwaukee, WI",
    33: "Albuquerque, NM",
    34: "Tucson, AZ",
    35: "Fresno, CA",
    36: "Sacramento, CA",
    37: "Kansas City, MO",
    38: "Mesa, AZ",
    39: "Virginia Beach, VA",
    40: "Atlanta, GA (North)",
    41: "Omaha, NE",
    42: "Colorado Springs, CO",
    43: "Raleigh, NC",
    44: "Minneapolis, MN",
    45: "Tampa, FL"
}

DEPT_NAMES = {
    1: "Candy & Tobacco",
    2: "Cosmetics & HABA",
    3: "Stationery & School",
    4: "Household Paper Goods",
    5: "Media & DVDs",
    6: "Photo & Portrait",
    7: "Toys & Hobbies",
    8: "Pets & Supplies",
    9: "Sporting Goods",
    10: "Automotive Accessories",
    11: "Hardware & Tools",
    12: "Paint & Decorating",
    13: "Household Chemicals",
    14: "Kitchen & Cookware",
    16: "Lawn & Garden",
    17: "Home Decor & Candles",
    18: "Seasonal Accessories",
    19: "Crafts & Sewing",
    20: "Bath & Bedding",
    21: "Books & Magazines",
    22: "Bedding Linens",
    23: "Furniture & Decor",
    24: "Office Products",
    25: "Consumer Electronics",
    26: "Computers & Software",
    27: "Phones & Wireless",
    28: "Home Audio & Theatre",
    29: "Cameras & Optics",
    30: "Small Appliances",
    31: "Large Appliances",
    32: "Smart Home & Automation",
    33: "Musical Instruments",
    34: "Luggage & Travel",
    35: "Fitness Equipment",
    36: "Outdoor Sports",
    37: "Indoor Sports",
    38: "Apparel - Men's",
    39: "Apparel - Women's",
    40: "Apparel - Kids & Baby",
    41: "Footwear - Men's",
    42: "Footwear - Women's",
    43: "Footwear - Kids & Athletic",
    44: "Jewelry & Watches",
    45: "Bags & Leather Goods",
    46: "Dry Grocery",
    47: "Bakery & Desserts",
    48: "Fresh Produce",
    49: "Meat & Poultry",
    50: "Seafood & Fish",
    51: "Dairy & Eggs",
    52: "Frozen Foods",
    54: "Deli & Prepared Meals",
    55: "Beverages & Water",
    56: "Snacks & Confectionery",
    58: "Canned & Packaged Foods",
    59: "Baking & Condiments",
    60: "International Foods",
    65: "Health & Pharmacy",
    67: "Personal Care",
    71: "Baby Products",
    72: "Toys - Preschool",
    74: "Seasonal Apparel",
    77: "Luggage & Accessories",
    78: "Party Supplies",
    79: "Greeting Cards",
    80: "Party Accessories",
    81: "Garden Center",
    82: "Outdoor Living",
    83: "Grills & Patio Furniture",
    85: "Storage & Organization",
    87: "Home Improvement",
    90: "Grocery - Bulk",
    91: "Apparel - Intimates",
    92: "Apparel - Activewear",
    93: "Beauty & Fragrance",
    94: "Personal Care - Hair",
    95: "Personal Care - Body",
    96: "Household Cleaners",
    97: "Apparel - Accessories",
    98: "Apparel - Maternity",
    99: "Dry Grocery - Baking"
}

def get_store_label(store_id):
    city = STORE_CITIES.get(int(store_id), "Unknown")
    return f"Store #{store_id} ({city})"

def get_dept_label(dept_id):
    name = DEPT_NAMES.get(int(dept_id), "General Dept")
    return f"Dept #{dept_id} ({name})"


def main():
    print(f"Connecting to database: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    
    # 1. Historical Sales Data Loading
    print("Loading historical sales...")
    sales_df = pd.read_sql_query("SELECT store, dept, date, weekly_sales, is_holiday FROM sales_data", conn)
    sales_df['date'] = pd.to_datetime(sales_df['date'])
    print(f"Loaded {len(sales_df):,} sales rows.")
    
    # 2. Load features if present
    print("Loading and joining features.csv...")
    features_df = None
    if os.path.exists(FEATURES_CSV):
        try:
            features_df = pd.read_csv(FEATURES_CSV)
            features_df['Date'] = pd.to_datetime(features_df['Date'])
            print(f"Loaded {len(features_df):,} feature rows.")
        except Exception as e:
            print(f"Failed to read features.csv: {e}")
            
    # 3. Load stores if present
    print("Loading stores.csv...")
    stores_df = None
    if os.path.exists(STORES_CSV):
        try:
            stores_df = pd.read_csv(STORES_CSV)
            stores_df.columns = stores_df.columns.str.lower()
            print(f"Loaded {len(stores_df):,} stores.")
        except Exception as e:
            print(f"Failed to read stores.csv: {e}")
            
    # Calculate executive metrics
    print("Calculating executive KPIs...")
    total_rev = float(sales_df['weekly_sales'].sum())
    avg_weekly = float(sales_df['weekly_sales'].mean())
    num_stores = int(sales_df['store'].nunique())
    num_depts = int(sales_df['dept'].nunique())
    
    # Extract unique stores and departments
    unique_stores = sorted([int(x) for x in sales_df['store'].unique()])
    unique_depts = sorted([int(x) for x in sales_df['dept'].unique()])
    
    # Historical Sales Trend (Monthly)
    print("Grouping sales by month...")
    sales_df['month'] = sales_df['date'].dt.strftime('%Y-%m')
    monthly_sales = sales_df.groupby('month')['weekly_sales'].sum().reset_index()
    monthly_sales_list = monthly_sales.rename(columns={'weekly_sales': 'sales'}).to_dict(orient='records')
    
    # Store Revenue Contribution by Type
    store_type_list = []
    if stores_df is not None:
        print("Grouping store sales by type...")
        store_sales = sales_df.groupby('store')['weekly_sales'].sum().reset_index()
        merged_type = pd.merge(store_sales, stores_df, on='store', how='left')
        type_sales = merged_type.groupby('type')['weekly_sales'].sum().reset_index()
        store_type_list = type_sales.rename(columns={'weekly_sales': 'sales'}).to_dict(orient='records')
        
    # Top 10 stores
    print("Locating top 10 stores...")
    top_10 = sales_df.groupby('store')['weekly_sales'].sum().reset_index()
    top_10 = top_10.sort_values('weekly_sales', ascending=False).head(10)
    top_10['label'] = top_10['store'].apply(get_store_label)
    top_10['city'] = top_10['store'].apply(lambda x: STORE_CITIES.get(int(x), "Unknown"))
    top_10_list = top_10.rename(columns={'weekly_sales': 'sales'}).to_dict(orient='records')
    
    # Seasonal Sales Averages
    print("Calculating seasonal averages...")
    sales_df['month_num'] = sales_df['date'].dt.month
    def get_season(m):
        if m in [12, 1, 2]: return 'Winter'
        elif m in [3, 4, 5]: return 'Spring'
        elif m in [6, 7, 8]: return 'Summer'
        else: return 'Fall'
    sales_df['season'] = sales_df['month_num'].apply(get_season)
    season_avg = sales_df.groupby('season')['weekly_sales'].mean().reset_index()
    season_order = {'Spring': 0, 'Summer': 1, 'Fall': 2, 'Winter': 3}
    season_avg['order'] = season_avg['season'].map(season_order)
    season_avg = season_avg.sort_values('order')
    season_list = season_avg[['season', 'weekly_sales']].rename(columns={'weekly_sales': 'avg_sales'}).to_dict(orient='records')
    
    # Store-Department Statistics
    # Map each store & department to its statistical properties and its last 12 weeks history
    print("Generating store-department stats & history...")
    store_dept_stats = {}
    
    # Group by store, dept to compute stats
    grp = sales_df.groupby(['store', 'dept'])
    means = grp['weekly_sales'].mean()
    stds = grp['weekly_sales'].std().fillna(0)
    medians = grp['weekly_sales'].median()
    
    # Build dictionary
    # For large datasets, let's keep keys stringified for JSON compatibility, e.g. "store_dept"
    for (s, d), mean_val in means.items():
        s = int(s)
        d = int(d)
        
        # Get history (last 12 weeks of sales)
        history_df = sales_df[(sales_df['store'] == s) & (sales_df['dept'] == d)]
        history_df = history_df.sort_values('date', ascending=True).tail(12)
        
        history_list = []
        for _, r in history_df.iterrows():
            history_list.append({
                'date': r['date'].strftime('%Y-%m-%d'),
                'weekly_sales': float(r['weekly_sales']),
                'is_holiday': int(r['is_holiday'])
            })
            
        key = f"{s}_{d}"
        store_dept_stats[key] = {
            'mean': float(mean_val),
            'std': float(stds.get((s, d), 0.0)),
            'median': float(medians.get((s, d), mean_val)),
            'history': history_list
        }
        
    # Store level weekly indicators for correlations (CPI, fuel, unemployment, is_holiday)
    # We group by (store, date) to merge with features or calculate aggregates
    print("Compiling macroeconomic and store level weekly data...")
    store_weekly_data = []
    
    # Group sales_df by store, date and is_holiday
    store_daily = sales_df.groupby(['store', 'date', 'is_holiday'])['weekly_sales'].sum().reset_index()
    
    if features_df is not None:
        merged_features = pd.merge(store_daily, features_df, left_on=['store', 'date'], right_on=['Store', 'Date'], how='left')
        # Select required columns and convert to clean list
        # Replace NaN with 0 or mean values using ffill and bfill
        merged_features['CPI'] = merged_features['CPI'].ffill().bfill().fillna(210.0)
        merged_features['Unemployment'] = merged_features['Unemployment'].ffill().bfill().fillna(7.5)
        merged_features['Fuel_Price'] = merged_features['Fuel_Price'].ffill().bfill().fillna(3.2)
        merged_features['Temperature'] = merged_features['Temperature'].ffill().bfill().fillna(60.0)
        merged_features['IsHoliday'] = merged_features['is_holiday'].fillna(0).astype(int)
        
        for _, row in merged_features.iterrows():
            store_weekly_data.append({
                'store': int(row['store']),
                'date': row['date'].strftime('%Y-%m-%d'),
                'weekly_sales': float(row['weekly_sales']),
                'cpi': float(row['CPI']),
                'unemployment': float(row['Unemployment']),
                'fuel_price': float(row['Fuel_Price']),
                'temperature': float(row['Temperature']),
                'is_holiday': int(row['IsHoliday'])
            })
    else:
        # Simple fallback
        for _, row in store_daily.iterrows():
            store_weekly_data.append({
                'store': int(row['store']),
                'date': row['date'].strftime('%Y-%m-%d'),
                'weekly_sales': float(row['weekly_sales']),
                'cpi': 210.0,
                'unemployment': 7.5,
                'fuel_price': 3.2,
                'temperature': 60.0,
                'is_holiday': int(row['is_holiday'])
            })

    # Assemble payload
    payload = {
        'kpis': {
            'total_revenue': total_rev,
            'avg_weekly_sales': avg_weekly,
            'num_stores': num_stores,
            'num_depts': num_depts
        },
        'stores': unique_stores,
        'departments': unique_depts,
        'store_labels': {s: get_store_label(s) for s in unique_stores},
        'dept_labels': {d: get_dept_label(d) for d in unique_depts},
        'monthly_sales': monthly_sales_list,
        'store_type_sales': store_type_list,
        'top_10_stores': top_10_list,
        'seasonal_avg': season_list,
        'store_dept_stats': store_dept_stats,
        'store_weekly_data': store_weekly_data
    }
    
    print(f"Writing payload to {OUT_JSON}...")
    with open(OUT_JSON, 'w') as f:
        json.dump(payload, f, indent=2)
        
    conn.close()
    print("Data extraction complete!")

if __name__ == "__main__":
    main()
