# Build an E-commerce AI Assistant with Tool Calling

A beginner-friendly, hands-on workshop (about 2 hours).

You will build **ShopBot**, a chat assistant for a fictional electronics store called *Demo Bazaar*. ShopBot answers shopping questions by calling **real Python functions ("tools")** that you write:

| Tool | What it does |
|---|---|
| `search_products` | Finds products by keyword, category and maximum price |
| `check_order` | Looks up an order ID in the database and returns its status and estimated delivery |
| `calculate_discount` | Takes a price and a percentage, returns the discount amount and final price |

The AI model **decides** which tool to call. **Our Python backend runs it** and gives the result back to the model. No agent framework is used, so you can see every step of how tool calling works.

> **You only write the tool code** (Steps 3, 4 and 5). Each tool starts as a short **outline**; you write the missing parts. You get less help with each tool, and the third one is almost all yours. It goes in three small files: `tools.py` (the functions), `tool_schemas.py` (the schemas) and `tool_registry.py` (the registration). Everything else (the web server, the chat loop and the chat page) is already built for you.

> **Just want the steps?** [WORKSHOP_GUIDE.md](WORKSHOP_GUIDE.md) is a shorter walkthrough that lists only what you do in each step. This README has the full explanations, troubleshooting and reference.

---

## Contents

