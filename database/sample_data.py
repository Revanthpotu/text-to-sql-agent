"""Generate a sample SQLite e-commerce database for testing.

Run directly:
    python database/sample_data.py

Creates ``sample_ecommerce.db`` in the project root with realistic data
across four tables: customers, products, orders, and order_items.
"""

from __future__ import annotations

import random
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "sample_ecommerce.db"

# ---------------------------------------------------------------------------
# Seed data
# ---------------------------------------------------------------------------

FIRST_NAMES = [
    "Alice", "Bob", "Carol", "David", "Eve", "Frank", "Grace", "Hank",
    "Ivy", "Jack", "Karen", "Leo", "Mia", "Nick", "Olivia", "Paul",
    "Quinn", "Rita", "Sam", "Tina", "Uma", "Vince", "Wendy", "Xander",
    "Yara", "Zane", "Nora", "Oscar", "Piper", "Reed", "Sofia", "Tyler",
    "Ursula", "Victor", "Willa", "Xena", "Yale", "Zara", "Amber", "Blake",
    "Cora", "Derek", "Elena", "Felix", "Gina", "Hugo", "Iris", "Joel",
    "Kira", "Liam",
]

LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller",
    "Davis", "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez",
    "Wilson", "Anderson", "Thomas", "Taylor", "Moore", "Jackson", "Martin",
    "Lee", "Perez", "Thompson", "White", "Harris", "Sanchez", "Clark",
    "Ramirez", "Lewis", "Robinson",
]

CITIES = [
    "New York", "Los Angeles", "Chicago", "Houston", "Phoenix",
    "Philadelphia", "San Antonio", "San Diego", "Dallas", "Austin",
    "Portland", "Denver", "Seattle", "Boston", "Miami",
]

PRODUCTS = [
    ("Wireless Mouse", "Electronics", 29.99),
    ("Mechanical Keyboard", "Electronics", 89.99),
    ("USB-C Hub", "Electronics", 45.99),
    ("27\" Monitor", "Electronics", 349.99),
    ("Webcam HD", "Electronics", 69.99),
    ("Noise-Cancelling Headphones", "Electronics", 199.99),
    ("Laptop Stand", "Accessories", 39.99),
    ("Desk Lamp", "Accessories", 24.99),
    ("Mouse Pad XL", "Accessories", 14.99),
    ("Cable Management Kit", "Accessories", 19.99),
    ("Ergonomic Chair", "Furniture", 499.99),
    ("Standing Desk", "Furniture", 599.99),
    ("Monitor Arm", "Furniture", 79.99),
    ("Footrest", "Furniture", 34.99),
    ("Bookshelf", "Furniture", 149.99),
    ("Python Crash Course", "Books", 35.99),
    ("Clean Code", "Books", 40.99),
    ("Designing Data-Intensive Apps", "Books", 45.99),
    ("The Pragmatic Programmer", "Books", 49.99),
    ("SQL Pocket Guide", "Books", 19.99),
    ("Notebook A5", "Stationery", 8.99),
    ("Gel Pen Set (10)", "Stationery", 12.99),
    ("Sticky Notes Pack", "Stationery", 6.99),
    ("Whiteboard Markers", "Stationery", 9.99),
    ("Planner 2025", "Stationery", 18.99),
]

ORDER_STATUSES = ["completed", "processing", "shipped", "cancelled", "refunded"]


