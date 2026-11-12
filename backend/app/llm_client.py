"""
llm_client.py - talks to the LLM provider (Groq).

All provider-specific code lives in this one file. The rest of the app only
sees two simple objects: AssistantTurn and ToolCall.
"""
from dataclasses import dataclass, field

from app import config


@dataclass
class ToolCall:
    id: str            # provider's id for this call; we send it back with the result
    name: str          # which tool the model wants, e.g. "search_products"
    arguments: str     # the arguments as a JSON *string*, e.g. '{"max_price": 3000}'


@dataclass
class AssistantTurn:
    content: str                                         # text answer (may be empty)
    tool_calls: list[ToolCall] = field(default_factory=list)


class LLMError(Exception):
    """A problem talking to the model. The message is safe to show to the user."""


class GroqLLM:
    def __init__(self) -> None:
        if not config.api_key_is_set():
            raise LLMError(
                "GROQ_API_KEY is missing. Add your key to backend/.env and restart "
                "the server (or set LLM_PROVIDER=mock to try the offline mock)."
            )
        from groq import Groq  # imported here so mock mode works without a key

        self.model = config.GROQ_MODEL
        self.client = Groq(api_key=config.GROQ_API_KEY, max_retries=2, timeout=60)

    def chat(self, messages: list[dict], tools: list[dict] | None) -> AssistantTurn:
        import groq

        request = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.2,
            "max_tokens": 1024,
        }
        if tools:
            request["tools"] = tools
            request["tool_choice"] = "auto"
        if self.model.startswith("openai/gpt-oss"):
            # Spend fewer tokens "thinking" - keeps us inside free-tier limits.
            request["extra_body"] = {"reasoning_effort": "low"}

        # Sometimes the model writes a badly formatted tool call and Groq
        # rejects it with "tool_use_failed". Trying again usually fixes it.
        for attempt in range(3):
            try:
                response = self.client.chat.completions.create(**request)
                break
            except groq.BadRequestError as e:
                if "tool_use_failed" in str(e) and attempt < 2:
                    print("[llm] model produced an invalid tool call - retrying")
                    request["temperature"] = 0.6
                    continue
                raise LLMError(f"The model rejected the request: {_short(e)}") from e
            except groq.AuthenticationError as e:
                raise LLMError("Groq rejected the API key. Check GROQ_API_KEY in backend/.env.") from e
            except groq.RateLimitError as e:
                raise LLMError("Groq free-tier rate limit reached. Wait about a minute and try again.") from e
            except groq.NotFoundError as e:
                raise LLMError(f"Model '{self.model}' was not found. Check GROQ_MODEL in backend/.env.") from e
            except groq.APIConnectionError as e:
                raise LLMError("Could not reach Groq. Check your internet connection.") from e
            except groq.APIError as e:
                raise LLMError(f"Groq returned an error: {_short(e)}") from e

        message = response.choices[0].message
        tool_calls = [
            ToolCall(id=tc.id, name=tc.function.name, arguments=tc.function.arguments or "{}")
            for tc in (message.tool_calls or [])
        ]
        return AssistantTurn(content=message.content or "", tool_calls=tool_calls)


def _short(error: Exception, limit: int = 300) -> str:
    text = str(error)
    return text if len(text) <= limit else text[:limit] + "..."


def get_llm():
    """Return the configured LLM client (Groq, or the offline mock)."""
    if config.LLM_PROVIDER == "mock":
        from app.mock_llm import MockLLM
        return MockLLM()
    return GroqLLM()


def model_label() -> str:
    return "mock (offline)" if config.LLM_PROVIDER == "mock" else config.GROQ_MODEL
