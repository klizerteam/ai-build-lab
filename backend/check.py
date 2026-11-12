"""
check.py - checkpoint tests for the workshop. Run from the backend folder:

    python check.py setup       Step 1: Python, packages, .env, database, Groq key
    python check.py search      Step 3: search_products
    python check.py order       Step 4: check_order
    python check.py discount    Step 5: calculate_discount
    python check.py all         Everything above

The tool checks call your Python functions directly (no AI involved), so they
show whether YOUR code is right, separately from what the model does.
"""
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

passed = 0
failed = 0


def check(description: str, condition: bool, hint: str = "") -> None:
    global passed, failed
    if condition:
        passed += 1
        print(f"  PASS  {description}")
    else:
        failed += 1
        print(f"  FAIL  {description}")
        if hint:
            print(f"        hint: {hint}")


class StopStep(Exception):
    """Raised when a tool crashes: the rest of that step's checks are skipped."""


def has_blanks(value) -> bool:
    """True if a template blank (...) is still somewhere inside value."""
    if value is Ellipsis:
        return True
    if isinstance(value, dict):
        return any(has_blanks(k) or has_blanks(v) for k, v in value.items())
    if isinstance(value, (list, tuple, set)):
        return any(has_blanks(v) for v in value)
    return False


def safe(function, name: str, step: int):
    """Wrap a tool so a crash becomes one FAIL (and stops the step), not a traceback."""
    def call(*args, **kwargs):
        try:
            result = function(*args, **kwargs)
        except Exception as e:
            check(f"{name} runs without crashing", False,
                  f"{type(e).__name__}: {e}. Look at the TASK {step} parts of app/tools.py.")
            raise StopStep
        if not isinstance(result, dict):
            check(f"{name} returns a dict", False,
                  f"it returned {result!r}. Replace  return ...  with your own return (TASK {step}).")
            raise StopStep
        return result
    call.unsafe = function
    return call


def load(module_name: str):
    """Import one of the tool files. A typo becomes a FAIL, not a crash."""
    import importlib
    try:
        return importlib.import_module(module_name)
    except Exception as e:
        path = "app/" + module_name.split(".", 1)[1].replace(".", "/") + ".py"
        check(f"{path} loads without errors", False,
              f"{type(e).__name__}: {e}. Look at the line it mentions in {path}.")
        return None


def schema_parts(schema) -> tuple[dict, dict, set]:
    """(function part, properties, required names) of a schema, or empties."""
    function = schema.get("function", {}) if isinstance(schema, dict) else {}
    parameters = function.get("parameters", {}) if isinstance(function, dict) else {}
    if not isinstance(parameters, dict):
        parameters = {}
    properties = parameters.get("properties", {})
    properties = properties if isinstance(properties, dict) else {}
    required = parameters.get("required", [])
    required = set(required) if isinstance(required, list) and not has_blanks(required) else set()
    return function, properties, required


def get_tool(name: str, step: int, schema_task: str):
    """Check the three parts of a tool. Returns (function, schema), or (None, None)."""
    package, folder = "app", "app"
    schema_name = f"{name.upper()}_SCHEMA"

    # Part 1: the function, in tools.py
    tools = load(f"{package}.tools")
    if tools is None:
        return None, None
    function = getattr(tools, name, None)
    check(f"{name} function is in {folder}/tools.py", callable(function),
          f"the {name} outline is missing: get a fresh copy of app/tools.py from the repo")

    # Part 2: the schema, in tool_schemas.py
    tool_schemas = load(f"{package}.tool_schemas")
    if tool_schemas is None:
        return None, None
    schema = getattr(tool_schemas, schema_name, None)
    check(f"{schema_name} is in {folder}/tool_schemas.py", schema is not None,
          f"the {schema_name} outline is missing: get a fresh copy of app/tool_schemas.py from the repo")
    check(f"{schema_name} has no ... left", not has_blanks(schema),
          f"{schema_task}: replace every ... in the STEP {step} part of {folder}/tool_schemas.py")

    # Part 3: the registration, in tool_registry.py
    registry = load(f"{package}.tool_registry")
    if registry is None:
        return None, None
    schema_names = [s.get("function", {}).get("name") for s in registry.TOOLS
                    if isinstance(s, dict) and isinstance(s.get("function"), dict)]
    check(f"{name} schema is in TOOLS ({folder}/tool_registry.py)", name in schema_names,
          f"add  TOOLS.append(tool_schemas.{schema_name})  in the STEP {step} part of "
          f"{folder}/tool_registry.py")
    check(f"{name} is registered in TOOL_FUNCTIONS ({folder}/tool_registry.py)",
          name in registry.TOOL_FUNCTIONS,
          f'add  TOOL_FUNCTIONS["{name}"] = tools.{name}  in the STEP {step} part of '
          f"{folder}/tool_registry.py")

    # The function is tested even before it is registered.
    return (safe(function, name, step) if callable(function) else None), schema


