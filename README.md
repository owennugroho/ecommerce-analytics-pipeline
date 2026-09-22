# End-to-End E-Commerce & Retail Analytics Pipeline

A full-stack data pipeline bridging transactional database design (OLTP) and analytical dimensional modeling (OLAP / Star Schema).

## Architecture
- **Source Database (OLTP):** MySQL (Normalized 3NF transactional retail schema)
- **Synthetic Data Engine:** Python (SQLAlchemy, Faker) simulating 2,500+ orders, inventory batches, and customer lifecycles
- **Data Warehouse (OLAP):** MySQL / Dimensional Star Schema (`dim_customers`, `dim_products`, `dim_date`, `fact_order_items`)
- **Transformation / ETL:** Python & Advanced SQL (Metric calculations, landed margin, discount allocations)
- **Presentation:** Executive BI Dashboards (Power BI / Metabase)

## Setup & Reproduction
1. Clone repository:
   ```bash
   git clone <your-repo-url>
   cd ecommerce-analytics-pipeline