import random
from datetime import datetime, timedelta
from faker import Faker
from sqlalchemy import create_engine, text

fake = Faker()

# Adjust connection string: mysql+pymysql://<user>:<password>@<host>:<port>/<db>
DB_URL = "mysql+pymysql://root:@127.0.0.1:3306/ecommerce_oltp"
engine = create_engine(DB_URL)

CATEGORIES = {
    'Electronics': (40.0, 300.0),
    'Apparel': (10.0, 80.0),
    'Home & Kitchen': (15.0, 120.0),
    'Outdoor & Gear': (25.0, 200.0)
}
CHANNELS = ['Organic Search', 'Paid Ads', 'Instagram', 'Direct', 'Referral']
STATUSES = ['Completed', 'Completed', 'Completed', 'Completed', 'Returned', 'Cancelled']

def seed():
    with engine.begin() as conn:
        print("1. Seeding Products...")
        products = []
        for i in range(1, 61):
            cat = random.choice(list(CATEGORIES.keys()))
            cost_range = CATEGORIES[cat]
            base_cost = round(random.uniform(*cost_range), 2)
            retail_price = round(base_cost * random.uniform(1.3, 1.8), 2)
            products.append({
                'sku': f"SKU-{cat[:3].upper()}-{i:04d}",
                'product_name': f"{fake.word().capitalize()} {fake.word().capitalize()}",
                'category': cat,
                'base_cost': base_cost,
                'retail_price': retail_price
            })
            conn.execute(
                text("""
                    INSERT INTO products (sku, product_name, category, base_cost, retail_price)
                    VALUES (:sku, :product_name, :category, :base_cost, :retail_price)
                """), products[-1]
            )

        print("2. Seeding Customers...")
        start_date = datetime(2025, 1, 1)
        customers = []
        for _ in range(500):
            created_at = fake.date_time_between(start_date=start_date, end_date='now')
            res = conn.execute(
                text("""
                    INSERT INTO customers (first_name, last_name, email, city, acquisition_channel, created_at)
                    VALUES (:first_name, :last_name, :email, :city, :channel, :created_at)
                """),
                {
                    'first_name': fake.first_name(),
                    'last_name': fake.last_name(),
                    'email': fake.unique.email(),
                    'city': fake.city(),
                    'channel': random.choice(CHANNELS),
                    'created_at': created_at
                }
            )
            customers.append({'id': res.lastrowid, 'created_at': created_at})

        print("3. Seeding Orders and Order Items...")
        for _ in range(2500):
            customer = random.choice(customers)
            order_date = fake.date_time_between(start_date=customer['created_at'], end_date='now')
            status = random.choice(STATUSES)
            discount = round(random.choice([0, 0, 0, 5, 10, 15]), 2)
            shipping = round(random.choice([0, 5.99, 9.99]), 2)

            res = conn.execute(
                text("""
                    INSERT INTO orders (customer_id, order_date, order_status, discount_amount, shipping_fee)
                    VALUES (:customer_id, :order_date, :order_status, :discount_amount, :shipping_fee)
                """),
                {
                    'customer_id': customer['id'],
                    'order_date': order_date,
                    'order_status': status,
                    'discount_amount': discount,
                    'shipping_fee': shipping
                }
            )
            order_id = res.lastrowid

            # 1 to 4 items per order
            num_items = random.choices([1, 2, 3, 4], weights=[0.5, 0.3, 0.15, 0.05])[0]
            selected_products = random.sample(range(1, 61), num_items)

            for prod_id in selected_products:
                prod = products[prod_id - 1]
                qty = random.choices([1, 2, 3], weights=[0.75, 0.2, 0.05])[0]
                conn.execute(
                    text("""
                        INSERT INTO order_items (order_id, product_id, quantity, unit_price, unit_cost)
                        VALUES (:order_id, :product_id, :quantity, :unit_price, :unit_cost)
                    """),
                    {
                        'order_id': order_id,
                        'product_id': prod_id,
                        'quantity': qty,
                        'unit_price': prod['retail_price'],
                        'unit_cost': prod['base_cost']
                    }
                )

        print("4. Seeding Initial Inventory Logs...")
        for prod_id in range(1, 61):
            prod = products[prod_id - 1]
            conn.execute(
                text("""
                    INSERT INTO inventory_logs (product_id, change_type, quantity_changed, unit_cost_at_change, logged_at)
                    VALUES (:product_id, 'Restock', :qty, :cost, :logged_at)
                """),
                {
                    'product_id': prod_id,
                    'qty': random.randint(50, 200),
                    'cost': prod['base_cost'],
                    'logged_at': start_date
                }
            )

    print("Phase 1 seeding completed successfully.")

if __name__ == '__main__':
    seed()