def create_database(db_path: Path = DB_PATH) -> None:
    """Create the sample database at *db_path*.

    Drops existing tables and regenerates all data so the function is
    idempotent.

    Args:
        db_path: File path for the SQLite database.
    """
    random.seed(42)

    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()

    # ------------------------------------------------------------------
    # Schema
    # ------------------------------------------------------------------
    cur.executescript(
        """
        DROP TABLE IF EXISTS order_items;
        DROP TABLE IF EXISTS orders;
        DROP TABLE IF EXISTS products;
        DROP TABLE IF EXISTS customers;

        CREATE TABLE customers (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT    NOT NULL,
            email       TEXT    NOT NULL UNIQUE,
            city        TEXT    NOT NULL,
            created_at  TEXT    NOT NULL
        );

        CREATE TABLE products (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            name            TEXT    NOT NULL,
            category        TEXT    NOT NULL,
            price           REAL    NOT NULL,
            stock_quantity  INTEGER NOT NULL
        );

        CREATE TABLE orders (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id  INTEGER NOT NULL REFERENCES customers(id),
            total_amount REAL    NOT NULL,
            status       TEXT    NOT NULL,
            created_at   TEXT    NOT NULL
        );

        CREATE TABLE order_items (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id    INTEGER NOT NULL REFERENCES orders(id),
            product_id  INTEGER NOT NULL REFERENCES products(id),
            quantity    INTEGER NOT NULL,
            unit_price  REAL    NOT NULL
        );
        """
    )

    # ------------------------------------------------------------------
    # Customers  (50)
    # ------------------------------------------------------------------
    base_date = datetime(2023, 1, 1)
    customers: list[tuple[str, str, str, str]] = []
    used_emails: set[str] = set()
    for i in range(50):
        first = random.choice(FIRST_NAMES)
        last = random.choice(LAST_NAMES)
        name = f"{first} {last}"
        email_base = f"{first.lower()}.{last.lower()}"
        email = f"{email_base}@example.com"
        # ensure unique
        while email in used_emails:
            email = f"{email_base}{random.randint(1, 999)}@example.com"
        used_emails.add(email)
        city = random.choice(CITIES)
        created = (base_date + timedelta(days=random.randint(0, 700))).isoformat()
        customers.append((name, email, city, created))
    cur.executemany(
        "INSERT INTO customers (name, email, city, created_at) VALUES (?, ?, ?, ?)",
        customers,
    )

    # ------------------------------------------------------------------
    # Products  (25)
    # ------------------------------------------------------------------
    products_rows: list[tuple[str, str, float, int]] = []
    for pname, cat, price in PRODUCTS:
        stock = random.randint(5, 200)
        products_rows.append((pname, cat, price, stock))
    cur.executemany(
        "INSERT INTO products (name, category, price, stock_quantity) VALUES (?, ?, ?, ?)",
        products_rows,
    )

    # ------------------------------------------------------------------
    # Orders + Order Items  (~80 orders, 1-4 items each)
    # ------------------------------------------------------------------
    order_id = 0
    for _ in range(80):
        customer_id = random.randint(1, 50)
        status = random.choices(
            ORDER_STATUSES, weights=[50, 15, 20, 10, 5], k=1
        )[0]
        order_date = (base_date + timedelta(days=random.randint(30, 730))).isoformat()

        num_items = random.randint(1, 4)
        item_product_ids = random.sample(range(1, len(PRODUCTS) + 1), num_items)

        total = 0.0
        items: list[tuple[int, int, int, float]] = []
        for pid in item_product_ids:
            qty = random.randint(1, 3)
            unit_price = PRODUCTS[pid - 1][2]
            total += qty * unit_price
            items.append((0, pid, qty, unit_price))  # order_id placeholder

        total = round(total, 2)
        cur.execute(
            "INSERT INTO orders (customer_id, total_amount, status, created_at) "
            "VALUES (?, ?, ?, ?)",
            (customer_id, total, status, order_date),
        )
        order_id = cur.lastrowid
        for _, pid, qty, up in items:
            cur.execute(
                "INSERT INTO order_items (order_id, product_id, quantity, unit_price) "
                "VALUES (?, ?, ?, ?)",
                (order_id, pid, qty, up),
            )

    conn.commit()
    conn.close()

    print(f"Sample database created at {db_path}")
    print(f"  - 50 customers")
    print(f"  - {len(PRODUCTS)} products")
    print(f"  - 80 orders with items")


if __name__ == "__main__":
    create_database()
