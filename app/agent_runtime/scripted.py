"""A deterministic stand-in for the LLM, for end-to-end tests and offline demos (``LLM_PROVIDER=scripted``).

It is rule based, not intelligent: it understands "sell 2 shirt to Ali" (and the Roman Urdu "2 shirt bech do Ali ko"),
"yes" / "haan", "today" sales, and nothing else. What it does is drive the REAL tools and the REAL approval flow with
predictable model turns, so a browser test can prove the whole path (chat, draft, approval, stock, trace) with no network
and no API key. It refuses to load in production.
"""

from __future__ import annotations

import json
import re
import uuid
from collections.abc import AsyncIterator
from typing import Any

from agents import Model, ModelResponse
from agents.usage import Usage
from openai.types.responses import ResponseFunctionToolCall, ResponseOutputMessage, ResponseOutputText

# "sell 2 shirt to Ali", "2 shirt bech do Ali ko", "1 jeans Ali ko udhaar pe"; the last word before "ko" is the customer
_FORMS = (
    re.compile(r"^(?:sell\s+)?(?P<qty>\d+)\s+(?P<product>.+?)\s+(?:to|for)\s+(?P<customer>[a-z][a-z0-9 .]*?)(?:\s+(?:on\s+)?(?:udhaar|credit))?$"),
    re.compile(r"^(?P<qty>\d+)\s+(?P<product>.+?)\s+(?:bech\s+do|becho)\s+(?P<customer>[a-z][a-z0-9 .]*?)\s+ko(?:\s+udhaar(?:\s+pe)?)?$"),
    re.compile(r"^(?P<qty>\d+)\s+(?P<product>.+?)\s+(?P<customer>[a-z][a-z0-9]*)\s+ko(?:\s+udhaar(?:\s+pe)?)?$"),
    re.compile(r"^(?:sell\s+)?(?P<qty>\d+)\s+(?P<product>.+?)(?:\s+(?:bech\s+do|becho))?(?:\s+(?:on\s+)?(?:udhaar|credit)(?:\s+pe)?)?$"),
)
_YES = re.compile(r"^(yes|y|haan|han|ok|okay|post it|confirm)\b")
_ID = re.compile(r"id=([0-9a-f]{8}-[0-9a-f-]{27})")


def _items(raw: Any) -> list[dict[str, Any]]:
    if isinstance(raw, str):
        return [{"role": "user", "content": raw}]
    return [i if isinstance(i, dict) else getattr(i, "__dict__", {}) for i in raw]


def _text_of(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return " ".join(str(p.get("text", "")) for p in content if isinstance(p, dict))
    return ""


def _call(name: str, arguments: dict[str, Any]) -> list[Any]:
    return [
        ResponseFunctionToolCall(
            type="function_call", call_id=f"call_{uuid.uuid4().hex[:12]}", name=name, arguments=json.dumps(arguments)
        )
    ]


def _say(text: str) -> list[Any]:
    return [
        ResponseOutputMessage(
            id=f"msg_{uuid.uuid4().hex[:12]}",
            type="message",
            role="assistant",
            status="completed",
            content=[ResponseOutputText(type="output_text", text=text, annotations=[])],
        )
    ]


class ScriptedModel(Model):
    async def get_response(self, *args: Any, **kwargs: Any) -> ModelResponse:
        raw = kwargs.get("input", args[1] if len(args) > 1 else "")
        return ModelResponse(output=self._next(_items(raw)), usage=Usage(requests=1, input_tokens=120, output_tokens=40), response_id="scripted")

    def stream_response(self, *args: Any, **kwargs: Any) -> AsyncIterator[Any]:
        raise NotImplementedError("the scripted model is not streamed")

    # -- the rules ---------------------------------------------------------------------------------------------

    def _next(self, items: list[dict[str, Any]]) -> list[Any]:
        last_user = max((i for i, it in enumerate(items) if it.get("role") == "user"), default=-1)
        text = _text_of(items[last_user].get("content")).strip().lower() if last_user >= 0 else ""
        since = items[last_user + 1 :]
        calls = [it for it in since if it.get("type") == "function_call"]
        outputs = {it.get("call_id"): str(it.get("output", "")) for it in since if it.get("type") == "function_call_output"}
        done = [(c.get("name"), outputs.get(c.get("call_id"), "")) for c in calls]

        if _YES.match(text):
            return self._confirm(items[: last_user + 1], done)
        if "today" in text or "aaj" in text:
            return _say(done[-1][1]) if done else _call("get_sales_summary", {"period": "today"})
        sell = next((m for form in _FORMS if (m := form.match(text))), None)
        if sell:
            return self._sell(text, sell, done)
        return _say("I can record sales for you. Try: sell 2 shirt to Ali, or ask for today's sales.")

    def _sell(self, text: str, sell: re.Match[str], done: list[tuple[Any, str]]) -> list[Any]:
        parts = sell.groupdict()
        qty, product, customer = int(parts["qty"]), parts["product"].strip(), (parts.get("customer") or "").strip()
        names = [n for n, _ in done]
        if "find_product" not in names:
            return _call("find_product", {"query": product})
        if customer and "find_customer" not in names:
            return _call("find_customer", {"query": customer})
        if "draft_order" not in names:
            found = dict(done).get("find_product", "")
            product_id = _ID.search(found)
            if not product_id:
                return _say(f"I could not find '{product}' in your products.")
            customer_id = None
            if customer:
                cid = _ID.search(dict(done).get("find_customer", ""))
                if not cid:
                    return _say(f"I could not find a customer called '{customer}'.")
                customer_id = cid.group(1)
            on_credit = "udhaar" in text or "credit" in text
            return _call(
                "draft_order",
                {
                    "items": [{"product_id": product_id.group(1), "qty": qty, "unit_price": None}],
                    "customer_id": customer_id,
                    "payment_method": "udhaar" if on_credit else "cash",
                    "amount_paid": None,
                    "discount": None,
                },
            )
        return _say(f"{dict(done)['draft_order']} Post it?")

    def _confirm(self, history: list[dict[str, Any]], done: list[tuple[Any, str]]) -> list[Any]:
        drafts = [it for it in history if it.get("type") == "function_call" and it.get("name") == "draft_order"]
        if not drafts:
            return _say("There is nothing waiting to be posted. Tell me what to sell first.")
        if "post_order" not in [n for n, _ in done]:
            return _call("post_order", json.loads(drafts[-1].get("arguments", "{}")))
        return _say(dict(done)["post_order"])


__all__ = ["ScriptedModel"]
