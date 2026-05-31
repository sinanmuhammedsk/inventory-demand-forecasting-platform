import os
import sys
import pandas as pd
import sqlite3

# Ensure the project root is on the import path when this script is run directly
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from database.db_manager import DatabaseManager

def seed():
    print("Starting database seeding...")
    db = DatabaseManager()
    db.init_db()

    # Check if sales_data already has rows
    conn = db.get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT COUNT(*) FROM sales_data")
        count = cursor.fetchone()[0]
    except Exception as e:
        print(f"Error checking sales_data table: {e}")
        count = 0
    finally:
        conn.close()

    if count > 0:
        print(f"Database already seeded with {count:,} records. Skipping.")
        return

    # Resolve path to dataset
    parquet_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "dataset", "processed", "analytical_dataset.parquet"
    )
    csv_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "dataset", "processed", "analytical_dataset.csv"
    )

    if os.path.exists(parquet_path):
        print(f"Loading processed dataset from {parquet_path}...")
        df = pd.read_parquet(parquet_path)
    elif os.path.exists(csv_path):
        print(f"Loading processed dataset from {csv_path}...")
        df = pd.read_csv(csv_path)
    else:
        print("Processed analytical dataset not found. Seeding skipped.")
        return

    # Align column names with DB schema (same for CSV or Parquet)
    df = df.rename(columns={
        "Store": "store",
        "Dept": "dept",
        "Date": "date",
        "Weekly_Sales": "weekly_sales",
        "IsHoliday": "is_holiday",
    })
    df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")

    # Speed up bulk insert for SQLite
    conn = db.get_connection()
    if db.db_mode == "SQLITE":
        cursor = conn.cursor()
        cursor.execute("PRAGMA journal_mode = OFF;")
        cursor.execute("PRAGMA synchronous = OFF;")
        conn.commit()
    try:
        df.to_sql("sales_data", conn, if_exists="append", index=False, chunksize=10000, method="multi")
        print("Database seeding completed successfully.")
    except Exception as e:
        print(f"Error during bulk insert: {e}")
    finally:
        conn.close()


if __name__ == "__main__":
    seed()