def check_setup() -> None:
    print("\nStep 1 - setup")
    check(f"Python version is 3.10 or newer (you have {sys.version.split()[0]})",
          sys.version_info >= (3, 10), "install Python 3.10+ from python.org")

    try:
        import dotenv, fastapi, groq, uvicorn  # noqa: F401
        check("packages installed (fastapi, uvicorn, groq, python-dotenv)", True)
    except ImportError as e:
        check("packages installed", False,
              f"{e}. Activate the venv, then run: pip install -r requirements.txt")
        return

    from app import config
    check("backend/.env file exists", (config.BACKEND_DIR / ".env").exists(),
          "copy .env.example to .env (see README step 1)")

    from app.database import ensure_database, get_connection
    ensure_database()
    with get_connection() as conn:
        products = conn.execute("SELECT COUNT(*) FROM products").fetchone()[0]
        orders = conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
    check(f"database has data ({products} products, {orders} orders)", products > 0 and orders > 0,
          "run: python seed_db.py")

    if config.LLM_PROVIDER == "mock":
        print("  NOTE  LLM_PROVIDER=mock - skipping the Groq key test (offline mode)")
        return

    check("GROQ_API_KEY is set in .env", config.api_key_is_set(),
          "paste your key from https://console.groq.com/keys into backend/.env")
    if not config.api_key_is_set():
        return

    from app.llm_client import GroqLLM, LLMError
    try:
        turn = GroqLLM().chat([{"role": "user", "content": "Reply with just the word OK."}], tools=None)
        check(f"Groq answered using model {config.GROQ_MODEL} (reply: {turn.content.strip()[:40]!r})", True)
    except LLMError as e:
        check("Groq answered a test message", False, str(e))


def check_search() -> None:
    print("\nStep 3 - search_products")
    search_products, schema = get_tool("search_products", 3, "TASK 3E")
    if search_products is None:
        return

    _, properties, _ = schema_parts(schema)
    check(f"schema inputs are query, category and max_price (got {sorted(properties)})",
          set(properties) == {"query", "category", "max_price"},
          'TASKS 3F and 3G: add "category" and "max_price" under "properties"')
    category = properties.get("category", {})
    check('"category" is a string with an "enum" of the 6 categories',
          isinstance(category, dict) and category.get("type") == "string"
          and isinstance(category.get("enum"), list) and len(category.get("enum")) == 6,
          'TASK 3F: "enum": ["headphones", "laptops", "smartphones", "smartwatches", '
          '"speakers", "accessories"]')
    max_price = properties.get("max_price", {})
    check('"max_price" has "type": "number"',
          isinstance(max_price, dict) and max_price.get("type") == "number", "TASK 3G")

    r = search_products(query="wireless", category="headphones", max_price=3000)
    products = r.get("products", [])
    check(f"wireless headphones under 3000 -> {len(products)} results",
          isinstance(products, list) and len(products) >= 1, 'TASKS 3C and 3D: return {"count": ..., "products": products}')
    if not isinstance(products, list) or not products:
        return
    keys = {"id", "name", "category", "price", "rating", "in_stock"}
    missing = sorted(keys - set(products[0])) if isinstance(products[0], dict) else sorted(keys)
    check("each product has id, name, category, price, rating, in_stock", not missing,
          f"TASK 3C: missing {', '.join(missing)}")
    if missing:
        return
    check("every result costs 3000 or less", all(p["price"] <= 3000 for p in products), "TASK 3B")
    check("every result is in the headphones category",
          all(p["category"] == "headphones" for p in products), "TASK 3A")
    check("in_stock is True or False", all(isinstance(p["in_stock"], bool) for p in products),
          'TASK 3C: use a comparison, row["stock"] > 0')
    check(f'"count" matches the number of products (got {r.get("count")!r})',
          r.get("count") == len(products), "TASK 3D: len(products)")

    r = search_products(category="laptops", max_price=50000)
    products = r.get("products", [])
    check("cheapest laptop under 50000 is listed first (Kito Student Laptop 14)",
          bool(products) and products[0].get("name") == "Kito Student Laptop 14",
          "results should be sorted by price, cheapest first (ORDER BY price ASC)")

    r = search_products(query="unicorn")
    check("a search with no matches returns count 0 and a message",
          r.get("count") == 0 and bool(r.get("message")),
          'TASK 3D: when products is empty, return "count": 0, "products": [] and a "message"')


