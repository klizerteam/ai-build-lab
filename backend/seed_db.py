"""
Rebuild data/shop.db from data/products.csv and data/orders.csv.

    python seed_db.py

Run this after editing the CSV files. (The app also creates the database
automatically on first start if it does not exist.)
"""
from app.database import get_connection, seed_database

seed_database()

with get_connection() as conn:
    products = conn.execute("SELECT COUNT(*) FROM products").fetchone()[0]
    orders = conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0]

print(f"Database ready: {products} products, {orders} orders -> data/shop.db")
