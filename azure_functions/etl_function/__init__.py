"""
Azure Function handler for ETL pipeline
Place this in: azure_functions/etl_function/__init__.py
"""
import azure.functions as func
import logging
import sys
import os
import datetime


# Import existing ETL code - use absolute imports
from smart_data_manager.extract import extract_table
from smart_data_manager.transform import transform_all
from smart_data_manager.load import load_transformed_schema
from smart_data_manager.daily_sales_etl import run_daily_sales_etl

def main(mytimer: func.TimerRequest) -> None:
    """
    Azure Function triggered by timer
    This runs the full ETL pipeline on a schedule
    """

    utc_timestamp = datetime.datetime.now(datetime.UTC).isoformat()

    logging.info('='*60)
    logging.info(f'ETL Function triggered at {utc_timestamp}')
    logging.info('='*60)
    
    # Log environment info for debugging
    logging.info(f"Python version: {sys.version}")
    logging.info(f"Working directory: {os.getcwd()}")
    logging.info(f"DB_SERVER present: {os.getenv('DB_SERVER') is not None}")
    
    try:
        # Run main ETL pipeline
        logging.info("Starting ETL Pipeline...")
        
        # Extract
        logging.info("Extracting data...")
        customers_df = extract_table("Customers")
        products_df = extract_table("Products")
        orders_df = extract_table("Orders")
        order_items_df = extract_table("OrderItems")
        
        if customers_df.empty:
            logging.warning("Customers table is empty")
        if products_df.empty:
            logging.warning("Products table is empty")
        if orders_df.empty:
            logging.warning("Orders table is empty")
        if order_items_df.empty:
            logging.warning("OrderItems table is empty")
        
        # Transform
        logging.info("Transforming data...")
        transformed_data = transform_all(
            customers_df, 
            products_df, 
            orders_df, 
            order_items_df
        )
        
        # Load
        logging.info("Loading data...")
        load_transformed_schema(
            dim_customers=transformed_data["dim_customers"],
            dim_products=transformed_data["dim_products"],
            dim_date=transformed_data["dim_date"],
            fact_orders=transformed_data["fact_orders"],
            fact_order_items=transformed_data["fact_order_items"],
            mode="replace"
        )
        
        # Run daily sales ETL
        logging.info("Running daily sales ETL...")
        daily_result = run_daily_sales_etl()
        
        logging.info('='*60)
        logging.info('ETL Pipeline completed successfully')
        logging.info(f'Daily sales result: {daily_result}')
        logging.info('='*60)
        
    except Exception as e:
        logging.error(f'ETL Pipeline failed: {str(e)}', exc_info=True)
        raise