def check_order() -> None:
    print("\nStep 4 - check_order")
    check_order_fn, schema = get_tool("check_order", 4, "TASKS 4D and 4E")
    if check_order_fn is None:
        return

    _, properties, required = schema_parts(schema)
    order_id = properties.get("order_id", {})
    check('schema has an "order_id" input of type "string"',
          isinstance(order_id, dict) and order_id.get("type") == "string", "TASK 4E")
    check(f'"order_id" is required (got {sorted(required)})', required == {"order_id"},
          'TASK 4E: "required": ["order_id"]')

    r = check_order_fn("ORD1024")
    check("ORD1024 is found", r.get("found") is True, 'TASK 4C: include "found": True')
    check(f"ORD1024 status is Shipped (got {r.get('status')!r})", r.get("status") == "Shipped",
          'TASK 4C: "status": row["status"]')
    keys = ["order_id", "status", "order_date", "estimated_delivery", "items", "total"]
    missing = [k for k in keys if k not in r]
    check("result has order_id, status, order_date, estimated_delivery, items, total", not missing,
          f"TASK 4C: missing {', '.join(missing)}")

    r = check_order_fn("  ord1024 ")
    check("lower-case ID with spaces also works", r.get("found") is True,
          "TASK 4A: strings have .strip() and .upper()")

    r = check_order_fn("ORD9999")
    check("ORD9999 returns found=False and a message (no made-up order)",
          r.get("found") is False and bool(r.get("message")),
          'TASK 4B: return "found": False, the "order_id" and a "message"')


def check_discount() -> None:
    print("\nStep 5 - calculate_discount")
    calculate_discount, schema = get_tool("calculate_discount", 5, "TASK 5E")
    if calculate_discount is None:
        return

    function, properties, required = schema_parts(schema)
    check(f'schema "name" is "calculate_discount" (got {function.get("name")!r})',
          function.get("name") == "calculate_discount",
          "TASK 5E: the name in the schema must match the function name exactly")
    check(f"schema inputs are price and discount_percent, both required (got {sorted(properties)})",
          set(properties) == {"price", "discount_percent"} and required == {"price", "discount_percent"},
          'TASK 5E: use exactly these names under "properties", and list both in "required"')

    keys = ["original_price", "discount_percent", "discount_amount", "final_price"]
    r = calculate_discount(2000, 10)
    missing = [k for k in keys if k not in r]
    check("result has original_price, discount_percent, discount_amount, final_price",
          not missing, f"TASK 5D: missing {', '.join(missing)} (the chat page needs these exact names)")
    check(f"10% off 2000 -> discount 200, final 1800 (got {r.get('discount_amount')}, {r.get('final_price')})",
          r.get("final_price") == 1800 and r.get("discount_amount") == 200, "TASK 5C")

    r = calculate_discount(29990, 10)
    check(f"10% off 29990 -> final 26991 (got {r.get('final_price')})", r.get("final_price") == 26991,
          "TASK 5C")

    r = calculate_discount(999, 33)
    check(f"33% off 999 -> final 669.33, rounded to 2 decimals (got {r.get('final_price')})",
          r.get("final_price") == 669.33 and r.get("discount_amount") == 329.67,
          "TASK 5C: round both amounts to 2 decimals: round(..., 2)")

    try:
        r = calculate_discount.unsafe("2000", "10")
        ok = isinstance(r, dict) and r.get("final_price") == 1800
    except Exception:
        ok = False
    check('numbers sent as text ("2000", "10") also work', ok,
          "TASK 5A: convert both inputs with float(...)")

    check("price of 0 or less returns an error", "error" in calculate_discount(-5, 10),
          'TASK 5B: return {"error": "..."}')
    check("discount above 90% returns an error", "error" in calculate_discount(1000, 150),
          'TASK 5B: return {"error": "..."}')
    check("negative discount returns an error", "error" in calculate_discount(1000, -5),
          'TASK 5B: return {"error": "..."}')


STEPS = {"setup": check_setup, "search": check_search, "order": check_order, "discount": check_discount}

if __name__ == "__main__":
    step = sys.argv[1] if len(sys.argv) > 1 else "all"
    if step != "all" and step not in STEPS:
        print(f"Unknown step '{step}'. Use one of: {', '.join(STEPS)}, all")
        sys.exit(2)

    for name, function in STEPS.items():
        if step in ("all", name):
            try:
                function()
            except StopStep:  # a tool crashed; its FAIL is already printed
                pass

    print(f"\n{passed} passed, {failed} failed")
    sys.exit(1 if failed else 0)