- [What you need before the workshop](#what-you-need-before-the-workshop)
- [How the app works](#how-the-app-works)
- [Project files](#project-files)
- [Step 1: Setup](#step-1-setup)
- [Step 2: Walk through the chat flow](#step-2-walk-through-the-chat-flow)
- [Step 3: Tool 1, product search](#step-3-tool-1-product-search)
- [Step 4: Tool 2, order lookup](#step-4-tool-2-order-lookup)
- [Step 5: Write tool 3 yourself (discount + multi-tool)](#step-5-write-tool-3-yourself-discount--multi-tool)
- [Step 6: Test end to end](#step-6-test-end-to-end)
- [Bonus: a fourth tool (check_inventory)](#bonus-a-fourth-tool-check_inventory)
- [If you get stuck](#if-you-get-stuck)
- [No internet or Groq problems? Use mock mode](#no-internet-or-groq-problems-use-mock-mode)
- [Troubleshooting](#troubleshooting)
- [Reference](#reference)

---

## What you need before the workshop

Please do these **before** you arrive. They take about 15 minutes.

### 1. Install VS Code

Download from <https://code.visualstudio.com/> and install it. (Any editor works, but these steps use VS Code.)

Recommended: open VS Code, go to **Extensions** (the four-squares icon on the left), search for **Python** (by Microsoft) and install it.

### 2. Install Python 3.10 or newer

Download from <https://www.python.org/downloads/>.

- **Windows:** in the installer, **tick "Add python.exe to PATH"** on the first screen before clicking *Install Now*.
- **macOS:** run the downloaded `.pkg` installer.

Check that it works. Open a terminal (Windows: *PowerShell*; macOS: *Terminal*) and run:

**Windows**
```powershell
python --version
```

**macOS / Linux**
```bash
python3 --version
```

You should see `Python 3.10` or higher (for example `Python 3.12.10`).

### 3. Create a free Groq account and API key

Groq hosts the AI model we use. The free tier is enough for this workshop.

1. Go to <https://console.groq.com/> and sign up (Google sign-in works).
2. Open <https://console.groq.com/keys>.
3. Click **Create API Key**, give it a name such as `workshop`, and click **Submit**.
4. **Copy the key now** (it starts with `gsk_`). Groq only shows it once. Paste it somewhere private, such as a note on your laptop.

> **Keep your key secret.** Never put it in frontend code, screenshots, chat messages or a public GitHub repo. In this project it lives only in a file called `.env` on the backend.

### 4. Get the project code

Either:

- **With Git:** `git clone <REPO-URL>` (your facilitator will share the URL), **or**
- **Without Git:** on the GitHub page click **Code → Download ZIP**, then unzip it somewhere easy to find, such as your Desktop or Documents folder.

The steps below assume the project folder is called `AI-workshop`.

---

## How the app works

```
 ┌──────────────┐     ┌──────────────────┐     ┌────────────┐     ┌──────────────────┐
 │ React chat UI│ ──▶ │ FastAPI backend  │ ──▶ │  Groq LLM  │ ──▶ │  Python tools    │
 │ you type a   │     │ runs the         │     │ decides    │     │ SQLite lookup /  │
 │ question     │     │ tool-calling loop│     │ which tool │     │ calculation      │
 └──────────────┘     └──────────────────┘     └────────────┘     └──────────────────┘
```

What happens when you ask **"Where is my order ORD1024?"**:

```
1. Browser  → Backend : {"message": "Where is my order ORD1024?"}
2. Backend  → Groq    : the conversation + the list of tool schemas
3. Groq     → Backend : "please call check_order with {"order_id": "ORD1024"}"
4. Backend            : checks check_order is allowed, runs the Python function
                        → {"found": true, "status": "Shipped", "estimated_delivery": "2026-10-16", ...}
5. Backend  → Groq    : the conversation + that tool result
6. Groq     → Backend : "Your order ORD1024 has shipped and should arrive by 16 Oct 2026."
7. Backend  → Browser : the reply + a list of the tools that ran
```

Key ideas:

- The model **never runs code and never touches the database.** It only *asks* for a tool by name, with arguments. Our backend decides whether to run it.
- The backend only runs tools from an **allowlist** (`TOOL_FUNCTIONS`). If the model asks for anything else, it is refused.
- The model can call tools **one after another**. For example: search for a laptop, then calculate a discount on its price.
- The **API key stays on the backend**. The browser only talks to our own server.

---

## Project files

```
AI-workshop/
├── README.md                ← this guide
├── .gitignore               ← keeps .env (your key) out of Git
├── backend/
│   ├── app/
│   │   ├── main.py          ← FastAPI server: /health and /chat endpoints
│   │   ├── agent.py         ← the tool-calling loop + safe tool runner
│   │   ├── llm_client.py    ← talks to Groq (the only provider-specific file)
│   │   ├── prompts.py       ← the system prompt (rules for the assistant)
│   │   ├── masking.py       ← hides personal data (emails, phones, cards...) from the model
│   │   ├── tools.py         ← ★ YOU FINISH: the tool functions (what the backend runs)
│   │   ├── tool_schemas.py  ← ★ YOU FINISH: the tool schemas (what the model reads)
│   │   ├── tool_registry.py ← ★ YOU FINISH: the registration (connects the two)
│   │   ├── database.py      ← SQLite helpers
│   │   ├── schemas.py       ← request/response shapes
│   │   ├── mock_llm.py      ← offline fake model (backup plan)
│   │   └── config.py        ← reads settings from .env
│   ├── data/
│   │   ├── products.csv     ← 30 fictional products
│   │   └── orders.csv       ← 10 fictional orders (ORD1021–ORD1030)
│   ├── check.py             ← checkpoint tests for each step
│   ├── check_masking.py     ← tests for personal-data masking (no internet needed)
│   ├── run_prompts.py       ← runs all the test questions in one go
│   ├── seed_db.py           ← rebuilds the database from the CSV files
│   ├── requirements.txt     ← Python packages to install
│   └── .env.example         ← template for your .env settings file
└── frontend/
    ├── index.html           ← the chat page
    ├── app.jsx              ← the React chat UI
    ├── styles.css
    └── vendor/              ← React, saved locally (no npm needed)
```

> **No Node.js or npm needed.** The React UI is served by the Python backend, so one command starts everything.

---

## Step 1: Setup

**Goal:** the app runs in your browser, and your API key is stored only on the backend.

### 1.1 Open the project in VS Code

1. Open VS Code.
2. **File → Open Folder…** and choose the `AI-workshop` folder.
3. If VS Code asks *"Do you trust the authors?"*, click **Yes, I trust the authors**.
4. Open a terminal inside VS Code: menu **Terminal → New Terminal**. It opens at the bottom, already inside `AI-workshop`.

### 1.2 Go into the backend folder

All Python commands are run from the `backend` folder.

```bash
cd backend
```

### 1.3 Create a virtual environment

A *virtual environment* (venv) is a private folder of Python packages just for this project.

**Windows (PowerShell)**
```powershell
python -m venv .venv
```

**macOS / Linux**
```bash
python3 -m venv .venv
```

This creates a `.venv` folder inside `backend`. It takes a few seconds and prints nothing if it worked.

### 1.4 Activate the virtual environment

**Windows (PowerShell)**
```powershell
.venv\Scripts\Activate.ps1
```

> If you get an error saying *"running scripts is disabled on this system"*, run this once, then run the activate command again:
> ```powershell
> Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
> ```

**Windows (Command Prompt / cmd)**
```bat
.venv\Scripts\activate.bat
```

**macOS / Linux**
```bash
source .venv/bin/activate
```

When it works, your prompt starts with **`(.venv)`**, like this:

```
(.venv) PS C:\Users\you\Desktop\AI-workshop\backend>
```

> **Every new terminal needs this activate step.** If you don't see `(.venv)`, activate again.

From now on, **`python` means the venv's Python on every system**, including macOS.

### 1.5 Install the packages

```bash
python -m pip install -r requirements.txt
```

This installs **FastAPI** (web server), **Uvicorn** (runs the server), **groq** (Groq's Python library) and **python-dotenv** (reads the `.env` file). It takes about a minute.

> If you see `[notice] A new release of pip is available`, ignore it. That's not an error.

### 1.6 Create your `.env` file and add your key

Copy the template:

**Windows (PowerShell)**
```powershell
Copy-Item .env.example .env
```

**macOS / Linux**
```bash
cp .env.example .env
```

Now open `backend/.env` in VS Code (click it in the Explorer on the left). Replace `your_groq_api_key_here` with your real key:

```ini
GROQ_API_KEY=gsk_your_real_key_goes_here
```

- No spaces around `=` and no quotes.
- **Save the file** (Ctrl+S on Windows, Cmd+S on macOS).

Leave the other settings as they are:

```ini
GROQ_MODEL=openai/gpt-oss-120b
LLM_PROVIDER=groq
```

> `.env` is listed in `.gitignore`, so Git will never upload it.

### 1.7 Run the setup check

```bash
python check.py setup
```

Expected output (your Python version may differ):

```
Step 1 - setup
  PASS  Python version is 3.10 or newer (you have 3.12.10)
  PASS  packages installed (fastapi, uvicorn, groq, python-dotenv)
  PASS  backend/.env file exists
  PASS  database has data (30 products, 10 orders)
  PASS  GROQ_API_KEY is set in .env
  PASS  Groq answered using model openai/gpt-oss-120b (reply: 'OK')

6 passed, 0 failed
```

If anything says `FAIL`, read the `hint:` line under it, or see [Troubleshooting](#troubleshooting).

### 1.8 Start the server

```bash
python -m uvicorn app.main:app --reload
```

You should see:

```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Application startup complete.
```

- **Leave this terminal running.** It is your server. Tool calls will be printed here.
- `--reload` restarts the server automatically every time you save a `.py` file.
- To stop the server: click in the terminal and press **Ctrl+C**.

### 1.9 Open the app

Open this address in your browser: **<http://localhost:8000>**

You should see the **Demo Bazaar / ShopBot** page. On the right is the **Workshop progress** panel (on a narrow window, it's a strip under the top bar):

```
Backend: connected · Model: openai/gpt-oss-120b
Tools (0/3)
  ○ search_products      Product search · step 3
  ○ check_order          Order lookup · step 4
  ○ calculate_discount   Discount calculator · step 5
```

This panel checks the backend every few seconds. Each tool turns green with a **✓** as soon as you add it, with no need to refresh.

### 1.10 Prove the key is server-side only

Open **<http://localhost:8000/health>**. You'll see something like:

```json
{"status":"ok","provider":"groq","model":"openai/gpt-oss-120b","api_key_configured":true,"tools":[]}
```

The browser only learns *that* a key is configured (`true`). It never sees the key itself. You can also right-click the chat page → **View Page Source**: there is no key anywhere in the frontend.

### ✅ Checkpoint 1

- [ ] `python check.py setup` shows `0 failed`
- [ ] The chat page opens at <http://localhost:8000>
- [ ] `/health` shows `"api_key_configured": true` and does not show the key

### 1.11 Open a second terminal (for running checks)

Your first terminal is busy running the server. Open a **second** one for the `check.py` commands:

1. In the VS Code terminal panel, click the **+** button (top-right of the terminal panel).
2. In the new terminal, go to the backend folder and activate the venv again:

**Windows (PowerShell)**
```powershell
cd backend
.venv\Scripts\Activate.ps1
```

**macOS / Linux**
```bash
cd backend
source .venv/bin/activate
```

You can switch between the two terminals using the list on the right side of the terminal panel.

---

## Step 2: Walk through the chat flow

**Goal:** understand the pre-built code, and see that chat works *without* tools.

### 2.1 Try the chat with no tools

In the browser, send these messages one at a time:

| Type this | What you should see |
|---|---|
| `Hi!` | A friendly greeting saying what ShopBot can help with |
| `Where is my order ORD1024?` | It says it **can't** check orders yet. It has no tool, so it can't know. Good: it does not invent a status. |
| `Write me a poem about the moon.` | It politely declines and says it only helps with products, orders and discounts |

This is the problem tools solve: the model alone knows nothing about *our* store's products or orders.

### 2.2 Read the code, in this order

Open each file in VS Code and read the comments. You don't need to change any of them.

**1. `backend/app/main.py`: the web server.**
- `GET /health` reports which tools are loaded.
- `POST /chat` receives `{"message": "...", "history": [...]}` and calls `run_agent(...)`.
- The last line serves the React page from the `frontend/` folder.

**2. `backend/app/prompts.py`: the system prompt.**
The rules the model reads before every conversation: only help with products, orders and discounts; never invent data; politely decline off-topic questions. **Off-topic handling is done here, with no extra tool.**

**3. `backend/app/agent.py`: the tool-calling loop. This is the most important file.**

```python
for _ in range(MAX_TOOL_ROUNDS):
    turn = llm.chat(messages, tools=registry.TOOLS or None)  # 1. ask the model

    if not turn.tool_calls:                                # 2. plain answer? done
        return {"reply": turn.content, ...}

    messages.append({... the model's tool request ...})    # 3. remember the request
    for call in turn.tool_calls:
        arguments, result = run_tool(call.name, call.arguments)   # 4. WE run the tool
        messages.append({"role": "tool", "tool_call_id": call.id,
                         "content": json.dumps(result)})   # 5. give the result back
    # ...and loop: the model now sees the result and can answer or call another tool
```

And `run_tool(...)`, the safety layer:
- Only runs functions listed in `TOOL_FUNCTIONS` (the **allowlist**).
- Parses the model's JSON arguments and rejects anything that isn't a JSON object.
- Turns any error into a message the model can read, so a bad tool call never crashes the server.

**4. `backend/app/llm_client.py`: the only file that knows about Groq.**
It sends `model`, `messages`, `tools` and `tool_choice="auto"` to Groq, and converts the reply into a simple `AssistantTurn(content, tool_calls)`. It also turns Groq errors (bad key, rate limit, no internet) into friendly messages.

**5. Your three files.** Each one holds a short **outline** for each tool, with comments marked `TASK` where your code goes. No tools are switched on yet. Every tool has **three parts**, and each part lives in its own file:

| File | Part | What it is | Who uses it |
|---|---|---|---|
| `backend/app/tools.py` | **Function** | A normal Python function that does the work | Our backend runs it. The model never sees it |
| `backend/app/tool_schemas.py` | **Schema** | A dictionary describing the tool's name, purpose and arguments | Sent to the model so it knows the tool exists |
| `backend/app/tool_registry.py` | **Registration** | `TOOLS.append(...)` + `TOOL_FUNCTIONS["name"] = function` | Connects the two |

`tool_registry.py` holds the two lists that `agent.py` reads:

```python
TOOLS = []            # tool schemas the model can see
TOOL_FUNCTIONS = {}   # tool name -> Python function (the allowlist)
```

> The **description** in a schema matters a lot. It is the only thing the model reads to decide *when* to use your tool and *what* to pass.

### 2.3 Look at the data (optional)

Open `backend/data/products.csv` and `backend/data/orders.csv` in VS Code. When the server first starts, these are loaded into the SQLite database file `backend/data/shop.db`. All products, brands and orders are fictional.

### ✅ Checkpoint 2

- [ ] Chat replies to "Hi!" (the model works without tools)
- [ ] Asking about an order gives "I can't do that yet", not a made-up status

---

## Step 3: Tool 1, product search

**Goal:** product questions return real data from our catalog.

### 3.1 Write the missing parts

Every tool has three parts, and each part has its own file in `backend/app/`. Under `# STEP 3: search_products`, each file has an **outline** for this tool. The parts that aren't about tool calling (the SQL setup and the database call) are written for you. Comments marked `TASK 3A`, `TASK 3B`, … show where your code goes, and `...` (as in `return ...`) is a placeholder for you to replace. Tip: press **Ctrl+F** and search for `TASK 3`.

Work **in this order**: function, schema, then registration. **Save after each file.** The tool stays switched off until you register it, so the server keeps running while you work.

> **Write it yourself.** If VS Code shows AI buttons or suggestions (such as **Implement with Codex** or GitHub Copilot), ignore them, or turn those extensions off for this workshop. Typing the code is how it sticks.

**a) The function**, in `backend/app/tools.py`:

| Task | What to write |
|---|---|
| **3A** | If a `category` was given: add `" AND category = ?"` to `sql`, and the category in lower case to `params`. The keyword filter just above is your example. |
| **3B** | If `max_price` was given (`is not None`): add `" AND price <= ?"` to `sql`, and `float(max_price)` to `params`. |
| **3C** | A list called `products` with one dict per row in `rows`. Keys: `id`, `name`, `category`, `price`, `rating` (read a column like this: `row["name"]`), and `in_stock`, which is `True` when `row["stock"]` is more than 0. |
| **3D** | Replace `return ...`. If `products` is empty, return `"count": 0`, `"products": []` and a helpful `"message"`, so the model tells the user instead of guessing. Otherwise return `"count": len(products)` and `"products": products`. |

**b) The schema**, in `backend/app/tool_schemas.py`. The `query` input is written for you as an example.

| Task | What to write |
|---|---|
| **3E** | `"description"`: a string that tells the model **when** to use this tool. For example: any question about products, prices or stock. |
| **3F** | A `"category"` input, written like `"query"` above it: `"type": "string"`, a short `"description"`, and an `"enum"` list of the six categories: `headphones`, `laptops`, `smartphones`, `smartwatches`, `speakers`, `accessories`. The `enum` stops the model inventing a category. |
| **3G** | A `"max_price"` input: `"type": "number"` and a short `"description"` (maximum price in rupees). |

**c) The registration**, in `backend/app/tool_registry.py`:

| Task | What to do |
|---|---|
| **3H** | Switch the tool on: delete the `# ` at the start of the two lines under `# STEP 3: search_products`. |

They should now read:

```python
TOOLS.append(tool_schemas.SEARCH_PRODUCTS_SCHEMA)
TOOL_FUNCTIONS["search_products"] = tools.search_products
```

<details>
<summary>✅ Answer: the finished function and schema</summary>

In `backend/app/tools.py`:

```python
def search_products(query: str = "", category: str = "", max_price: float | None = None) -> dict:
    """Find products in the catalog. Every filter is optional."""
    sql = "SELECT id, name, category, price, rating, stock FROM products WHERE 1=1"
    params = []

    # Every keyword must appear in the product's name, description or tags.
    for word in (query or "").lower().split():
        sql += " AND (LOWER(name) LIKE ? OR LOWER(description) LIKE ? OR LOWER(tags) LIKE ?)"
        params += [f"%{word}%"] * 3

    if category:
        sql += " AND category = ?"
        params.append(category.lower())

    if max_price is not None:
        sql += " AND price <= ?"
        params.append(float(max_price))

    sql += " ORDER BY price ASC LIMIT 5"  # cheapest first, at most 5 results

    with get_connection() as conn:
        rows = conn.execute(sql, params).fetchall()

    products = [
        {
            "id": row["id"],
            "name": row["name"],
            "category": row["category"],
            "price": row["price"],
            "rating": row["rating"],
            "in_stock": row["stock"] > 0,
        }
        for row in rows
    ]

    if not products:
        return {
            "count": 0,
            "products": [],
            "message": "No matching products. Try fewer keywords or a higher max_price.",
        }
    return {"count": len(products), "products": products}
```

In `backend/app/tool_schemas.py`:

```python
SEARCH_PRODUCTS_SCHEMA = {
    "type": "function",
    "function": {
        "name": "search_products",
        "description": (
            "Search the Demo Bazaar product catalog. Use this for any question about "
            "products, prices or stock. Returns up to 5 matches, cheapest first."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": (
                        "1-3 product keywords, e.g. 'wireless' or 'gaming'. "
                        "Do not include prices or words like 'cheap' or 'best'."
                    ),
                },
                "category": {
                    "type": "string",
                    "enum": ["headphones", "laptops", "smartphones",
                             "smartwatches", "speakers", "accessories"],
                    "description": "Product category to search in.",
                },
                "max_price": {
                    "type": "number",
                    "description": "Maximum price in rupees, e.g. 3000.",
                },
            },
        },
    },
}
```

</details>

### 3.2 What this code does

**The function `search_products`:**
- All three arguments are optional, so the model can search by keyword, category, price or any mix.
- It builds an SQL query step by step. `WHERE 1=1` is always true; it's a trick so every filter can simply be added with `AND ...`.
- **Keyword filter:** each word in `query` must appear in the product's name, description or tags. The `?` placeholders keep the SQL safe from injection.
- **Category filter** and **price filter** (`price <= max_price`) are only added if the model passed them.
- `ORDER BY price ASC LIMIT 5`: cheapest first, never more than 5 results. A bounded result keeps responses small.
- If nothing matches, it returns `count: 0` and a helpful message, so the model can tell the user instead of guessing.

**The schema `SEARCH_PRODUCTS_SCHEMA`:**
- `name` must exactly match the key in `TOOL_FUNCTIONS`.
- `description` tells the model *when* to use the tool.
- `parameters` is a JSON Schema. `enum` limits `category` to the six real categories, so the model can't invent one.

**The registration** (the two lines in `tool_registry.py`): `TOOLS.append(...)` puts the schema on the model's menu, and `TOOL_FUNCTIONS[...]` adds the function to the allowlist. The prefixes `tool_schemas.` and `tools.` show which file each piece comes from.

### 3.3 Check your code

The server reloads by itself when you save (you'll see `Reloading...` in the server terminal). In your **second terminal**, run:

```bash
python check.py search
```

You can run it at any time, even before you've finished: each FAIL names the TASK to look at. When everything is written and registered, you'll see:

```
Step 3 - search_products
  PASS  search_products function is in app/tools.py
  PASS  SEARCH_PRODUCTS_SCHEMA is in app/tool_schemas.py
  PASS  SEARCH_PRODUCTS_SCHEMA has no ... left
  PASS  search_products schema is in TOOLS (app/tool_registry.py)
  PASS  search_products is registered in TOOL_FUNCTIONS (app/tool_registry.py)
  PASS  schema inputs are query, category and max_price (got ['category', 'max_price', 'query'])
  PASS  "category" is a string with an "enum" of the 6 categories
  PASS  "max_price" has "type": "number"
  PASS  wireless headphones under 3000 -> 3 results
  PASS  each product has id, name, category, price, rating, in_stock
  PASS  every result costs 3000 or less
  PASS  every result is in the headphones category
  PASS  in_stock is True or False
  PASS  "count" matches the number of products (got 3)
  PASS  cheapest laptop under 50000 is listed first (Kito Student Laptop 14)
  PASS  a search with no matches returns count 0 and a message

16 passed, 0 failed
```

> `check.py` calls your Python function directly, with no AI involved. So if it passes, your tool is correct, whatever the model does.

### 3.4 Try it in the browser

Look at **Workshop progress** on the right: within a few seconds **search_products** turns green with a **✓**. (If it doesn't, refresh the page with F5.)

Ask:

```
Find wireless headphones under ₹3,000.
```

Expected: a list of headphones, all priced ₹3,000 or less (for example *Vyom Sport Wireless Neckband ₹1,299*, *Auralis Bass Pro Wireless Earbuds ₹1,999*, *Auralis Wireless Over-Ear Headphones ₹2,799*).

Under the answer you'll see **product cards**, drawn from the data your function returned. Below them, click **🔧 Used 1 tool: search_products** to see the exact arguments the model chose and the raw JSON your function returned. Also look at the **server terminal**:

```
[tool] model asked for search_products({"query": "wireless", "category": "headphones", "max_price": 3000})
[tool] result: {"count": 3, "products": [...]}
```

More to try: `Show me smartwatches`, `Any gaming laptops?`, `Bluetooth speakers under 2000`.

### ✅ Checkpoint 3

- [ ] `python check.py search` shows `0 failed`
- [ ] Product questions in the browser return catalog data, and the 🔧 panel shows `search_products`

---

## Step 4: Tool 2, order lookup

**Goal:** a valid order ID returns its status, and an unknown ID is handled honestly.

### 4.1 Write the missing parts

Same three files, same order: function, schema, registration. The outline is under `# STEP 4: check_order`, and this time only the database query is written for you. Search for `TASK 4`.

**a) The function**, in `backend/app/tools.py`:

| Task | What to write |
|---|---|
| **4A** | Tidy up `order_id` so `" ord1024 "` becomes `"ORD1024"`. Strings have `.strip()` (removes spaces at both ends) and `.upper()`. |
| **4B** | If `row is None`, the order doesn't exist: return `"found": False`, the `"order_id"`, and a `"message"` such as `f"No order found with ID {order_id}."` This is what stops the model inventing a status. |
| **4C** | Replace `return ...`: return `"found": True`, plus the order's `order_id`, `status`, `order_date`, `estimated_delivery`, `items` and `total` (read each one like `row["status"]`). |

**b) The schema**, in `backend/app/tool_schemas.py`:

| Task | What to write |
|---|---|
| **4D** | `"description"`: when to use this tool (getting an order's status and delivery date). |
| **4E** | `"parameters"`: the same shape as in `SEARCH_PRODUCTS_SCHEMA` (`"type": "object"` and `"properties"`), with one input, `order_id`, of type `"string"`. Then add `"required": ["order_id"]`: this tool can't work without it. |

**c) The registration**, in `backend/app/tool_registry.py`:

| Task | What to write |
|---|---|
| **4F** | No `#` to delete this time: write the two registration lines yourself under `# STEP 4: check_order`, following the Step 3 lines. |

<details>
<summary>✅ Answer: the finished function and schema</summary>

In `backend/app/tools.py`:

```python
def check_order(order_id: str) -> dict:
    """Look up one order by its ID, e.g. ORD1024."""
    order_id = order_id.strip().upper()  # " ord1024 " -> "ORD1024"

    with get_connection() as conn:
        row = conn.execute(
            "SELECT order_id, order_date, items, total, status, estimated_delivery "
            "FROM orders WHERE order_id = ?",
            (order_id,),
        ).fetchone()

    # Unknown ID: say so clearly, so the model cannot invent a status.
    if row is None:
        return {
            "found": False,
            "order_id": order_id,
            "message": f"No order found with ID {order_id}.",
        }

    return {
        "found": True,
        "order_id": row["order_id"],
        "status": row["status"],
        "order_date": row["order_date"],
        "estimated_delivery": row["estimated_delivery"],
        "items": row["items"],
        "total": row["total"],
    }
```

In `backend/app/tool_schemas.py`:

```python
CHECK_ORDER_SCHEMA = {
    "type": "function",
    "function": {
        "name": "check_order",
        "description": "Get the status and estimated delivery date of an order.",
        "parameters": {
            "type": "object",
            "properties": {
                "order_id": {
                    "type": "string",
                    "description": "The order ID, e.g. ORD1024.",
                },
            },
            "required": ["order_id"],
        },
    },
}
```

In `backend/app/tool_registry.py`:

```python
TOOLS.append(tool_schemas.CHECK_ORDER_SCHEMA)
TOOL_FUNCTIONS["check_order"] = tools.check_order
```

</details>

### 4.2 What this code does

- `order_id.strip().upper()` cleans the input, so `" ord1024 "` becomes `"ORD1024"`. Users (and models) are not always tidy.
- It reads **one** row from the `orders` table using a `?` placeholder (safe SQL).
- **If the order doesn't exist**, it returns `found: False` with a clear message. This is what stops the model from inventing a status: the tool result says plainly that there is no such order.
- If it exists, it returns **only** the fields the assistant needs: status, dates, items and total.
- In the schema, `"required": ["order_id"]` tells the model this argument must always be sent.

### 4.3 Check your code

```bash
python check.py order
```

Expected:

```
Step 4 - check_order
  PASS  check_order function is in app/tools.py
  PASS  CHECK_ORDER_SCHEMA is in app/tool_schemas.py
  PASS  CHECK_ORDER_SCHEMA has no ... left
  PASS  check_order schema is in TOOLS (app/tool_registry.py)
  PASS  check_order is registered in TOOL_FUNCTIONS (app/tool_registry.py)
  PASS  schema has an "order_id" input of type "string"
  PASS  "order_id" is required (got ['order_id'])
  PASS  ORD1024 is found
  PASS  ORD1024 status is Shipped (got 'Shipped')
  PASS  result has order_id, status, order_date, estimated_delivery, items, total
  PASS  lower-case ID with spaces also works
  PASS  ORD9999 returns found=False and a message (no made-up order)

12 passed, 0 failed
```

### 4.4 Try it in the browser

Check that **check_order** shows a green **✓** in Workshop progress, then ask:

| Ask | Expected |
|---|---|
| `Where is my order ORD1024?` | **Shipped**, estimated delivery **2026-10-16** |
| `Where is order ORD9999?` | Says **no order was found** and asks you to check the ID. No made-up status. |
| `What's the status of ord1022?` | **Processing**, estimated delivery 2026-10-20 |

All sample order IDs: `ORD1021` to `ORD1030` (see `backend/data/orders.csv`).

### ✅ Checkpoint 4

- [ ] `python check.py order` shows `0 failed`
- [ ] A valid ID returns its status; `ORD9999` is reported as not found

---

## Step 5: Write tool 3 yourself (discount + multi-tool)

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

**c) The registration**, in `backend/app/tool_registry.py`:

| Task | What to write |
|---|---|
| **5F** | The two registration lines, under `# STEP 5: calculate_discount`. |

### 5.2 Check your work

```bash
python check.py discount
```

Each FAIL tells you which TASK is wrong. Fix it, save, and run the check again. When everything passes, you'll see:

```
Step 5 - calculate_discount
  PASS  calculate_discount function is in app/tools.py
  PASS  CALCULATE_DISCOUNT_SCHEMA is in app/tool_schemas.py
  PASS  CALCULATE_DISCOUNT_SCHEMA has no ... left
  PASS  calculate_discount schema is in TOOLS (app/tool_registry.py)
  PASS  calculate_discount is registered in TOOL_FUNCTIONS (app/tool_registry.py)
  PASS  schema "name" is "calculate_discount" (got 'calculate_discount')
  PASS  schema inputs are price and discount_percent, both required (got ['discount_percent', 'price'])
  PASS  result has original_price, discount_percent, discount_amount, final_price
  PASS  10% off 2000 -> discount 200, final 1800 (got 200.0, 1800.0)
  PASS  10% off 29990 -> final 26991 (got 26991.0)
  PASS  33% off 999 -> final 669.33, rounded to 2 decimals (got 669.33)
  PASS  numbers sent as text ("2000", "10") also work
  PASS  price of 0 or less returns an error
  PASS  discount above 90% returns an error
  PASS  negative discount returns an error

15 passed, 0 failed
```

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

### 5.4 Try a multi-tool question

Workshop progress should now show **Tools (3/3)**, all green. Ask:

```
Find the cheapest laptop under ₹50,000 and show its price after 10% off.
```

Expected: **Kito Student Laptop 14**, original price **₹29,990**, discount **₹2,999**, final price **₹26,991**.

You'll see product cards **and** a discount receipt. Open the 🔧 panel: it says **Used 2 tools: search_products → calculate_discount**. The model:

1. called `search_products` (category `laptops`, max price 50000),
2. read the results and picked the cheapest laptop,
3. called `calculate_discount` with that laptop's price,
4. wrote the answer from both results.

That's the tool-calling loop in `agent.py` going round twice.

Also try: `What is 15% off ₹2,499?` (one tool, expected final price ₹2,124.15).

### ✅ Checkpoint 5

- [ ] `python check.py discount` shows `0 failed`
- [ ] The laptop question uses **both** tools in one answer

---

## Step 6: Test end to end

**Goal:** every sample question behaves as expected.

### 6.1 Run all the checks

```bash
python check.py all
```

Expected last line: `49 passed, 0 failed`.

### 6.2 Test in the browser

Click **Clear chat** (top-right) to start fresh, then try each of these. The example questions on the empty chat page, and under **Try asking** on the right, send them for you.

| # | Ask | Expected tool(s) | Expected answer |
|---|---|---|---|
| 1 | `Find wireless headphones under ₹3,000.` | `search_products` | Headphones ≤ ₹3,000 with prices |
| 2 | `Where is my order ORD1024?` | `check_order` | Shipped, delivery 2026-10-16 |
| 3 | `Find the cheapest laptop under ₹50,000 and show its price after 10% off.` | `search_products` → `calculate_discount` | Kito Student Laptop 14, ₹26,991 |
| 4 | `Where is order ORD9999?` | `check_order` | Not found, no invented status |
| 5 | `Write me a poem about the moon.` | *(none)* | Politely declines, offers shopping help |
| 6 | `Who won the cricket match yesterday?` | *(none)* | Politely declines, offers shopping help |

### 6.3 Run them all automatically (optional)

```bash
python run_prompts.py
```

This sends all six questions to the model and prints which tools ran and the final answers. It pauses about 12 seconds between questions to stay inside Groq's free-tier limits, so it takes about 2 minutes.

> **AI answers vary.** The wording will differ each time, and very occasionally the model takes a slightly different path. What matters: product, order and price **facts always come from tool results**, and off-topic questions are declined.

### ✅ Checkpoint 6: you're done! 🎉

- [ ] All six questions behave as in the table
- [ ] You can explain why the model never runs the tool itself
- [ ] You can explain where the API key lives, and why it must never be in the frontend

---

## Bonus: a fourth tool (check_inventory)

Finished early? Add a tool that reports **how many units** of a product are in stock.

**1.** Paste each part at the **very bottom** of its file, in this order, and save each one.

In `backend/app/tools.py`:

```python
def check_inventory(product_name: str) -> dict:
    """How many units of a product are in stock?"""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT id, name, stock FROM products WHERE LOWER(name) LIKE ? LIMIT 3",
            (f"%{product_name.strip().lower()}%",),
        ).fetchall()

    if not rows:
        return {"found": False, "message": f"No product with a name like '{product_name}'."}

    return {
        "found": True,
        "products": [
            {"id": row["id"], "name": row["name"], "units_in_stock": row["stock"]}
            for row in rows
        ],
    }
```

In `backend/app/tool_schemas.py`:

```python
CHECK_INVENTORY_SCHEMA = {
    "type": "function",
    "function": {
        "name": "check_inventory",
        "description": (
            "Get how many units of a product are in stock. Use the exact "
            "product name from search_products results when you have it."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "product_name": {
                    "type": "string",
                    "description": "Full or partial product name, e.g. 'Kito Wireless Mouse'.",
                },
            },
            "required": ["product_name"],
        },
    },
}
```

In `backend/app/tool_registry.py`:

```python
TOOLS.append(tool_schemas.CHECK_INVENTORY_SCHEMA)
TOOL_FUNCTIONS["check_inventory"] = tools.check_inventory
```

**2.** Tell the assistant it has a new ability. In `backend/app/prompts.py`, find this line:

```
3. Calculating a discounted price (use the calculate_discount tool).
```

Add a new line straight after it:

```
4. Checking how many units of a product are in stock (use the check_inventory tool).
```

Save.

**3.** Wait until **check_inventory** appears in Workshop progress (as a *Bonus tool*), then ask:

```
How many Kito Wireless Mouse units do you have?
```

Expected: **80 units**. Then try `Is the Kito HD Webcam in stock?` (expected: 0 units, out of stock).

> This tool needs the real Groq model. Mock mode (below) only knows the three core tools.

---

## If you get stuck

No problem:

1. Run `python check.py <step>` (`search`, `order` or `discount`). The hint under each FAIL names the TASK to look at.
2. Open the **✅ Answer** section in that step and compare it with your code, line by line.
3. Still stuck, or short on time? Copy the code from the ✅ Answer section into your file, save, and carry on. The server reloads by itself.

---

## No internet or Groq problems? Use mock mode

If Wi-Fi is down, Groq is unreachable or you hit the rate limit, you can switch to an **offline fake model**. It uses simple keyword rules instead of AI, but it asks for tools just like the real model would, so you can still build and test your tools.

1. In `backend/.env`, set:
   ```ini
   LLM_PROVIDER=mock
   ```
2. Restart the server (Ctrl+C, then `python -m uvicorn app.main:app --reload`).
3. Workshop progress shows `Model: mock (offline)`.

The mock understands the workshop's sample questions, and not much else. Set `LLM_PROVIDER=groq` (and restart) to go back to the real model.

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `python` is not recognized, or opens the Microsoft Store (Windows) | Reinstall Python from python.org and **tick "Add python.exe to PATH"**. Or use `py` instead of `python` for the venv step: `py -m venv .venv`. Then close and reopen VS Code. |
| `python: command not found` (macOS) | Use `python3` for creating the venv. After activating the venv, `python` works. |
| `running scripts is disabled on this system` | Run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`, then activate again. Or use Command Prompt with `.venv\Scripts\activate.bat`. |
| `No module named fastapi` / `uvicorn` / `groq` / `dotenv` | The venv isn't active (no `(.venv)` in the prompt). Activate it (step 1.4), then `python -m pip install -r requirements.txt`. |
| `No module named 'app'` | You're in the wrong folder. `cd backend` first (the folder that contains `app/` and `check.py`). |
| `Could not open requirements file` | Same: run `cd backend` first. |
| `check.py setup` says `.env file exists` FAIL | You didn't copy `.env.example` to `.env`, or saved it somewhere other than the `backend` folder. Its name must be exactly `.env` (not `.env.txt`). |
| Chat says **"GROQ_API_KEY is missing"** | Put your key in `backend/.env`, **save**, and restart the server. |
| Chat says **"Groq rejected the API key"** | The key is wrong or was deleted. Create a new one at <https://console.groq.com/keys>. No quotes, no spaces. |
| Chat says **"rate limit reached"** | The free tier allows a limited number of requests and tokens per minute. Wait about a minute. Keep questions short. If it keeps happening, use `GROQ_MODEL=openai/gpt-oss-20b` or mock mode. |
| Chat says **"Model … was not found"** | Groq changed its model list. Pick a current model at <https://console.groq.com/docs/models>, put it in `GROQ_MODEL`, restart. |
| Chat says **"Could not reach Groq"** | Internet problem. Check Wi-Fi, or use [mock mode](#no-internet-or-groq-problems-use-mock-mode). |
| Chat says **"Cannot reach the backend"** | The server isn't running, or crashed. Look at the server terminal. Start it again with `python -m uvicorn app.main:app --reload`. |
| `[Errno 10048]` / `address already in use` | Another server is already on port 8000 (maybe in another terminal). Close it, or use a different port: `python -m uvicorn app.main:app --reload --port 8001` and open <http://localhost:8001>. |
| Workshop progress still shows **○ … step N** after writing a tool | A tool turns green only once its two registration lines are in `tool_registry.py` (not commented out) and saved. Did you **save all three files**? Wait a few seconds or refresh. If the status says **Backend: offline**, check the server terminal for a red error: a typo in any of the three files stops the server from restarting. |
| `IndentationError` or `SyntaxError` in the server terminal | A typo: a missing quote, comma or bracket, or wrong indentation. Look at the line number in the error. Compare your code with the ✅ Answer section of that step. Every line of a function must be indented with 4 spaces under its `def`. |
| `AttributeError: module 'app.tools' has no attribute ...` (or `app.tool_schemas`) | A name in a registration line doesn't match the function or schema name (a typo), or part of the outline was deleted. Compare with the ✅ Answer section of that step. |
| Chat shows an error, or the status goes **offline**, after you register a tool | That tool isn't finished: a `...` placeholder is still there. Run `python check.py <step>`: it names the TASK to finish. |
| `check.py` says a tool FAILs | The hint under each FAIL names the TASK or file to fix: `tools.py` (function), `tool_schemas.py` (schema) or `tool_registry.py` (the `TOOLS.append(...)` and `TOOL_FUNCTIONS[...] = ...` lines). |
| The model answers without using a tool | Ask more specifically, for example "Search the catalog for …". Make sure Workshop progress shows the tool with a green ✓. Check the schema `description` you wrote says when to use the tool. |
| A search returns nothing | The keywords must appear in the product data. Try fewer words, for example `wireless` instead of `best wireless`. |
| Want to reset the data | `python seed_db.py` rebuilds the database from the CSV files. |

---

## Reference

### API

| Endpoint | Method | Purpose |
|---|---|---|
| `/health` | GET | Readiness check: provider, model, loaded tools, whether a key is configured |
| `/chat` | POST | Send a message, get the assistant's reply |
| `/` | GET | The chat page |
| `/docs` | GET | Interactive API docs (try `/chat` from the browser) |

**Request**
```json
{
  "message": "Find headphones under 3000",
  "history": [
    {"role": "user", "content": "Hi"},
    {"role": "assistant", "content": "Hello! How can I help?"}
  ]
}
```

**Response**
```json
{
  "reply": "Here are some headphones under ₹3,000: ...",
  "tool_calls": [
    {
      "name": "search_products",
      "arguments": {"category": "headphones", "max_price": 3000},
      "result": {"count": 3, "products": ["..."]}
    }
  ]
}
```

Try it from a terminal (macOS/Linux, or Git Bash on Windows):
```bash
curl -X POST http://localhost:8000/chat -H "Content-Type: application/json" -d "{\"message\": \"Where is order ORD1024?\"}"
```

Or in Windows PowerShell:
```powershell
Invoke-RestMethod -Method Post -Uri http://localhost:8000/chat -ContentType "application/json" -Body '{"message": "Where is order ORD1024?"}'
```

### Settings (`backend/.env`)

| Setting | Default | Meaning |
|---|---|---|
| `GROQ_API_KEY` | *(none)* | Your Groq key. Backend only. |
| `GROQ_MODEL` | `openai/gpt-oss-120b` | Groq model; must support tool calling. Alternative: `openai/gpt-oss-20b`. |
| `LLM_PROVIDER` | `groq` | `groq` = real model, `mock` = offline fake model |
| `MASK_PII` | `true` | `true` = hide emails, phone numbers, cards, Aadhaar, PAN, UPI IDs and API keys from the model (see `app/masking.py`) |

### Useful commands (run in `backend/` with the venv active)

| Command | What it does |
|---|---|
| `python -m uvicorn app.main:app --reload` | Start the server at <http://localhost:8000> |
| `python check.py setup` | Check Python, packages, `.env`, database and Groq key |
| `python check.py search` / `order` / `discount` | Check one tool |
| `python check.py all` | Check everything |
| `python run_prompts.py` | Run all six test questions through the model |
| `python seed_db.py` | Rebuild the database from the CSV files |

### Sample data

- **Products** (`backend/data/products.csv`): 30 fictional products in 6 categories: `headphones`, `laptops`, `smartphones`, `smartwatches`, `speakers`, `accessories`. Prices are in Indian Rupees.
- **Orders** (`backend/data/orders.csv`): `ORD1021` to `ORD1030` with statuses *Processing*, *Shipped*, *Out for delivery*, *Delivered*, *Cancelled* and *Returned*.

Edit the CSV files, then run `python seed_db.py` to load your changes.

### Security notes

- The **API key lives only in `backend/.env`**, which is git-ignored. The browser never sees it.
- The backend runs **only allowlisted functions** (`TOOL_FUNCTIONS`). The model cannot make it run anything else.
- Tool arguments are **validated** (JSON object, known argument names, sensible numbers), and SQL uses `?` placeholders.
- The app is **read-only**: no orders are placed, changed, cancelled or refunded.
- All data is **fictional**. Don't type real personal information into the chat.
- Model output can be wrong. That's why product, order and price facts come from tools, not from the model's memory.

### Where to go next

- Add more tools: product details, compare two products, list delivered orders.
- Add a `quantity` argument to `calculate_discount` to price several items.
- Read Groq's tool-use guide: <https://console.groq.com/docs/tool-use>.
