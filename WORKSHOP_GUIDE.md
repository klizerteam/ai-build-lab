# Workshop Guide: Build ShopBot with Tool Calling

**What you'll build:** ShopBot, a chat assistant for a fictional electronics store called *Demo Bazaar*. It answers questions about products, orders and discounts by calling Python functions ("tools") that you add.

**Why it matters:** a language model on its own knows nothing about your store. It can't see your catalog or your orders, and it can get arithmetic wrong. With tool calling, the model decides *which* function to call and your backend runs it, so every fact in the answer comes from real data.

> [!NOTE]
> The workshop takes about **2 hours**. Each tool starts as a short **outline**, and you write the missing parts. You get less help with each tool, and the third is almost all **written by you**. All your code goes in three small files in `backend/app/`: `tools.py` (the functions), `tool_schemas.py` (the schemas) and `tool_registry.py` (the registration). The web server, the chat loop and the chat page are already built.

> [!TIP]
> This page lists **what to do**, step by step. For the reasons behind each step, longer explanations and the full troubleshooting table, see [README.md](README.md).

```
 React chat UI  ──▶  FastAPI backend  ──▶  Groq LLM  ──▶  Your Python tools
 you ask             runs the loop         picks a tool    reads the database
```

---

## Before you arrive (about 15 minutes)

1. Install **VS Code** from <https://code.visualstudio.com/> and add the **Python** extension (by Microsoft).
2. Install **Python 3.10 or newer** from <https://www.python.org/downloads/>. On Windows, tick **"Add python.exe to PATH"** in the installer.
3. Create a free **Groq** account at <https://console.groq.com/>. Then go to <https://console.groq.com/keys>, click **Create API Key** and **copy the key** (it starts with `gsk_`). Groq only shows it once.
4. **Get the code:** run `git clone <REPO-URL>`, or on GitHub click **Code → Download ZIP** and unzip it.
5. Please keep this google docs link open during live sessions to get links, code snippets, etc. <https://docs.google.com/document/d/1kaTE5sk5nJ17WbbrxQKir4ra6lSlTkWnc3QtsAJPZDY/edit?usp=sharing>
---

## Step 1: Set up and run the app (20 min)

1. Open the `AI-workshop` folder in VS Code (**File → Open Folder…**), then open a terminal (**Terminal → New Terminal**).

2. Create and activate a virtual environment, then install the packages:

   **Windows (PowerShell)**
   ```powershell
   cd backend
   python -m venv .venv
   .venv\Scripts\Activate.ps1
   python -m pip install -r requirements.txt
   ```

   **macOS / Linux**
   ```bash
   cd backend
   python3 -m venv .venv
   source .venv/bin/activate
   python -m pip install -r requirements.txt
   ```

   Your prompt now starts with **`(.venv)`**. If PowerShell says *"running scripts is disabled"*, run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` and activate again.

3. Copy the settings template: `Copy-Item .env.example .env` (Windows) or `cp .env.example .env` (macOS/Linux).

4. Open `backend/.env`, paste your key, and **save**:
   ```ini
   GROQ_API_KEY=gsk_your_real_key_goes_here
   ```

5. Check your setup:
   ```bash
   python check.py setup
   ```
   You should see `6 passed, 0 failed`.

6. Start the server, and leave this terminal running:
   ```bash
   python -m uvicorn app.main:app --reload
   ```

7. Open **<http://localhost:8000>**. You'll see the ShopBot chat with a **Workshop progress** panel showing **Tools (0/3)**.

8. Open **<http://localhost:8000/health>** and confirm `"api_key_configured": true`. The key itself never reaches the browser.

9. Open a **second terminal** (the **+** button in the terminal panel) for running checks. Run `cd backend` and activate the venv again.

✅ **Checkpoint:** the chat page loads and `check.py setup` passes.

---

## Step 2: See what the model can't do yet (15 min)

1. In the chat, send these three messages:

   | Ask | You should see |
   |---|---|
   | `Hi!` | A friendly greeting |
   | `Where is my order ORD1024?` | It says it **can't** check orders yet, and doesn't make up a status |
   | `Write me a poem about the moon.` | A polite refusal: it only helps with shopping |

2. Skim these files in order. You won't change them.
   - `backend/app/main.py`: the `/health` and `/chat` endpoints
   - `backend/app/prompts.py`: the assistant's rules
   - `backend/app/agent.py`: **the tool-calling loop** (ask the model → run the tool it asks for → send back the result → repeat)
   - **Your three files**, which hold a short outline for each tool, with comments marked `TASK` where your code goes:
     - `backend/app/tools.py`: the **functions** (the backend runs them; the model never sees them)
     - `backend/app/tool_schemas.py`: the **schemas** (the only part the model sees)
     - `backend/app/tool_registry.py`: the **registration** (connects each schema to its function)

3. Notice that every tool has three parts, one in each of those files. Each step from now on finishes one tool by writing its parts in all three.

✅ **Checkpoint:** asking about an order gets "I can't do that yet", not a made-up answer.

---

## Step 3: Add tool 1, product search (25 min)

Every tool has three parts, and each part has its own file in `backend/app/`:

| File | Part | Who uses it |
|---|---|---|
| `tools.py` | the **function** | the backend runs it |
| `tool_schemas.py` | the **schema** | the model reads it |
| `tool_registry.py` | the **registration** | connects the two |

Under `# STEP 3: search_products`, each file has an **outline**. Comments marked `TASK 3A`, `TASK 3B`, … show where your code goes, and `...` (as in `return ...`) is a placeholder to replace. Press **Ctrl+F** and search for `TASK 3`. Work **in this order**, and **save after each file**.

