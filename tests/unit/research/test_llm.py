"""Tests for the DeepSeek chat model client (mocked transport, no network)."""

import asyncio
import json

import httpx

from nine_bars.research.llm import ChatModel, DeepSeekChatModel


def test_deepseek_complete_sends_openai_compatible_request() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url) == "https://api.deepseek.com/chat/completions"
        assert request.headers["authorization"] == "Bearer test-key"
        body = json.loads(request.content)
        assert body["model"] == "deepseek-flash"
        assert body["stream"] is False
        assert body["messages"] == [{"role": "user", "content": "hello"}]
        return httpx.Response(200, json={"choices": [{"message": {"content": "hi back"}}]})

    model = DeepSeekChatModel(api_key="test-key", transport=httpx.MockTransport(handler))

    assert asyncio.run(model.complete("hello")) == "hi back"


def test_deepseek_complete_handles_empty_choices() -> None:
    model = DeepSeekChatModel(
        api_key="k",
        transport=httpx.MockTransport(lambda request: httpx.Response(200, json={"choices": []})),
    )

    assert asyncio.run(model.complete("x")) == ""


def test_deepseek_model_satisfies_chat_model_protocol() -> None:
    model = DeepSeekChatModel(api_key="k", transport=httpx.MockTransport(lambda r: httpx.Response(200, json={})))

    assert isinstance(model, ChatModel)
