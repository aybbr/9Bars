"""DeepSeek chat model client (OpenAI-compatible) for coffee research."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

import httpx


@runtime_checkable
class ChatModel(Protocol):
    """A minimal chat-completion seam satisfied by any OpenAI-compatible API."""

    async def complete(self, prompt: str) -> str: ...


class DeepSeekChatModel:
    """Calls DeepSeek's OpenAI-compatible ``/chat/completions`` endpoint via httpx."""

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.deepseek.com",
        model: str = "deepseek-flash",
        timeout: float = 20.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._timeout = timeout
        self._transport = transport

    async def complete(self, prompt: str) -> str:
        """Return the assistant text for ``prompt`` (single non-streaming turn)."""
        async with httpx.AsyncClient(timeout=self._timeout, transport=self._transport) as client:
            response = await client.post(
                f"{self._base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self._api_key}"},
                json={
                    "model": self._model,
                    "messages": [{"role": "user", "content": prompt}],
                    "stream": False,
                },
            )
            response.raise_for_status()
            payload: dict[str, Any] = response.json()
            return _first_message(payload)


def _first_message(payload: dict[str, Any]) -> str:
    choices = payload.get("choices") or []
    if not choices:
        return ""
    message = choices[0].get("message") or {}
    content = message.get("content")
    return content if isinstance(content, str) else ""
