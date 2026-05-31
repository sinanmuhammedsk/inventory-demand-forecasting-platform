import os
import pandas as pd

# Paths
def main():
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    csv_path = os.path.join(base_dir, "dataset", "processed", "analytical_dataset.csv")
    parquet_path = os.path.join(base_dir, "dataset", "processed", "analytical_dataset.parquet")
    if not os.path.exists(csv_path):
        print(f"CSV not found at {csv_path}")
        return
    if os.path.exists(parquet_path):
        print(f"Parquet already exists at {parquet_path}, skipping conversion.")
        return
    print(f"Reading CSV from {csv_path} ...")
    df = pd.read_csv(csv_path)
    # Ensure date column is datetime for proper storage
    if "Date" in df.columns:
        df["Date"] = pd.to_datetime(df["Date"])
    print(f"Writing Parquet to {parquet_path} ...")
    df.to_parquet(parquet_path, index=False)
    print("Conversion completed.")

if __name__ == "__main__":
    main()
