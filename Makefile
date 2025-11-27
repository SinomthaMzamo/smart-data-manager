# -------------------------------
# DATA PIPELINE MAKEFILE
# -------------------------------
 
# Default target: run everything
all: seed foundation specialised
 
# 1. Seed the data
seed:
    python -m smart_data_manager_package.seed
 
# 2. Run foundational ETL pipeline
foundation:
    python -m smart_data_manager_package.run_etl_pipeline
 
# 3. Run all specialised pipelines
specialised: daily_sales 
 
daily_sales:
    python -m smart_data_manager_package.powerBI.daily_sales_etl
 
 
# Utility target: install dependencies
install:
    pip install -r requirements.txt
 
# Clean __pycache__ and build artifacts
clean:
    find . -type d -name "__pycache__" -exec rm -r {} +
 
 
