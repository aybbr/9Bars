"""Tests for the read/state routes."""

from fastapi.testclient import TestClient


def test_onboard_and_list_coffees(client: TestClient) -> None:
    created = client.post("/api/coffee", json={"name": "Ethiopia", "roaster": "R"})

    assert created.status_code == 201
    assert created.json()["name"] == "Ethiopia"

    listed = client.get("/api/coffee").json()

    assert len(listed) == 1
    assert listed[0]["name"] == "Ethiopia"


def test_shots_for_unknown_coffee_is_empty(client: TestClient) -> None:
    assert client.get("/api/coffee/unknown/shots").json() == []


def test_latest_shot_for_unknown_coffee_returns_404(client: TestClient) -> None:
    assert client.get("/api/coffee/unknown/latest-shot").status_code == 404


def test_record_feedback(client: TestClient) -> None:
    response = client.post(
        "/api/feedback",
        json={
            "shot_id": "s1",
            "acidity": 4,
            "sweetness": 2,
            "body": 3,
            "overall": 3,
            "bitterness": 2,
            "aroma": 4,
            "finish": 3,
        },
    )

    assert response.status_code == 201
    assert response.json()["bitterness"] == 2
    assert response.json()["finish"] == 3


def test_get_feedback_for_shot(client: TestClient) -> None:
    client.post(
        "/api/feedback",
        json={"shot_id": "s2", "acidity": 3, "sweetness": 4, "body": 3, "overall": 4, "aroma": 5},
    )

    response = client.get("/api/shot/s2/feedback")

    assert response.status_code == 200
    assert response.json()["aroma"] == 5
    assert response.json()["bitterness"] == 3


def test_get_feedback_for_unknown_shot_returns_404(client: TestClient) -> None:
    assert client.get("/api/shot/nope/feedback").status_code == 404


def test_next_action_requires_shots(client: TestClient) -> None:
    response = client.post(
        "/api/next-action",
        json={"coffee_id": "unknown", "acidity": 5, "sweetness": 1, "body": 3, "overall": 3},
    )

    assert response.status_code == 404


def test_research_returns_offline_stub(client: TestClient) -> None:
    response = client.post("/api/coffee/research", json={"text": "Berlin roaster"})

    assert response.status_code == 200
    body = response.json()
    assert body["coffee"]["name"] == "Berlin roaster"
    assert body["evidence"] == []
