"""
run_prompts.py - send the workshop's test questions to the assistant and print
what happened (which tools ran, and the final answer). Run from backend/:

    python run_prompts.py

Uses the same settings as the server (.env). Each question is a separate
conversation. With the free Groq tier, this script pauses between questions
to stay under the rate limit.
"""
import json
import sys
import time

from app import config
from app.agent import available_tool_names, run_agent
from app.database import ensure_database
from app.llm_client import LLMError, model_label

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

TEST_PROMPTS = [
    ("Find wireless headphones under ₹3,000.", "calls search_products, lists matches with prices"),
    ("Where is my order ORD1024?", "calls check_order, says Shipped + delivery date"),
    ("Find the cheapest laptop under ₹50,000 and show its price after 10% off.",
     "search_products, then calculate_discount (Kito Student Laptop 14 -> ₹26,991)"),
    ("Where is order ORD9999?", "says the order was not found, no invented status"),
    ("Write me a poem about the moon.", "no tool; politely declines and redirects"),
    ("Who won the cricket match yesterday?", "no tool; politely declines and redirects"),
]

ensure_database()
print(f"Model: {model_label()}   Tools loaded: {available_tool_names() or 'none'}\n")

for i, (prompt, expected) in enumerate(TEST_PROMPTS, start=1):
    print("=" * 70)
    print(f"{i}. USER: {prompt}")
    print(f"   EXPECTED: {expected}")
    try:
        result = run_agent(prompt, history=[])
    except LLMError as e:
        print(f"   ERROR: {e}")
        continue
    for call in result["tool_calls"]:
        print(f"   TOOL  {call['name']}({json.dumps(call['arguments'], ensure_ascii=False)})")
    if not result["tool_calls"]:
        print("   TOOL  (none)")
    print(f"   ASSISTANT: {result['reply']}\n")
    if config.LLM_PROVIDER != "mock" and i < len(TEST_PROMPTS):
        time.sleep(12)  # stay under the free-tier tokens-per-minute limit
