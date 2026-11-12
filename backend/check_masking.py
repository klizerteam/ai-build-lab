"""
check_masking.py - test PII masking (app/masking.py). No internet or key needed.
Run from backend/ with the venv active:

    python check_masking.py

Checks that:
  1. personal data is detected and hidden
  2. normal shop data (prices, dates, order IDs, products) is NEVER touched
  3. placeholders come back as the real values, even if the model copies them a bit wrong
  4. the full agent loop never sends real personal data to the model
"""
import csv
import json
import sys

from app import config
from app.masking import Masker

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
passed = failed = 0


def check(label: str, ok: bool, detail: str = "") -> None:
    global passed, failed
    if ok:
        passed += 1
        print(f"  PASS  {label}")
    else:
        failed += 1
        print(f"  FAIL  {label}   {detail}")


# ---------------------------------------------------------------------------
print("\n1. Personal data is hidden")
SENSITIVE = {
    "EMAIL":   ["asha@gmail.com", "ravi.kumar+shop@company.co.in"],
    "PHONE":   ["9876543210", "+91 98765 43210", "+91-9876543210", "098765 43210", "987-654-3210"],
    "CARD":    ["4111 1111 1111 1111", "4111-1111-1111-1111", "5555555555554444", "3782 822463 10005"],
    "AADHAAR": ["2345 6789 0123", "234567890123"],
    "PAN":     ["ABCDE1234F"],
    "UPI":     ["asha@okaxis", "ravi.k@ybl"],
    "API_KEY": ["gsk_abcdefghijklmnop1234", "sk-proj-ABCDEFGHIJKLMNOP1234"],
}
for kind, values in SENSITIVE.items():
    for value in values:
        m = Masker()
        out = m.mask(f"my details: {value}. thanks")
        check(f"{kind:8} {value}", value not in out and f"[{kind}_1]" in out, f"-> {out!r}")

# ---------------------------------------------------------------------------
print("\n2. Normal shop data is never touched")
SAFE = [
    "Where is my order ORD1024?", "Where is order ORD9999?", "ord 1024",
    "Find wireless headphones under ₹3,000.", "under 50000", "under 50k", "₹46,499", "₹1,23,456",
    "Find the cheapest laptop under ₹50,000 and show its price after 10% off.",
    "33% off 999", "Estimated delivery: 2026-10-16", "ordered 2026-10-12, arriving 2026-10-20",
    "2026-10-12 2026-10-20", "4.5 stars, 12 in stock", "65W USB-C charger", "1234567890123",
    "Option 1: phone 1 is cheaper than card 2", "Write me a poem about the moon.",
    "Who won the cricket match yesterday?", "price 26991.0", "total 4698",
]
data_dir = config.DATA_DIR
for name in ("products.csv", "orders.csv"):
    with open(data_dir / name, encoding="utf-8") as f:
        SAFE += [", ".join(row) for row in csv.reader(f)]
bad = []
for text in SAFE:
    m = Masker()
    if m.mask(text) != text or m.clean_reply(text) != text:
        bad.append(f"{text!r} -> {m.mask(text)!r}")
check(f"{len(SAFE)} normal texts (incl. every product + order row) unchanged", not bad, "; ".join(bad[:5]))

# ---------------------------------------------------------------------------
print("\n3. Placeholders turn back into real values")
m = Masker()
m.mask("email asha@gmail.com phone 9876543210 key gsk_abcdefghijklmnop1234")
VARIANTS = ["[EMAIL_1]", "[Email_1]", "[email_1]", "[EMAIL 1]", "[EMAIL-1]", "[EMAIL1]",
            "<EMAIL_1>", "{EMAIL_1}", "[ EMAIL_1 ]", r"\[EMAIL\_1\]", "EMAIL_1", r"EMAIL\_1",
            "**[EMAIL_1]**"]
for v in VARIANTS:
    out = m.clean_reply(f"We will write to {v}.")
    check(f"model writes {v:16} -> real email", "asha@gmail.com" in out and "EMAIL" not in out.upper(), out)
check("[API_KEY_1] / [API KEY 1] restored",
      m.unmask("[API_KEY_1] [API KEY 1]") == "gsk_abcdefghijklmnop1234 gsk_abcdefghijklmnop1234")
check("same value -> same placeholder", m.mask("asha@gmail.com") == "[EMAIL_1]")
out = m.clean_reply("Contact [EMAIL_7] for help.")
check("made-up placeholder [EMAIL_7] -> (hidden)", out == "Contact (hidden) for help.", out)
out = m.clean_reply("Call our support line at 9123456789 or mail help@shop.com.")
check("phone/email the model invented are redacted",
      "9123456789" not in out and "help@shop.com" not in out, out)
check("normal words 'phone 1', 'card 2' left alone",
      m.clean_reply("Phone 1 and card 2 are cheaper.") == "Phone 1 and card 2 are cheaper.")
check("tool arguments unmasked (dict/list)",
      m.unmask_value({"to": "[EMAIL_1]", "list": ["[PHONE_1]"], "n": 5})
      == {"to": "asha@gmail.com", "list": ["9876543210"], "n": 5})

# ---------------------------------------------------------------------------
print("\n4. Full agent loop: the model never sees real personal data")
config.MASK_PII = True
from app import agent  # noqa: E402
from app.llm_client import AssistantTurn, ToolCall  # noqa: E402

REAL = ["asha@gmail.com", "9876543210", "ravi@gmail.com", "9123456789", "4111 1111 1111 1111"]
original_tool = agent.registry.TOOL_FUNCTIONS.get("check_order")
agent.registry.TOOL_FUNCTIONS["check_order"] = lambda order_id, **_: {
    "order_id": order_id, "customer_email": "ravi@gmail.com", "phone": "9123456789"}
seen, tool_args = [], []


class SpyLLM:
    def chat(self, messages, tools):
        seen.append(json.dumps(messages, ensure_ascii=False))
        if len(seen) == 1:  # step 1: ask for a tool, using the placeholder
            return AssistantTurn("", [ToolCall("c1", "check_order", '{"order_id": "ORD1024", "note": "[EMAIL_1]"}')])
        # history phone = PHONE_1, user email = EMAIL_1, tool result = EMAIL_2 / PHONE_2
        return AssistantTurn("Order ORD1024 is for [EMAIL_2] ([PHONE_2]). Updates go to Email_1.")


agent.get_llm = lambda: SpyLLM()
old_run_tool = agent.run_tool


def spy_run_tool(name, arguments_json, masker=None):
    args, result = old_run_tool(name, arguments_json, masker)
    tool_args.append(args)
    return args, result


agent.run_tool = spy_run_tool
reply = agent.run_agent(
    "I'm asha@gmail.com, card 4111 1111 1111 1111, check ORD1024",
    [{"role": "user", "content": "hi, my number is 9876543210"}, {"role": "assistant", "content": "Hello!"}],
)["reply"]
leaks = [v for v in REAL if any(v in s for s in seen)]
check("no real personal data in ANY message sent to the model", not leaks, f"leaked: {leaks}")
check("tool received the real email (unmasked on our server)",
      tool_args and tool_args[0].get("note") == "asha@gmail.com", str(tool_args))
check("final reply has real values back",
      reply == "Order ORD1024 is for ravi@gmail.com (9123456789). Updates go to asha@gmail.com.", reply)
if original_tool:
    agent.registry.TOOL_FUNCTIONS["check_order"] = original_tool

print(f"\n{passed} passed, {failed} failed")
sys.exit(1 if failed else 0)
