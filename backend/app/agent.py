"""
agent.py - the tool-calling loop. This is the heart of the app.

    1. Send the conversation + the tool schemas to the model.
    2. If the model answers with text -> done, return it.
    3. If the model asks for tools -> run each one (only allowlisted Python
       functions), add the results to the conversation, and go back to step 1.

The model never runs code or touches the database. It only *asks*; we decide
whether to run the tool, and we run it ourselves.
"""
import json

from app import config
from app.llm_client import get_llm
from app.masking import Masker
from app.prompts import SYSTEM_PROMPT

# Your tool registry. It brings in the functions (tools.py) and the
# schemas (tool_schemas.py) by itself.
from app import tool_registry as registry

MAX_TOOL_ROUNDS = 5   # safety limit: stop if the model keeps calling tools
MAX_HISTORY = 10      # how many earlier messages to send (keeps requests small)


def log(text: str) -> None:
    """Print to the server terminal (ASCII only, so no Windows console errors)."""
    for fancy, plain in {"₹": "Rs.", "‑": "-", "–": "-", "—": "-",
                         "‘": "'", "’": "'", "“": '"', "”": '"'}.items():
        text = text.replace(fancy, plain)
    print(text.encode("ascii", "replace").decode(), flush=True)


def available_tool_names() -> list[str]:
    return [schema["function"]["name"] for schema in registry.TOOLS]


def run_tool(name: str, arguments_json: str, masker: Masker | None = None) -> tuple[dict, dict]:
    """Run ONE tool the model asked for. Returns (arguments, result).

    Safety checks:
      - only names in TOOL_FUNCTIONS can run (an allowlist)
      - arguments must be a valid JSON object
      - any error becomes a result the model can read, instead of a crash
    """
    # 1. Allowlist: is this a tool we actually wrote?
    function = registry.TOOL_FUNCTIONS.get(name)
    if function is None:
        return {}, {"error": f"Unknown tool '{name}'. Available: {available_tool_names()}"}

    # 2. Parse the JSON arguments the model sent.
    try:
        arguments = json.loads(arguments_json or "{}")
    except json.JSONDecodeError:
        return {}, {"error": "Tool arguments were not valid JSON."}
    if not isinstance(arguments, dict):
        return {}, {"error": "Tool arguments must be a JSON object."}

    # The model only knows placeholders like [EMAIL_1]. Put the real values
    # back so the tool (which runs on OUR server) gets the real data.
    if masker:
        arguments = masker.unmask_value(arguments)

    # 3. Run the Python function.
    try:
        result = function(**arguments)
    except TypeError as e:          # wrong / unexpected argument names
        result = {"error": f"Invalid arguments for {name}: {e}"}
    except Exception as e:          # bug inside the tool - don't crash the server
        log(f"[tool] {name} crashed: {e!r}")
        result = {"error": f"The {name} tool failed. Please try again."}
    return arguments, result


def run_agent(user_message: str, history: list[dict]) -> dict:
    """Answer one user message. Returns {"reply": str, "tool_calls": [...]}."""
    llm = get_llm()

    # PII masking: one Masker per request. Everything we send to the model goes
    # through hide(); everything the model sends back to the user goes through
    # masker.clean_reply(). With MASK_PII=false both do nothing.
    masker = Masker() if config.MASK_PII else None

    def hide(text: str) -> str:
        return masker.mask(text) if masker else text

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages += [{**m, "content": hide(m["content"])} for m in history[-MAX_HISTORY:]]
    messages.append({"role": "user", "content": hide(user_message)})
    if masker and masker.to_real:
        log(f"[mask] model sees: {messages[-1]['content']}")

    trace = []  # every tool we ran, so the UI can show it

    for _ in range(MAX_TOOL_ROUNDS):
        turn = llm.chat(messages, tools=registry.TOOLS or None)

        # No tool requested -> this is the final answer.
        if not turn.tool_calls:
            reply = turn.content.strip() or "(no answer)"
            if masker:
                cleaned = masker.clean_reply(reply)   # output masking
                if cleaned != reply:
                    log(f"[mask] model wrote: {reply}")
                    log(f"[mask] user sees:   {cleaned}")
                reply = cleaned
            return {"reply": reply, "tool_calls": trace}

        # The model asked for tool(s). Record its request in the conversation...
        messages.append({
            "role": "assistant",
            "content": turn.content or "",
            "tool_calls": [
                {
                    "id": call.id,
                    "type": "function",
                    "function": {"name": call.name, "arguments": call.arguments},
                }
                for call in turn.tool_calls
            ],
        })

        # ...then run each tool and send back its result.
        for call in turn.tool_calls:
            log(f"[tool] model asked for {call.name}({call.arguments})")
            arguments, result = run_tool(call.name, call.arguments, masker)
            log(f"[tool] result: {json.dumps(result)[:300]}")
            trace.append({"name": call.name, "arguments": arguments, "result": result})
            messages.append({
                "role": "tool",
                "tool_call_id": call.id,
                "name": call.name,
                # Tool results can contain personal data too - mask before the model sees it.
                "content": hide(json.dumps(result)),
            })

    return {
        "reply": "Sorry, I couldn't finish that request. Please try asking in a simpler way.",
        "tool_calls": trace,
    }
