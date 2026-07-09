import os
import tempfile
import sqlite3
import datetime
import pandas as pd

try:
    import pymysql
    PYMYSQL_AVAILABLE = True
except ImportError:
    PYMYSQL_AVAILABLE = False

class DatabaseManager:
    def __init__(self):
        # Database selection config
        self.mysql_host = os.environ.get("MYSQL_HOST")
        self.mysql_user = os.environ.get("MYSQL_USER")
        self.mysql_password = os.environ.get("MYSQL_PASSWORD")
        self.mysql_db = os.environ.get("MYSQL_DB", "inventory_forecast_db")
        self.mysql_port = int(os.environ.get("MYSQL_PORT", 3306))
        
        # Use a path relative to the project root for cross‑platform compatibility
        # Use a temporary writable directory for SQLite DB (required on read‑only deployments like Streamlit Cloud)
        self.sqlite_db_path = os.path.join(tempfile.gettempdir(), "inventory_forecast.db")
        self.db_mode = "SQLITE"
        
        # Check if we should use MySQL
        if self.mysql_host and self.mysql_user and PYMYSQL_AVAILABLE:
            self.db_mode = "MYSQL"
            
        print(f"Database Manager initialized in {self.db_mode} mode.")

        # Bootstrap SQLite DB by copying existing seeded database if it doesn't exist in temp directory
        if self.db_mode == "SQLITE" and not os.path.exists(self.sqlite_db_path):
            import shutil
            repo_db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "inventory_forecast.db")
            if os.path.exists(repo_db_path):
                try:
                    os.makedirs(os.path.dirname(self.sqlite_db_path), exist_ok=True)
                    shutil.copy2(repo_db_path, self.sqlite_db_path)
                    print(f"Successfully bootstrapped SQLite DB from {repo_db_path} to {self.sqlite_db_path}")
                except Exception as e:
                    print(f"Failed to bootstrap pre-seeded SQLite DB: {e}")

    def get_connection(self):
        """Returns a database connection based on config mode."""
        if self.db_mode == "MYSQL":
            try:
                conn = pymysql.connect(
                    host=self.mysql_host,
                    user=self.mysql_user,
                    password=self.mysql_password,
                    database=self.mysql_db,
                    port=self.mysql_port,
                    autocommit=True
                )
                return conn
            except Exception as e:
                print(f"Error connecting to MySQL: {e}. Falling back to SQLite.")
                # Temporary fallback
                os.makedirs(os.path.dirname(self.sqlite_db_path), exist_ok=True)
                return sqlite3.connect(self.sqlite_db_path)
        else:
            os.makedirs(os.path.dirname(self.sqlite_db_path), exist_ok=True)
            return sqlite3.connect(self.sqlite_db_path)

    def init_db(self):
        """Initializes database tables depending on the mode."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        if self.db_mode == "MYSQL" and not isinstance(conn, sqlite3.Connection):
            # MySQL DDL
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS {self.mysql_db}")
            cursor.execute(f"USE {self.mysql_db}")
            
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS sales_data (
                id INT AUTO_INCREMENT PRIMARY KEY,
                store INT NOT NULL,
                dept INT NOT NULL,
                date DATE NOT NULL,
                weekly_sales DOUBLE NOT NULL,
                is_holiday INT DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE KEY uq_store_dept_date (store, dept, date)
            )
            """)
            
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS forecast_results (
                id INT AUTO_INCREMENT PRIMARY KEY,
                store INT NOT NULL,
                dept INT NOT NULL,
                forecast_date DATE NOT NULL,
                horizon_days INT NOT NULL,
                forecast_value DOUBLE NOT NULL,
                lower_ci DOUBLE,
                upper_ci DOUBLE,
                run_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)
            
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS recommendation_history (
                id INT AUTO_INCREMENT PRIMARY KEY,
                store INT NOT NULL,
                dept INT NOT NULL,
                current_stock INT NOT NULL,
                forecasted_demand INT NOT NULL,
                recommendation_type VARCHAR(50) NOT NULL,
                recommended_quantity INT NOT NULL,
                estimated_cost DOUBLE,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)
            
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_activity_logs (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_name VARCHAR(100) DEFAULT 'admin',
                action_performed VARCHAR(255) NOT NULL,
                page_visited VARCHAR(100) NOT NULL,
                details TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)
        else:
            # SQLite DDL (auto_increment is handled slightly differently in SQLite)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS sales_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                store INTEGER NOT NULL,
                dept INTEGER NOT NULL,
                date TEXT NOT NULL,
                weekly_sales REAL NOT NULL,
                is_holiday INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (store, dept, date)
            )
            """)
            
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS forecast_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                store INTEGER NOT NULL,
                dept INTEGER NOT NULL,
                forecast_date TEXT NOT NULL,
                horizon_days INTEGER NOT NULL,
                forecast_value REAL NOT NULL,
                lower_ci REAL,
                upper_ci REAL,
                run_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)
            
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS recommendation_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                store INTEGER NOT NULL,
                dept INTEGER NOT NULL,
                current_stock INTEGER NOT NULL,
                forecasted_demand INTEGER NOT NULL,
                recommendation_type TEXT NOT NULL,
                recommended_quantity INTEGER NOT NULL,
                estimated_cost REAL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)
            
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_activity_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_name TEXT DEFAULT 'admin',
                action_performed TEXT NOT NULL,
                page_visited TEXT NOT NULL,
                details TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)
            
        conn.commit()
        conn.close()
        print("Database tables initialized successfully.")

    def log_activity(self, user_name, action_performed, page_visited, details=None):
        """Logs user dashboard interactions."""
        conn = self.get_connection()
        cursor = conn.cursor()
        query = """
        INSERT INTO user_activity_logs (user_name, action_performed, page_visited, details)
        VALUES (%s, %s, %s, %s)
        """ if self.db_mode == "MYSQL" and not isinstance(conn, sqlite3.Connection) else """
        INSERT INTO user_activity_logs (user_name, action_performed, page_visited, details)
        VALUES (?, ?, ?, ?)
        """
        cursor.execute(query, (user_name, action_performed, page_visited, details))
        conn.commit()
        conn.close()

    def save_forecast_results(self, store, dept, forecast_date, horizon_days, forecast_value, lower_ci=None, upper_ci=None):
        """Saves generated forecasting points."""
        conn = self.get_connection()
        cursor = conn.cursor()
        query = """
        INSERT INTO forecast_results (store, dept, forecast_date, horizon_days, forecast_value, lower_ci, upper_ci)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """ if self.db_mode == "MYSQL" and not isinstance(conn, sqlite3.Connection) else """
        INSERT INTO forecast_results (store, dept, forecast_date, horizon_days, forecast_value, lower_ci, upper_ci)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        if isinstance(forecast_date, datetime.date):
            forecast_date = forecast_date.strftime("%Y-%m-%d")
        cursor.execute(query, (store, dept, forecast_date, horizon_days, forecast_value, lower_ci, upper_ci))
        conn.commit()
        conn.close()

    def save_recommendation(self, store, dept, current_stock, forecasted_demand, rec_type, quantity, cost=None):
        """Logs action recommendations."""
        conn = self.get_connection()
        cursor = conn.cursor()
        query = """
        INSERT INTO recommendation_history (store, dept, current_stock, forecasted_demand, recommendation_type, recommended_quantity, estimated_cost)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """ if self.db_mode == "MYSQL" and not isinstance(conn, sqlite3.Connection) else """
        INSERT INTO recommendation_history (store, dept, current_stock, forecasted_demand, recommendation_type, recommended_quantity, estimated_cost)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        cursor.execute(query, (store, dept, current_stock, forecasted_demand, rec_type, quantity, cost))
        conn.commit()
        conn.close()

    def get_activity_logs(self, limit=100):
        """Pulls user activity logs."""
        conn = self.get_connection()
        query = f"SELECT user_name, action_performed, page_visited, details, timestamp FROM user_activity_logs ORDER BY timestamp DESC LIMIT {limit}"
        df = pd.read_sql(query, conn)
        conn.close()
        return df

    def get_recommendation_history(self, limit=100):
        """Pulls recommendation history."""
        conn = self.get_connection()
        query = f"SELECT store, dept, current_stock, forecasted_demand, recommendation_type, recommended_quantity, estimated_cost, timestamp FROM recommendation_history ORDER BY timestamp DESC LIMIT {limit}"
        df = pd.read_sql(query, conn)
        conn.close()
        return df

    def load_historical_sales(self, store=None, dept=None, limit=1000):
        """Fetches sales data for analysis."""
        conn = self.get_connection()
        where_clause = []
        params = []
        if store is not None:
            where_clause.append("store = %s" if self.db_mode == "MYSQL" and not isinstance(conn, sqlite3.Connection) else "store = ?")
            params.append(store)
        if dept is not None:
            where_clause.append("dept = %s" if self.db_mode == "MYSQL" and not isinstance(conn, sqlite3.Connection) else "dept = ?")
            params.append(dept)
            
        sql = "SELECT store, dept, date, weekly_sales, is_holiday FROM sales_data"
        if where_clause:
            sql += " WHERE " + " AND ".join(where_clause)
        sql += " ORDER BY date DESC"
        if limit:
            sql += f" LIMIT {limit}"
            
        df = pd.read_sql(sql, conn, params=params)
        conn.close()
        return df

    def bulk_insert_sales_data(self, df):
        """Loads historical sales records into database (efficient batch execution)."""
        print(f"Bulk inserting {len(df):,} sales rows to DB...")
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Prepare list of tuples
        data = []
        for _, row in df.iterrows():
            d_str = row['Date'].strftime("%Y-%m-%d") if isinstance(row['Date'], datetime.datetime) or hasattr(row['Date'], 'strftime') else str(row['Date'])[:10]
            data.append((
                int(row['Store']),
                int(row['Dept']),
                d_str,
                float(row['Weekly_Sales']),
                int(row['IsHoliday'])
            ))
            
        query = """
        INSERT INTO sales_data (store, dept, date, weekly_sales, is_holiday)
        VALUES (%s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE weekly_sales = VALUES(weekly_sales), is_holiday = VALUES(is_holiday)
        """ if self.db_mode == "MYSQL" and not isinstance(conn, sqlite3.Connection) else """
        INSERT OR REPLACE INTO sales_data (store, dept, date, weekly_sales, is_holiday)
        VALUES (?, ?, ?, ?, ?)
        """
        
        # Batch insert by 10k rows
        batch_size = 10000
        for i in range(0, len(data), batch_size):
            batch = data[i:i+batch_size]
            cursor.executemany(query, batch)
            conn.commit()
            print(f"Inserted batch {i//batch_size + 1}/{len(data)//batch_size + 1}")
            
        conn.close()
        print("Bulk insert complete.")

if __name__ == "__main__":
    db = DatabaseManager()
    db.init_db()
