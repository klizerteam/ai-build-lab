"""
mock_llm.py - a FAKE model for when the internet or Groq is down.

Turn it on with LLM_PROVIDER=mock in backend/.env. It uses simple keyword
rules (no AI) to pretend to be the model: it asks for the same tools a real
model would, so you can still build and test your tools offline.
It only understands the workshop's example questions, so don't expect magic.
"""
import json
import re
import uuid

from app.llm_client import AssistantTurn, ToolCall

CATEGORY_WORDS = {
    "headphones": ["headphone", "earbud", "earphone", "neckband"],
    "laptops": ["laptop", "notebook"],
    "smartphones": ["phone", "mobile"],
    "smartwatches": ["watch"],
    "speakers": ["speaker", "soundbar"],
    "accessories": ["mouse", "keyboard", "charger", "power bank", "backpack", "webcam"],
}
FEATURE_WORDS = ["wireless", "wired", "gaming", "bluetooth", "noise-cancelling", "5g",
                 "mechanical", "portable", "budget", "premium", "amoled"]


def _price(text: str) -> float | None:
    """'under ₹3,000' -> 3000, '50k' -> 50000."""
    m = re.search(r"(?:under|below|less than|within|upto|up to|max)\s*(?:rs\.?|inr|₹)?\s*([\d,]+(?:\.\d+)?)\s*(k)?", text)
    if not m:
        return None
    value = float(m.group(1).replace(",", ""))
    return value * 1000 if m.group(2) else value


def _percent(text: str) -> float | None:
    m = re.search(r"(\d+(?:\.\d+)?)\s*(?:%|percent)", text)
    return float(m.group(1)) if m else None


def _rupees(value) -> str:
    return f"₹{value:,.2f}".replace(".00", "")


class MockLLM:
    model = "mock"

    def chat(self, messages: list[dict], tools: list[dict] | None) -> AssistantTurn:
        available = {t["function"]["name"] for t in (tools or [])}

        # Find the latest user message and any tool results that came after it.
        last_user = max(i for i, m in enumerate(messages) if m["role"] == "user")
        text = messages[last_user]["content"].lower()
        results = {}
        for m in messages[last_user + 1:]:
            if m["role"] == "tool":
                results[m["name"]] = json.loads(m["content"])

        if not results:
            return self._first_step(text, available)
        return self._after_tools(text, available, results)

    # ---- step 1: decide which tool to call -------------------------------
    def _first_step(self, text: str, available: set) -> AssistantTurn:
        order = re.search(r"\bord\s*-?\s*\d+\b", text)
        category = next((c for c, words in CATEGORY_WORDS.items() if any(w in text for w in words)), None)
        percent = _percent(text)

        if order:
            order_id = re.sub(r"[\s-]", "", order.group(0)).upper()
            return self._call("check_order", {"order_id": order_id}, available)

        if category:
            args = {"category": category}
            keywords = [w for w in FEATURE_WORDS if w in text]
            if keywords:
                args["query"] = " ".join(keywords[:2])
            if _price(text) is not None:
                args["max_price"] = _price(text)
            return self._call("search_products", args, available)

        without_percent = re.sub(r"\d+(?:\.\d+)?\s*(?:%|percent)", "", text)
        numbers = [float(n.replace(",", "")) for n in re.findall(r"\d[\d,]*(?:\.\d+)?", without_percent)]
        if percent is not None and numbers:
            return self._call("calculate_discount", {"price": max(numbers), "discount_percent": percent}, available)

        if re.search(r"\b(hi|hello|hey|namaste)\b", text):
            return AssistantTurn("Hi! I'm ShopBot (mock mode). Ask me to find a product, "
                                 "check an order like ORD1024, or calculate a discount.")

        return AssistantTurn("Sorry, I can only help with Demo Bazaar products, orders and discounts. "
                             "For example, try: \"Find wireless headphones under ₹3,000.\"")

    def _call(self, name: str, args: dict, available: set) -> AssistantTurn:
        if name not in available:
            return AssistantTurn(f"Sorry, I can't do that yet - the {name} tool hasn't been added.")
        call = ToolCall(id=f"call_{uuid.uuid4().hex[:8]}", name=name, arguments=json.dumps(args))
        return AssistantTurn(content="", tool_calls=[call])

    # ---- step 2: write an answer from the tool results ---------------------
    def _after_tools(self, text: str, available: set, results: dict) -> AssistantTurn:
        for result in results.values():
            if "error" in result:
                return AssistantTurn(f"Sorry, something went wrong: {result['error']}")

        search = results.get("search_products")
        discount = results.get("calculate_discount")
        order = results.get("check_order")

        # Chained request: search done, discount asked for but not calculated yet.
        percent = _percent(text)
        if search and search["count"] and percent is not None and not discount:
            cheapest = search["products"][0]
            return self._call("calculate_discount",
                              {"price": cheapest["price"], "discount_percent": percent}, available)

        if order:
            if not order["found"]:
                return AssistantTurn(f"I couldn't find an order with ID {order['order_id']}. "
                                     "Please check the ID and try again.")
            reply = f"Order {order['order_id']} ({order['items']}) is **{order['status']}**."
            if order["estimated_delivery"]:
                reply += f" Estimated delivery: {order['estimated_delivery']}."
            return AssistantTurn(reply)

        if discount:
            reply = ""
            if search:
                reply = f"The cheapest match is **{search['products'][0]['name']}**. "
            reply += (f"Original price {_rupees(discount['original_price'])}, "
                      f"{discount['discount_percent']:g}% off saves {_rupees(discount['discount_amount'])}, "
                      f"so the final price is **{_rupees(discount['final_price'])}**.")
            return AssistantTurn(reply)

        if search:
            if not search["count"]:
                return AssistantTurn("I couldn't find any matching products. "
                                     "Try fewer keywords or a higher budget.")
            lines = [f"- {p['name']} - {_rupees(p['price'])}"
                     + ("" if p["in_stock"] else " (out of stock)")
                     for p in search["products"]]
            return AssistantTurn("Here's what I found:\n" + "\n".join(lines))

        return AssistantTurn("Done.")
