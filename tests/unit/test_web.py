"""Tests for the web-UI backing routes (offline/demo mode, no live API)."""

from fastapi.testclient import TestClient

from nine_bars.fixtures.generate import DEMO_COFFEE_ID


def test_demo_load_ingests_fixture_shots(client: TestClient) -> None:
    response = client.post("/api/demo/load")

    assert response.status_code == 200
    assert response.json()["coffee_id"] == DEMO_COFFEE_ID
    assert response.json()["shots"] == ["1042", "1043"]


def test_shot_telemetry_returns_curves(client: TestClient) -> None:
    client.post("/api/demo/load")

    response = client.get("/api/shot/1042/telemetry")

    assert response.status_code == 200
    body = response.json()
    assert body["shot_id"] == "1042"
    assert len(body["pressure"]) > 20
    assert len(body["flow"]) == len(body["pressure"])


def test_shot_telemetry_unknown_returns_404(client: TestClient) -> None:
    assert client.get("/api/shot/nope/telemetry").status_code == 404


def test_scripted_chat_streams_tools_and_fills_activity(client: TestClient) -> None:
    response = client.post("/api/agent/chat", json={"prompt": "Run the demo"})

    assert response.status_code == 200
    body = response.text
    assert "tool_start" in body
    assert '"done"' in body

    activity = client.get("/api/agent/activity").json()
    assert activity["mode"] == "demo"
    assert len(activity["spans"]) >= 8
    assert {span["tool_name"] for span in activity["spans"]} >= {
        "research_coffee",
        "analyze_shot",
        "propose_next_action",
    }


def test_chat_rejects_empty_prompt(client: TestClient) -> None:
    assert client.post("/api/agent/chat", json={"prompt": "   "}).status_code == 400
