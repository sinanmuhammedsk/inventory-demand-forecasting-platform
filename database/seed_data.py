import os
import sys
import pandas as pd
import sqlite3

# Ensure the project root is on the import path when this script is run directly
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from database.db_manager import DatabaseManager

def seed():
    """Seed the database from the raw train.csv (always available in Git, NOT in LFS)."""
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

    # -------------------------------------------------------------------
    # Priority 1: raw/train.csv  (421k rows, Git-tracked, no LFS)
    # Priority 2: processed/analytical_dataset.parquet  (local builds)
    # Priority 3: processed/analytical_dataset.csv       (local, LFS – may be empty on Cloud)
    # -------------------------------------------------------------------
    base = os.path.dirname(os.path.abspath(__file__))

    raw_train = os.path.join(base, "..", "dataset", "raw", "train.csv")
    parquet   = os.path.join(base, "..", "dataset", "processed", "analytical_dataset.parquet")
    csv_proc  = os.path.join(base, "..", "dataset", "processed", "analytical_dataset.csv")

    df = None

    # Try raw train.csv first — always present on Streamlit Cloud
    if os.path.exists(raw_train):
        size = os.path.getsize(raw_train)
        if size > 1024:          # pointer files are <200 bytes; real data is MB-scale
            print(f"Loading raw train.csv ({size/1e6:.1f} MB)...")
            df = pd.read_csv(raw_train)
            df = df.rename(columns={
                "Store":        "store",
                "Dept":         "dept",
                "Date":         "date",
                "Weekly_Sales": "weekly_sales",
                "IsHoliday":    "is_holiday",
            })
            df["is_holiday"] = df["is_holiday"].astype(int)
            df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")
            print(f"  Loaded {len(df):,} rows from train.csv")
        else:
            print("train.csv appears to be a Git-LFS pointer; skipping.")

    # Fallback: Parquet (local builds)
    if df is None and os.path.exists(parquet):
        size = os.path.getsize(parquet)
        if size > 1024:
            print(f"Loading Parquet ({size/1e6:.1f} MB)...")
            df = pd.read_parquet(parquet)
            df = df.rename(columns={
                "Store":        "store",
                "Dept":         "dept",
                "Date":         "date",
                "Weekly_Sales": "weekly_sales",
                "IsHoliday":    "is_holiday",
            })
            df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")
            print(f"  Loaded {len(df):,} rows from parquet")
        else:
            print("Parquet appears to be a Git-LFS pointer; skipping.")

    # Fallback: processed CSV (may also be LFS on Cloud)
    if df is None and os.path.exists(csv_proc):
        size = os.path.getsize(csv_proc)
        if size > 1024:
            print(f"Loading processed CSV ({size/1e6:.1f} MB)...")
            df = pd.read_csv(csv_proc)
            df = df.rename(columns={
                "Store":        "store",
                "Dept":         "dept",
                "Date":         "date",
                "Weekly_Sales": "weekly_sales",
                "IsHoliday":    "is_holiday",
            })
            df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")
            print(f"  Loaded {len(df):,} rows from processed CSV")
        else:
            print("Processed CSV appears to be a Git-LFS pointer; skipping.")

    if df is None:
        print("ERROR: No usable data source found. Seeding aborted.")
        return

    # Only keep columns the DB expects; drop any extras silently
    keep = ["store", "dept", "date", "weekly_sales", "is_holiday"]
    df = df[[c for c in keep if c in df.columns]]

    # Bulk insert with SQLite speed pragmas
    conn = db.get_connection()
    if db.db_mode == "SQLITE":
        cursor = conn.cursor()
        cursor.execute("PRAGMA journal_mode = OFF;")
        cursor.execute("PRAGMA synchronous = OFF;")
        conn.commit()

    try:
        df.to_sql("sales_data", conn, if_exists="append", index=False,
                  chunksize=10000)
        print(f"Database seeding completed: {len(df):,} rows inserted.")
    except Exception as e:
        print(f"Error during bulk insert: {e}")
    finally:
        conn.close()


if __name__ == "__main__":
    seed()