> **Write it yourself.** If VS Code shows AI buttons or suggestions (such as **Implement with Codex** or GitHub Copilot), ignore them, or turn those extensions off for this workshop. Typing the code is how it sticks.

1. **The function**, in `backend/app/tools.py`. The keyword filter is written for you as an example:

   | Task | What to write |
   |---|---|
   | **3A** | If a `category` was given: add `" AND category = ?"` to `sql`, and the category in lower case to `params`. The keyword filter just above is your example. |
   | **3B** | If `max_price` was given (`is not None`): add `" AND price <= ?"` to `sql`, and `float(max_price)` to `params`. |
   | **3C** | A list called `products` with one dict per row in `rows`. Keys: `id`, `name`, `category`, `price`, `rating` (read a column like this: `row["name"]`), and `in_stock`, which is `True` when `row["stock"]` is more than 0. |
   | **3D** | Replace `return ...`. If `products` is empty, return `"count": 0`, `"products": []` and a helpful `"message"`, so the model tells the user instead of guessing. Otherwise return `"count": len(products)` and `"products": products`. |

2. **The schema**, in `backend/app/tool_schemas.py`. The `query` input is written for you as an example:

   | Task | What to write |
   |---|---|
   | **3E** | `"description"`: a string that tells the model **when** to use this tool. For example: any question about products, prices or stock. |
   | **3F** | A `"category"` input, written like `"query"` above it: `"type": "string"`, a short `"description"`, and an `"enum"` list of the six categories: `headphones`, `laptops`, `smartphones`, `smartwatches`, `speakers`, `accessories`. The `enum` stops the model inventing a category. |
   | **3G** | A `"max_price"` input: `"type": "number"` and a short `"description"` (maximum price in rupees). |

3. **The registration**, in `backend/app/tool_registry.py`. **TASK 3H:** delete the `# ` at the start of the two lines under `# STEP 3: search_products`, so they read:

   ```python
   TOOLS.append(tool_schemas.SEARCH_PRODUCTS_SCHEMA)
   TOOL_FUNCTIONS["search_products"] = tools.search_products
   ```

   `TOOLS` is the model's menu of schemas. `TOOL_FUNCTIONS` is the **allowlist**: the backend will only run a function listed there. Until you register a tool, it stays switched off.

