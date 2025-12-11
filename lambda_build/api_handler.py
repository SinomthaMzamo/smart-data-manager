import json
from datetime import datetime, date
from sqlalchemy import text
from rds_db import get_engine
import os

# ------------------------
# Configuration
# ------------------------
engine = get_engine()
POWERAPPS_KEY = os.environ.get("POWERAPPS_API_KEY")
POWERBI_KEY = os.environ.get("POWERBI_API_KEY")

# ------------------------
# JSON Serializer
# ------------------------
class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        return super().default(obj)

# ------------------------
# Auth Helper
# ------------------------
def check_api_key(headers, read_only=False):
    key = headers.get("x-api-key")
    if read_only:
        return key in [POWERBI_KEY, POWERAPPS_KEY]
    return key == POWERAPPS_KEY

def forbidden_response():
    return {"statusCode": 403, "body": json.dumps({"error": "Forbidden"})}

# ------------------------
# Response Builder
# ------------------------
def json_response(status_code, data):
    return {
        "statusCode": status_code,
        "body": json.dumps(data, cls=DateTimeEncoder)
    }

# ------------------------
# Generic CRUD Operations
# ------------------------
class CRUDResource:
    def __init__(self, table_name, id_field, fields):
        self.table_name = table_name
        self.id_field = id_field
        self.fields = fields
    
    def get(self, resource_id=None):
        with engine.connect() as conn:
            if resource_id:
                query = text(f'SELECT * FROM "{self.table_name}" WHERE {self.id_field}=:id AND deleted_at IS NULL')
                result = conn.execute(query, {"id": resource_id}).mappings().fetchone()
                return json_response(200, dict(result) if result else {})
            else:
                query = text(f'SELECT * FROM "{self.table_name}" WHERE deleted_at IS NULL')
                result = conn.execute(query).mappings().fetchall()
                return json_response(200, [dict(r) for r in result])
    
    def create(self, body):
        with engine.connect() as conn:
            fields_str = ",".join(self.fields)
            values_str = ",".join([f":{f}" for f in self.fields])
            query = text(f'INSERT INTO "{self.table_name}"({fields_str}) VALUES ({values_str}) RETURNING {self.id_field}')
            result = conn.execute(query, body)
            conn.commit()
            return json_response(201, {self.id_field: result.scalar()})
    
    def update(self, resource_id, body):
        if not resource_id:
            return json_response(400, {"error": f"Missing {self.id_field}"})
        with engine.connect() as conn:
            set_clause = ",".join([f"{f}=:{f}" for f in self.fields])
            query = text(f'UPDATE "{self.table_name}" SET {set_clause} WHERE {self.id_field}=:id AND deleted_at IS NULL')
            conn.execute(query, {**body, "id": resource_id})
            conn.commit()
            return json_response(200, {"message": f"{self.table_name} updated"})
    
    def delete(self, resource_id):
        if not resource_id:
            return json_response(400, {"error": f"Missing {self.id_field}"})
        with engine.connect() as conn:
            query = text(f'UPDATE "{self.table_name}" SET deleted_at=NOW() WHERE {self.id_field}=:id')
            conn.execute(query, {"id": resource_id})
            conn.commit()
            return json_response(200, {"message": f"{self.table_name} soft-deleted"})

# ------------------------
# Resource Definitions
# ------------------------
RESOURCES = {
    "customers": CRUDResource(
        "Customers",
        "customer_id",
        ["first_name", "last_name", "email", "phone"]
    ),
    "products": CRUDResource(
        "Products",
        "product_id",
        ["product_name", "description", "price", "stock_quantity", "category"]
    ),
    "orders": CRUDResource(
        "Orders",
        "order_id",
        ["customer_id", "order_date", "status", "total_amount"]
    ),
    "order-items": CRUDResource(
        "OrderItems",
        "order_item_id",
        ["order_id", "product_id", "quantity", "price"]
    )
}

# ------------------------
# Special Handlers
# ------------------------
def create_order_with_items(body):
    with engine.begin() as conn:
        total_amount = sum(i["quantity"] * i["price"] for i in body.get("items", []))
        query_order = text(
            'INSERT INTO "Orders"(customer_id,order_date,status,total_amount) '
            'VALUES (:customer_id,:order_date,:status,:total_amount) RETURNING order_id'
        )
        result = conn.execute(query_order, {
            "customer_id": body["customer_id"],
            "order_date": body.get("order_date"),
            "status": body.get("status", "Pending"),
            "total_amount": total_amount
        })
        order_id = result.scalar()
        
        for item in body.get("items", []):
            query_item = text(
                'INSERT INTO "OrderItems"(order_id,product_id,quantity,price) '
                'VALUES (:order_id,:product_id,:quantity,:price)'
            )
            conn.execute(query_item, {**item, "order_id": order_id})
        
        return json_response(201, {"order_id": order_id})

