# 📦 Inventory Demand Forecasting & Stock Optimization System

An end-to-end, production-ready Business Intelligence (BI) and predictive analytics dashboard. This platform leverages machine learning models trained on real-world retail data to forecast weekly demand, optimize safety stock thresholds, trigger restocking triggers, and audit warehouse inventory gaps.

[Inventory Demand Forecasting Web Dashboard (Vercel-Deployed)](https://inventory-demand-forecasting-platfo.vercel.app/)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## 🚀 System Architecture Flow

```
                      +-----------------------------+
                      |   Walmart Raw Datasets      |
                      | (Sales, Stores, features)   |
                      +--------------+--------------+
                                     |
                                     v
                      +-----------------------------+
                      |    Preprocessing Pipeline   |
                      |  - Missing values median    |
                      |  - Winsorize sales outliers |
                      +--------------+--------------+
                                     |
                                     v
                      +-----------------------------+
                      |    Feature Engineering      |
                      |  - Temporal: Week, Month... |
                      |  - Holiday specific dummies |
                      +--------------+--------------+
                                     |
                                     v
                      +--------------+--------------+
                      |      ML Modeling & CV       |
                      |  - Linear Reg vs RF vs XGB  |
                      |  - Chronological splitting  |
                      +--------------+--------------+
                                     | (Best Model: RF)
                                     v
                      +-----------------------------+
                      |  Demand Forecasting Engine  |
                      |  - 7D, 30D, 90D Horizons    |
                      |  - 95% Confidence Bounds    |
                      +--------------+--------------+
                                     |
                                     v
                      +-----------------------------+
                      |   Inventory Recommendations |
                      |  - Safety Stock Calculation |
                      |  - Reorder Point (ROP)      |
                      +--------------+--------------+
                                     |
                                     v
                      +-----------------------------+
                      |  Streamlit BI Interface     |
                      |  - SQLite/MySQL Persistence |
                      |  - Audit Log Tracking       |
                      +-----------------------------+
```

---

## ⚡ Core Features

*   **Executive KPI Dashboard**: High-level corporate view containing Total Revenue, Average Sales, Active Stores, Forecasted Demand, and a dynamic Inventory Risk Index.
*   **Granular Market Analytics**: Multi-dimensional interactive filters (Store, Department, Date Range, Holiday status) displaying sales trends and correlations.
*   **Macroeconomic Impact Evaluator**: Interactive scatter plots evaluating the impact of CPI, Unemployment rates, and Fuel Prices on consumer demand.
*   **Predictive Forecasting Engine**: Generates demand forecasts for 7, 30, and 90 days. Uses the best-fit machine learning model to display future trends with shaded 95% confidence intervals.
*   **Restocking Optimization Engine**: Calculates Safety Stock and Reorder Points (ROP) using service levels (90%, 95%, 99%) and supplier lead times, flagging LOW STOCK and OVERSTOCK alerts with projected restocking costs.
*   **Audit Logger & Reports Panel**: Logs page-level user sessions and writes forecast outcomes/replenishment sheets to local CSV and Excel exports. Supports on-demand model retraining from the UI.
*   **Hybrid Database Connector**: Out-of-the-box support for both high-performance MySQL (production) and self-contained SQLite (local sandbox).

---

## 📊 Dataset Information

This system uses the official **Walmart Sales Forecasting Dataset** from Kaggle:
*   `stores.csv`: Metadata for 45 Walmart stores (Store ID, Type, Size).
*   `train.csv`: Historical weekly sales records from 2010-02-05 to 2012-10-26 (Store, Dept, Date, Weekly_Sales, IsHoliday).
*   `features.csv`: Store-specific environmental variables (Temperature, Fuel_Price, CPI, Unemployment, Markdowns).

---

## 📈 Model Performance & Selection

During chronological cross-validation (training before `2012-05-01`, validation on or after `2012-05-01`), the models achieved the following results:

| Machine Learning Model | Validation RMSE ($) | Validation MAE ($) | Validation $R^2$ Score |
| :--- | :--- | :--- | :--- |
| **Linear Regression** | 20,997.17 | 14,696.27 | 0.0918 |
| **XGBoost Regressor** | 6,526.14 | 3,988.45 | 0.9123 |
| **Random Forest Regressor (Best)** | **5,447.12** | **2,918.18** | **0.9389** |

The system automatically selects **Random Forest** (lowest RMSE), retrains it on the full historical dataset, and serializes it to `models/best_model.joblib`.

---

## 🛠️ Local Installation

### 1. Clone the Repository & Setup Directory
```bash
git clone https://github.com/your-username/inventory-demand-forecasting.git
cd inventory-demand-forecasting
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Fetch Data & Build Pipelines
Run the automated script to download files from Kaggle, preprocess features, train the models, and seed the local database:
```bash
# Downloads and Merges CSV files
python models/preprocessor.py

# Trains and selects the best model
python models/train.py

# Initializes SQLite Database and seeds 420k+ sales records
python -m database.seed_data
```

### 4. Run the Streamlit Application
```bash
streamlit run app.py
```

---

## 🗄️ Database Configuration

### SQLite (Default Setup)
The application will automatically initialize a local SQLite file `database/inventory_forecast.db` out of the box if no MySQL configurations are found.

### MySQL (Production Setup)
For live deployment, configure MySQL details. Add the following environment variables (or specify them in a `.env` file):
```env
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=your_username
MYSQL_PASSWORD=your_password
MYSQL_DB=inventory_forecast_db
```
Expose `database/schema.sql` to your MySQL instance to pre-create tables.

---

## 🌐 Deployment to Vercel

1.  Push the repository to GitHub.
2.  Log in to [Vercel](https://vercel.com).
3.  Import the repository: `inventory-demand-forecasting-platform`.
4.  Leave all settings as default, as the project serves static web assets directly from the repository root.
5.  Click **Deploy**. Vercel will host the Single-Page Application (SPA) instantly.

