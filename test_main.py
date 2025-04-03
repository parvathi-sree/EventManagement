import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from main import app, get_db
from model import Base
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
import asyncio


DATABASE_URL = "sqlite+aiosqlite:///./test.db"
engine = create_async_engine(DATABASE_URL, echo=False)
TestingSessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)


async def override_get_db():
    async with TestingSessionLocal() as session:
        yield session


app.dependency_overrides[get_db] = override_get_db


@pytest_asyncio.fixture(scope="session")
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.mark.asyncio
async def test_create_event(client):
    event_data = {
        "name": "TechFest",
        "description": "Annual Tech Event",
        "start_time": "2025-06-15T09:00:00",
        "end_time": "2025-06-15T17:00:00",
        "location": "cochin",
        "max_attendees": 100
    }
    response = await client.post("/events/", json=event_data)
    assert response.status_code == 200
    assert response.json()["name"] == "TechFest"


@pytest.mark.asyncio
async def test_update_event(client):
    event_data = {
        "name": "Updated TechFest",
        "description": "Updated Description",
        "start_time": "2025-06-16T10:00:00",
        "end_time": "2025-06-16T18:00:00",
        "location": "cochin",
        "max_attendees": 150
    }
    response = await client.put("/events/1", json=event_data)
    assert response.status_code == 200
    assert response.json()["name"] == "Updated TechFest"


@pytest.mark.asyncio
async def test_register_attendee(client):
    attendee_data = {
        "first_name": "parvathi",
        "last_name": "k",
        "email": "parvathi@gmail.com",
        "phone_number": "1234567890"
    }
    response = await client.post("/attendees/1", json=attendee_data)
    assert response.status_code == 200
    assert response.json()["email"] == "parvathi@gmail.com"


@pytest.mark.asyncio
async def test_check_in_attendee(client):
    response = await client.post("/attendees/1/check_in/1")
    assert response.status_code == 200
    assert response.json()["check_in_status"] is True


@pytest.mark.asyncio
async def test_list_events(client):
    response = await client.get("/events/")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_list_attendees(client):
    response = await client.get("/attendees/1")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_bulk_check_in(client):
    csv_data = "attendee_id,event_id\n1,1\n2,1\n"
    files = {"file": ("attendees.csv", csv_data, "text/csv")}
    response = await client.post("/attendees/bulk_check_in/", files=files)
    assert response.status_code == 200
    assert response.json()["message"] == "Bulk check-in completed"