def get_daily_summary(summary_date=None):
    if not summary_date:
        summary_date = date.today().isoformat()
    with engine.connect() as conn:
        query = text('SELECT * FROM "DailySalesSummary" WHERE summary_date=:d')
        result = conn.execute(query, {"d": summary_date}).mappings().fetchone()
        return json_response(200, dict(result) if result else {})

def get_summary_range(range_param="today"):
    range_queries = {
        "today": 'SELECT * FROM "DailySalesSummary" WHERE summary_date=CURRENT_DATE',
        "week": 'SELECT * FROM "DailySalesSummary" WHERE summary_date >= CURRENT_DATE - INTERVAL \'7 days\'',
        "month": 'SELECT * FROM "DailySalesSummary" WHERE summary_date >= CURRENT_DATE - INTERVAL \'30 days\''
    }
    
    if range_param not in range_queries:
        return json_response(400, {"error": "Invalid range parameter"})
    
    with engine.connect() as conn:
        query = text(range_queries[range_param])
        result = conn.execute(query).mappings().fetchall()
        return json_response(200, [dict(r) for r in result])

# ------------------------
# Route Handler
# ------------------------
def update_order_with_items(order_id, body):
    """Update order and optionally replace all order items"""
    with engine.begin() as conn:
        # Update the order itself
        order_fields = ["customer_id", "order_date", "status", "total_amount"]
        order_data = {k: v for k, v in body.items() if k in order_fields}
        
        if order_data:
            set_clause = ",".join([f"{f}=:{f}" for f in order_data.keys()])
            query = text(f'UPDATE "Orders" SET {set_clause} WHERE order_id=:id AND deleted_at IS NULL')
            conn.execute(query, {**order_data, "id": order_id})
        
        # If items are provided, delete old items and insert new ones
        if "items" in body:
            # Soft delete existing items
            delete_query = text('UPDATE "OrderItems" SET deleted_at=NOW() WHERE order_id=:oid AND deleted_at IS NULL')
            conn.execute(delete_query, {"oid": order_id})
            
            # Insert new items
            for item in body["items"]:
                insert_query = text(
                    'INSERT INTO "OrderItems"(order_id,product_id,quantity,price) '
                    'VALUES (:order_id,:product_id,:quantity,:price)'
                )
                conn.execute(insert_query, {**item, "order_id": order_id})
            
            # Recalculate total_amount if items were updated
            total_amount = sum(i["quantity"] * i["price"] for i in body["items"])
            update_total = text('UPDATE "Orders" SET total_amount=:total WHERE order_id=:oid')
            conn.execute(update_total, {"total": total_amount, "oid": order_id})
        
        return json_response(200, {"message": "Order updated", "order_id": order_id})

def handle_crud_resource(resource_name, method, resource_id, body):
    resource = RESOURCES.get(resource_name.lower())
    if not resource:
        return None
    
    if method == "GET":
        return resource.get(resource_id)
    elif method == "POST":
        # Special case for orders with nested items
        if resource_name.lower() == "orders" and body.get("items"):
            return create_order_with_items(body)
        return resource.create(body)
    elif method in ["PUT", "PATCH"]:
        # Special case for orders with nested items
        if resource_name.lower() == "orders" and body.get("items"):
            return update_order_with_items(resource_id, body)
        return resource.update(resource_id, body)
    elif method == "DELETE":
        return resource.delete(resource_id)
    
    return json_response(405, {"error": "Method not allowed"})

def handle_dashboard(path_parts, query_params):
    if len(path_parts) < 2:
        return json_response(400, {"error": "Missing dashboard endpoint"})
    
    endpoint = path_parts[1].lower()
    
    if endpoint == "daily-summary":
        summary_date = query_params.get("date")
        return get_daily_summary(summary_date)
    elif endpoint == "summary":
        range_param = query_params.get("range", "today")
        return get_summary_range(range_param)
    
    return json_response(404, {"error": "Unknown dashboard endpoint"})

# ------------------------
# Main Lambda Handler
# ------------------------
def lambda_handler(event, context):
    path = event.get("path", "")
    method = event.get("httpMethod", "")
    headers = event.get("headers") or {}
    path_parts = path.strip("/").split("/")
    
    try:
        resource_name = path_parts[0].lower()
        resource_id = path_parts[1] if len(path_parts) > 1 else None
        body = json.loads(event.get("body") or "{}") if method in ["POST", "PUT", "PATCH"] else {}
        query_params = event.get("queryStringParameters") or {}
        
        # Handle dashboard/analytics (read-only)
        if resource_name == "dashboard":
            if not check_api_key(headers, read_only=True):
                return forbidden_response()
            return handle_dashboard(path_parts, query_params)
        
        # Handle CRUD resources
        if resource_name in RESOURCES:
            if not check_api_key(headers):
                return forbidden_response()
            return handle_crud_resource(resource_name, method, resource_id, body)
        
        return json_response(404, {"error": f"Unknown path {path}"})
    
    except Exception as e:
        return json_response(500, {"error": str(e)})
    

    