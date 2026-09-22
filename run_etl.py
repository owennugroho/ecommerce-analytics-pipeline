import pandas as pd
from datetime import datetime, timedelta
from sqlalchemy import create_engine, text

OLTP_URL = "mysql+pymysql://root:@127.0.0.1:3306/ecommerce_oltp"
DW_URL = "mysql+pymysql://root:@127.0.0.1:3306/ecommerce_dw"

oltp_engine = create_engine(OLTP_URL)
dw_engine = create_engine(DW_URL)

def populate_dim_date(start_date="2024-01-01", days=1000):
    print("1. Populating dim_date...")
    base = datetime.strptime(start_date, "%Y-%m-%d")
    date_records = []
    
    for x in range(days):
        dt = base + timedelta(days=x)
        date_records.append({
            "date_key": int(dt.strftime("%Y%m%d")),
            "full_date": dt.date(),
            "year": dt.year,
            "quarter": (dt.month - 1) // 3 + 1,
            "month": dt.month,
            "month_name": dt.strftime("%B"),
            "day": dt.day,
            "day_name": dt.strftime("%A"),
            "is_weekend": dt.weekday() >= 5
        })
    
    df_date = pd.DataFrame(date_records)
    with dw_engine.begin() as conn:
        conn.execute(text("TRUNCATE TABLE fact_order_items;"))
        conn.execute(text("DELETE FROM dim_date;"))
        df_date.to_sql("dim_date", con=conn, if_exists="append", index=False)

def sync_dimensions():
    print("2. Syncing dim_customers and dim_products...")
    
    # Sync Customers
    with oltp_engine.connect() as conn:
        df_cust = pd.read_sql(text("""
            SELECT 
                customer_id,
                CONCAT(first_name, ' ', last_name) AS full_name,
                city,
                acquisition_channel,
                DATE(created_at) AS signup_date
            FROM customers
        """), conn)

    with dw_engine.begin() as conn:
        conn.execute(text("DELETE FROM dim_customers;"))
        df_cust.to_sql("dim_customers", con=conn, if_exists="append", index=False)

    # Sync Products
    with oltp_engine.connect() as conn:
        df_prod = pd.read_sql(text("""
            SELECT product_id, sku, product_name, category, base_cost, retail_price 
            FROM products
        """), conn)

    with dw_engine.begin() as conn:
        conn.execute(text("DELETE FROM dim_products;"))
        df_prod.to_sql("dim_products", con=conn, if_exists="append", index=False)

def transform_and_load_facts():
    print("3. Transforming & loading fact_order_items...")
    
    # Query raw data without MySQL string formatting (% conflicts)
    raw_query = text("""
        SELECT 
            o.order_id,
            o.order_date,
            o.customer_id,
            oi.product_id,
            o.order_status,
            oi.quantity,
            oi.unit_price,
            oi.unit_cost,
            o.discount_amount,
            o.shipping_fee,
            COUNT(*) OVER (PARTITION BY o.order_id) AS line_item_count
        FROM orders o
        JOIN order_items oi ON o.order_id = oi.order_id
    """)
    
    with oltp_engine.connect() as conn:
        df = pd.read_sql(raw_query, conn)

    # Convert order_date to integer YYYYMMDD date_key in Pandas
    df["order_date"] = pd.to_datetime(df["order_date"])
    df["date_key"] = df["order_date"].dt.strftime("%Y%m%d").astype(int)

    # Fetch surrogate keys from warehouse dimensions
    with dw_engine.connect() as conn:
        cust_dim = pd.read_sql(text("SELECT customer_key, customer_id FROM dim_customers"), conn)
        prod_dim = pd.read_sql(text("SELECT product_key, product_id FROM dim_products"), conn)

    df = df.merge(cust_dim, on="customer_id", how="left")
    df = df.merge(prod_dim, on="product_id", how="left")

    # Financial metric calculations
    df["gross_revenue"] = (df["quantity"] * df["unit_price"]).round(2)
    df["cogs"] = (df["quantity"] * df["unit_cost"]).round(2)
    df["gross_profit"] = (df["gross_revenue"] - df["cogs"]).round(2)
    
    # Prorate order-level discount and shipping across line items
    df["allocated_discount"] = (df["discount_amount"] / df["line_item_count"]).round(2)
    df["allocated_shipping"] = (df["shipping_fee"] / df["line_item_count"]).round(2)
    df["net_revenue"] = (df["gross_revenue"] - df["allocated_discount"]).round(2)
    df["net_profit"] = (df["net_revenue"] - df["cogs"]).round(2)

    fact_cols = [
        "order_id", "date_key", "customer_key", "product_key", "order_status",
        "quantity", "unit_price", "unit_cost", "gross_revenue", "cogs",
        "gross_profit", "allocated_discount", "allocated_shipping", "net_revenue", "net_profit"
    ]
    df_fact = df[fact_cols]

    with dw_engine.begin() as conn:
        conn.execute(text("TRUNCATE TABLE fact_order_items;"))
        df_fact.to_sql("fact_order_items", con=conn, if_exists="append", index=False)
    
    print(f"ETL completed: {len(df_fact)} records loaded into fact_order_items.")

if __name__ == "__main__":
    populate_dim_date()
    sync_dimensions()
    transform_and_load_facts()