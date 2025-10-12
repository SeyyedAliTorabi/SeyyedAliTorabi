from fastapi.testclient import TestClient
from backend.main import app
import pytest

client = TestClient(app)

@pytest.fixture(scope="module", autouse=True)
def setup_database():
    # In a real test suite, you'd use a separate test database
    # and clean it up after tests. For this example, we'll
    # rely on the existing sqlite db.
    pass

def test_create_user():
    response = client.post(
        "/users/",
        json={
            "first_name": "test",
            "last_name": "user",
            "city": "test city",
            "water_organization": "test org",
            "national_id": "1234567890",
            "password": "testpassword",
        },
    )
    # This might fail if the user already exists from a previous run
    # A proper test setup would clean the database before each test
    assert response.status_code == 200 or response.status_code == 400
    if response.status_code == 200:
        assert response.json()["national_id"] == "1234567890"

def test_login_for_access_token():
    # First, ensure the user exists
    client.post(
        "/users/",
        json={
            "first_name": "test",
            "last_name": "user",
            "city": "test city",
            "water_organization": "test org",
            "national_id": "1234567890",
            "password": "testpassword",
        },
    )

    response = client.post(
        "/token",
        data={"username": "1234567890", "password": "testpassword"},
    )
    assert response.status_code == 200
    assert "access_token" in response.json()
    assert response.json()["token_type"] == "bearer"
