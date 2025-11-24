# smart-data-manager

TODO

- Create ETL tickets

## 📦 Project Dependencies
 
This project uses several Python libraries to support ETL workflows, data cleaning, reporting, and automated analytics. Below is a summary of each dependency and its role in the Smart Data Manager system.
 
### **1. pandas**
Used for data extraction, transformation, and cleaning.  
Provides DataFrame structures and powerful functions for manipulating customer, order, and product datasets.
 
### **2. SQLAlchemy**
A Python ORM & database toolkit used to connect to Azure SQL Database.  
Handles querying, inserts, updates, and writing transformed data back to SQL.
 
### **3. python-dotenv**
Loads environment variables from a `.env` file.  
Prevents exposing database credentials in code and keeps secrets out of GitHub.
 
### **4. openpyxl**
Used for generating Excel-based reports (e.g., monthly BI report).  
Enables writing multi-sheet, formatted reporting files.
 
### **5. matplotlib**
Creates charts and visualizations for automated reports.  
Used in daily sales reports, product performance graphs, and monthly summaries.
 
### **6. seaborn**
Built on top of matplotlib.  
Provides visually appealing statistical graphics for trends and analytics.
 
### **7. jinja2** _(optional)_
A templating engine used to generate AI-ready summaries or structured report templates.  
Useful for creating consistent text-based reports (HTML, Markdown, TXT).

Here is the **Installation Requirements** section in **raw Markdown**, ready to paste into your README:

---

## 🔧 Installation & Setup

Follow the steps below to set up the Python environment for the Smart Data Manager ETL pipeline.

### **Prerequisites**
Before you begin, ensure the following are installed on your system:

- **Python 3.10+**  
  Download from: https://www.python.org/downloads/

- **pip** (comes with Python)
- **Access to the Azure SQL Database** (connection details)

---

## 🐍 1. Create and Activate a Virtual Environment

Navigate to the project folder:

```bash
cd smart-data-manager
````

Create the virtual environment:

```bash
python -m venv venv
```

Activate the environment:

### **Windows**

```bash
venv\Scripts\activate
```

### **macOS / Linux**

```bash
source venv/bin/activate
```

---

## 📦 2. Install Dependencies

Ensure you are inside the activated virtual environment, then run:

```bash
pip install -r requirements.txt
```

This installs all required packages for:

* Database connectivity
* ETL pipeline (extract, transform, load)
* Reporting and visualizations
* Environment variable management

---


## ETL Pipeline Overview

The project implements a full ETL (Extract, Transform, Load) pipeline to process sales data from SQL Server into an analytics-ready star schema. This pipeline is designed to support dashboards, reporting, and business intelligence in Power BI.

### 1. Extraction

* **File:** `extract.py`
* **Description:** Connects to the SQL Server database using `db.py` and extracts the following tables into pandas DataFrames:

  * `Customers`
  * `Products`
  * `Orders`
  * `OrderItems`
* **Features:**

  * Handles connection errors and empty tables.
  * Prints a preview of extracted data for verification.

### 2. Cleaning

* **File:** `clean.py`
* **Description:** Cleans and normalizes raw data before transformation.
* **Key Steps:**

  * Removes duplicates.
  * Normalizes text (emails, names).
  * Handles nulls and invalid values (e.g., negative prices or quantities).
  * Adds derived fields:

    * `full_name` in `Customers`
    * `full_description` in `Products`
    * `line_total` in `OrderItems`
  * Logs detailed cleaning operations both to console and `transform.log`.

### 3. Transformation

* **File:** `transform.py`
* **Description:** Reshapes cleaned data into analytics-ready tables following a star schema:

  * **Dimensions**

    * `DimCustomers`: Customer details.
    * `DimProducts`: Product details.
    * `DimDate`: Date dimension created from `Orders.order_date`.
  * **Facts**

    * `FactOrders`: Order-level metrics.
    * `FactOrderItems`: Item-level metrics (quantities, line totals).
* **Features:**

  * Wraps cleaning functions for end-to-end processing.
  * Generates additional keys (`date_key`) and derived columns.
  * Returns a dictionary of transformed DataFrames ready for loading.

### 4. Loading

* **File:** `load.py`
* **Description:** Loads transformed tables into SQL Server in proper dependency order:

  1. Dimensions first (`DimCustomers`, `DimProducts`, `DimDate`)
  2. Facts next (`FactOrders`, `FactOrderItems`)
* **Features:**

  * Supports `replace` or `append` modes.
  * Logs success and errors to both console and `load.log`.

### 5. Running the Pipeline

* **File:** `run_etl_pipeline.py`
* **Description:** Orchestrates the ETL flow end-to-end:

  1. Extract raw data from SQL Server.
  2. Clean and transform the data.
  3. Build dimensions and facts.
  4. Load the processed tables into SQL Server for Power BI consumption.

**Usage Example:**

```bash
python run_etl_pipeline.py
```

---
