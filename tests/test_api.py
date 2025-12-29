import pytest


@pytest.mark.asyncio
async def test_create_user(client):
    response = await client.post("/users/", json={
        "telegram_id": 12345,
        "first_name": "Test",
        "last_name": "User"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["telegram_id"] == 12345
    assert data["first_name"] == "Test"

@pytest.mark.asyncio
async def test_add_score(client):
    await client.post("/users/", json={
        "telegram_id": 12345,
        "first_name": "Test",
        "last_name": "User"
    })

    response = await client.post("/scores/", json={
        "telegram_id": 12345,
        "subject": "Math",
        "score": 90
    })
    assert response.status_code == 200
    assert response.json()["score"] == 90

@pytest.mark.asyncio
async def test_get_scores(client):
    await client.post("/users/", json={"telegram_id": 12345, "first_name": "T", "last_name": "U"})
    await client.post("/scores/", json={"telegram_id": 12345, "subject": "Math", "score": 85})

    response = await client.get("/scores/12345")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["subject"] == "Math"
    assert data[0]["score"] == 85
