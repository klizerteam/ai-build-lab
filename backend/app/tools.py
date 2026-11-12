"""
tools.py  <-- YOU write the missing parts of this file during the workshop.

THE FUNCTIONS: the Python code that does the real work (reads the database,
does the maths). Only our backend runs these. The model never sees this file.

Every tool has three parts, each in its own file:

    1. tools.py          the FUNCTION      what our backend runs     <- this file
    2. tool_schemas.py   the SCHEMA        what the model reads
    3. tool_registry.py  the REGISTRATION  connects 1 and 2

HOW IT WORKS
Each step has a starting outline. Comments marked  TASK 3A, TASK 3B, ...  say
what code to write there, and  return ...  is a placeholder to replace.
Search for "TASK 3" (then "TASK 4", "TASK 5"). Save, then run
python check.py <step>  to see what's still missing.
"""
from app.database import get_connection


# ----------------------------------------------------------------------
# STEP 3: search_products
# ----------------------------------------------------------------------

def search_products(query: str = "", category: str = "", max_price: float | None = None) -> dict:
    """Find products in the catalog. Every filter is optional."""
    sql = "SELECT id, name, category, price, rating, stock FROM products WHERE 1=1"
    params = []

    # Keyword filter (written for you, as an example): every word must appear
    # in the product's name, description or tags. Each ? is filled from params.
    for word in (query or "").lower().split():
        sql += " AND (LOWER(name) LIKE ? OR LOWER(description) LIKE ? OR LOWER(tags) LIKE ?)"
        params += [f"%{word}%"] * 3

    # TASK 3A: category filter. Only if a category was given.

    # TASK 3B: price filter. Only if max_price was given.

    sql += " ORDER BY price ASC LIMIT 5"  # cheapest first, at most 5 results

    with get_connection() as conn:
        rows = conn.execute(sql, params).fetchall()

    # TASK 3C: build a list called products, with one dict per row.

    # TASK 3D: return the result (and handle "nothing found").
    return ...


# ----------------------------------------------------------------------
# STEP 4: check_order
# ----------------------------------------------------------------------

def check_order(order_id: str) -> dict:
    """Look up one order by its ID, e.g. ORD1024."""
    # TASK 4A: tidy up order_id, so " ord1024 " becomes "ORD1024".

    with get_connection() as conn:
        row = conn.execute(
            "SELECT order_id, order_date, items, total, status, estimated_delivery "
            "FROM orders WHERE order_id = ?",
            (order_id,),
        ).fetchone()

    # TASK 4B: no such order (row is None)? Say so clearly.

    # TASK 4C: return the order's details.
    return ...


# ----------------------------------------------------------------------
# STEP 5: calculate_discount
# ----------------------------------------------------------------------

def calculate_discount(price: float, discount_percent: float) -> dict:
    """Apply a percentage discount to a price."""
    # TASK 5A: make sure both inputs are numbers.
    # TASK 5B: refuse inputs that make no sense.
    # TASK 5C: work out the discount and the final price.
    # TASK 5D: return the result.
    return ...
