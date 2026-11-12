"""
database.py - SQLite helpers.

The database file (data/shop.db) is built from data/products.csv and
data/orders.csv. It is created automatically the first time the app starts.
To rebuild it from the CSV files, run:  python seed_db.py
"""
import csv
import sqlite3
from contextlib import contextmanager

from app.config import DATA_DIR, DB_PATH


@contextmanager
def get_connection():
    """Open the database, give it to the caller, then close it.

    Usage:
        with get_connection() as conn:
            rows = conn.execute("SELECT * FROM products").fetchall()

    Each row behaves like a dict: row["name"], row["price"], ...
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def _read_csv(filename: str) -> list[dict]:
    with open(DATA_DIR / filename, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def seed_database() -> None:
    """(Re)create shop.db from the CSV files."""
    if DB_PATH.exists():
        DB_PATH.unlink()

    products = _read_csv("products.csv")
    orders = _read_csv("orders.csv")

    conn = sqlite3.connect(DB_PATH)
    try:
        conn.executescript(
            """
            CREATE TABLE products (
                id          TEXT PRIMARY KEY,
                name        TEXT NOT NULL,
                category    TEXT NOT NULL,
                brand       TEXT NOT NULL,
                price       REAL NOT NULL,
                rating      REAL NOT NULL,
                stock       INTEGER NOT NULL,
                description TEXT NOT NULL,
                tags        TEXT NOT NULL
            );
            CREATE TABLE orders (
                order_id           TEXT PRIMARY KEY,
                order_date         TEXT NOT NULL,
                items              TEXT NOT NULL,
                total              REAL NOT NULL,
                status             TEXT NOT NULL,
                estimated_delivery TEXT
            );
            """
        )
        conn.executemany(
            "INSERT INTO products VALUES (:id, :name, :category, :brand, :price,"
            " :rating, :stock, :description, :tags)",
            products,
        )
        conn.executemany(
            "INSERT INTO orders VALUES (:order_id, :order_date, :items, :total,"
            " :status, NULLIF(:estimated_delivery, ''))",
            orders,
        )
        conn.commit()
    finally:
        conn.close()


def ensure_database() -> None:
    """Create the database on first run."""
    if not DB_PATH.exists():
        seed_database()
