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