4. In your second terminal, run `python check.py search`. You should see `16 passed, 0 failed`. Run it as often as you like: each FAIL names the TASK to fix. The full answer is in [README.md → Step 3](README.md#31-write-the-missing-parts).

5. In the browser, wait for **search_products** to turn green (✓), then ask:
   ```
   Find wireless headphones under ₹3,000.
   ```
   You get product cards, all ₹3,000 or less.

6. Click **🔧 Used 1 tool: search_products** under the answer to see the arguments the model chose and the data your function returned. The same call is printed in the server terminal.

✅ **Checkpoint:** product questions return real catalog data.

---

## Step 4: Add tool 2, order lookup (15 min)

Same three files, same order: function, schema, registration. The outline is under `# STEP 4: check_order`, and this time only the database query is written for you. Search for `TASK 4`.

1. **The function**, in `backend/app/tools.py`:

   | Task | What to write |
   |---|---|
   | **4A** | Tidy up `order_id` so `" ord1024 "` becomes `"ORD1024"`. Strings have `.strip()` (removes spaces at both ends) and `.upper()`. |
   | **4B** | If `row is None`, the order doesn't exist: return `"found": False`, the `"order_id"`, and a `"message"` such as `f"No order found with ID {order_id}."` This is what stops the model inventing a status. |
   | **4C** | Replace `return ...`: return `"found": True`, plus the order's `order_id`, `status`, `order_date`, `estimated_delivery`, `items` and `total` (read each one like `row["status"]`). |

2. **The schema**, in `backend/app/tool_schemas.py`:

   | Task | What to write |
   |---|---|
   | **4D** | `"description"`: when to use this tool (getting an order's status and delivery date). |
   | **4E** | `"parameters"`: the same shape as in `SEARCH_PRODUCTS_SCHEMA` (`"type": "object"` and `"properties"`), with one input, `order_id`, of type `"string"`. Then add `"required": ["order_id"]`: this tool can't work without it. |

3. **The registration**, in `backend/app/tool_registry.py`. **TASK 4F:** write the two lines yourself under `# STEP 4: check_order`, following the Step 3 lines.

4. Run `python check.py order`. You should see `12 passed, 0 failed`. The full answer is in [README.md → Step 4](README.md#41-write-the-missing-parts).

5. In the browser, ask:

   | Ask | You should see |
   |---|---|
   | `Where is my order ORD1024?` | **Shipped**, delivery **2026-10-16** |
   | `Where is order ORD9999?` | **Not found.** No made-up status. |

✅ **Checkpoint:** real orders return their status, and unknown orders are reported honestly.

---

## Step 5: Write tool 3 yourself, discounts (25 min)

This time only the function's name and inputs are given. You write the rest yourself, using Steps 3 and 4 as your examples. Same three files, same order: function, schema, registration. Search for `TASK 5`.

**Why a tool for simple maths?** Language models can make arithmetic mistakes. A Python function is exactly right every time, so the model should never work out a discount by itself.

### 5.1 Your task

**a) The function**, in `backend/app/tools.py`. This tool doesn't need the database.

| Task | What to write |
|---|---|
| **5A** | Turn both inputs into numbers with `float(...)`. The model sometimes sends numbers as text, like `"2000"`. |
| **5B** | Reject bad input:<br>if `price` is 0 or less, return `{"error": "Price must be greater than 0."}`<br>if `discount_percent` is below 0 or above 90, return `{"error": "Discount must be between 0 and 90 percent."}`<br>The model reads the error and explains it to the user, instead of showing a nonsense price. |
| **5C** | discount amount = price × discount_percent ÷ 100<br>final price = price − discount amount<br>Round both to 2 decimals with `round(..., 2)`. |
| **5D** | Replace `return ...` with a dict with exactly these four keys: `original_price`, `discount_percent`, `discount_amount`, `final_price`. The chat page uses these names to draw the price receipt. |

**b) The schema**, in `backend/app/tool_schemas.py`:

| Task | What to write |
|---|---|
| **5E** | Replace the `...` with the whole schema. Copy `CHECK_ORDER_SCHEMA` as a starting point, then change it:<br>• `"name": "calculate_discount"`<br>• a `"description"` that tells the model **when** to use it. Tip: tell it to always use this tool instead of doing the maths itself.<br>• two inputs, `price` and `discount_percent`, both `"type": "number"` with a short description, and both in `"required"`. |

> The input names in the schema must match the function's argument names **exactly**. The backend calls your function with whatever names the model sends, and the model copies them from the schema.

**c) The registration**, in `backend/app/tool_registry.py`. **TASK 5F:** the two registration lines, under `# STEP 5: calculate_discount`.

### 5.2 Check your work

```bash
python check.py discount
```

Each FAIL tells you which TASK is wrong. Fix it, save, and run the check again. When everything passes, the last line reads `15 passed, 0 failed`.

### 5.3 Stuck?

Try for a while before opening these. Working it out yourself is the point of this step.

<details>
<summary>💡 Hint: an outline for the function</summary>

```python
def calculate_discount(price: float, discount_percent: float) -> dict:
    """Apply a percentage discount to a price."""
    price = float(price)
    discount_percent = ...

    if price <= 0:
        return {"error": "Price must be greater than 0."}
    if ...:
        return {"error": "Discount must be between 0 and 90 percent."}

    discount_amount = round(..., 2)
    final_price = round(..., 2)

    return {
        "original_price": price,
        ...
    }
```

</details>

<details>
<summary>✅ Answer: all three parts</summary>

In `backend/app/tools.py`:

```python
def calculate_discount(price: float, discount_percent: float) -> dict:
    """Apply a percentage discount to a price."""
    price = float(price)
    discount_percent = float(discount_percent)

    # Validate: refuse numbers that make no sense.
    if price <= 0:
        return {"error": "Price must be greater than 0."}
    if discount_percent < 0 or discount_percent > 90:
        return {"error": "Discount must be between 0 and 90 percent."}

    discount_amount = round(price * discount_percent / 100, 2)
    final_price = round(price - discount_amount, 2)

    return {
        "original_price": price,
        "discount_percent": discount_percent,
        "discount_amount": discount_amount,
        "final_price": final_price,
    }
```

In `backend/app/tool_schemas.py`:

```python
CALCULATE_DISCOUNT_SCHEMA = {
    "type": "function",
    "function": {
        "name": "calculate_discount",
        "description": (
            "Calculate the price after a percentage discount. "
            "Always use this instead of doing the maths yourself."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "price": {
                    "type": "number",
                    "description": "Original price in rupees, e.g. 29990.",
                },
                "discount_percent": {
                    "type": "number",
                    "description": "Discount percentage, e.g. 10 for 10% off.",
                },
            },
            "required": ["price", "discount_percent"],
        },
    },
}
```

In `backend/app/tool_registry.py`:

```python
TOOLS.append(tool_schemas.CALCULATE_DISCOUNT_SCHEMA)
TOOL_FUNCTIONS["calculate_discount"] = tools.calculate_discount
```

</details>

### 5.4 Chain two tools

Workshop progress now shows **Tools (3/3)**. Ask one question that needs two tools:

```
Find the cheapest laptop under ₹50,000 and show its price after 10% off.
```

Expected: **Kito Student Laptop 14**, ₹29,990 → **₹26,991**. The 🔧 panel shows **Used 2 tools: search_products → calculate_discount**, which means the loop in `agent.py` ran twice. Your tool did the maths.

✅ **Checkpoint:** you wrote a tool yourself, and one question used two tools in a single answer.

---

## Step 6: Test everything (10 min)

1. Run every check:
   ```bash
   python check.py all
   ```
   The last line should read `49 passed, 0 failed`.

2. Click **Clear chat**, then try each question. You can also click the examples on the page.

   | Ask | Tool(s) used | Expected answer |
   |---|---|---|
   | `Find wireless headphones under ₹3,000.` | `search_products` | Headphones ≤ ₹3,000 |
   | `Where is my order ORD1024?` | `check_order` | Shipped, 2026-10-16 |
   | `Find the cheapest laptop under ₹50,000 and show its price after 10% off.` | `search_products` → `calculate_discount` | ₹26,991 |
   | `Where is order ORD9999?` | `check_order` | Not found |
   | `Write me a poem about the moon.` | *(none)* | Polite refusal |
   | `Who won the cricket match yesterday?` | *(none)* | Polite refusal |

3. Optional: run `python run_prompts.py` to send all six questions automatically (about 2 minutes).

✅ **You're done!** Before you leave, make sure you can answer these two questions:
- Why does the model never run the tool itself?
- Where does the API key live, and why must it never be in the frontend?

---

## Finished early? Try the bonus

Add a fourth tool, `check_inventory`, that reports how many units of a product are in stock. The code and steps are in [README.md → Bonus](README.md#bonus-a-fourth-tool-check_inventory).

---

## Stuck?

| Situation | What to do |
|---|---|
| Fell behind or code won't work | Run `python check.py <step>` and read the hints. Still stuck? Copy the code from the step's **✅ Answer** section ([README.md](README.md)), save, and carry on. |
| No internet, or Groq errors or rate limits | In `backend/.env` set `LLM_PROVIDER=mock`, then restart the server |
| A tool doesn't turn green | It turns green only once its two registration lines are in `tool_registry.py` (not commented out) and saved. Did you **save all three files**? Check the server terminal for a red `IndentationError` or `SyntaxError` |
| `AttributeError: module 'app.tools' has no attribute ...` (or `app.tool_schemas`) | A name in a registration line has a typo, or part of the outline was deleted. Compare with the step's ✅ Answer section in README.md |
| Chat errors, or status goes offline, after registering a tool | That tool isn't finished: a `...` placeholder is still there. Run `python check.py <step>`: it names the TASK to finish |
| Anything else | See [README.md → Troubleshooting](README.md#troubleshooting), or raise your hand |

> `.env` changes need a server restart. `--reload` only picks up changes to `.py` files.

---

## Cleanup

1. Stop the server: click in its terminal and press **Ctrl+C**.
2. Run `deactivate` in both terminals to leave the virtual environment.
3. If you no longer need your Groq key, delete it at <https://console.groq.com/keys>.
4. Never commit `backend/.env`. It's git-ignored, so leave it that way.
