from fastapi import FastAPI, HTTPException, Depends, Query, UploadFile, File
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.future import select
from datetime import datetime
from typing import List
import csv
import io

from model import Event, Attendee, EventStatus, Base

app = FastAPI()

# Database setup


DATABASE_URL = "sqlite+aiosqlite:///./test.db"
engine = create_async_engine(DATABASE_URL, echo=True)

SessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        print("✅ Database tables created successfully!")


@app.on_event("startup")
async def on_startup():
    await init_db()


async def get_db():
    async with SessionLocal() as session:
        yield session


class EventCreate(BaseModel):
    name: str
    description: str
    start_time: datetime
    end_time: datetime
    location: str
    max_attendees: int


class AttendeeCreate(BaseModel):
    first_name: str
    last_name: str
    email: str
    phone_number: str


@app.post("/events/", response_model=EventCreate)
async def create_event(event: EventCreate, db: AsyncSession = Depends(get_db)):
    db_event = Event(**event.dict())
    db.add(db_event)
    await db.commit()
    await db.refresh(db_event)
    return db_event


@app.put("/events/{event_id}", response_model=EventCreate)
async def update_event(event_id: int, event: EventCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Event).where(Event.event_id == event_id))
    db_event = result.scalars().first()

    if not db_event:
        raise HTTPException(status_code=404, detail="Event not found")

    for key, value in event.dict().items():
        setattr(db_event, key, value)

    await db.commit()
    await db.refresh(db_event)
    return db_event


@app.post("/attendees/{event_id}", response_model=AttendeeCreate)
async def register_attendee(event_id: int, attendee: AttendeeCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Event).where(Event.event_id == event_id))
    db_event = result.scalars().first()

    if not db_event:
        raise HTTPException(status_code=404, detail="Event not found")

    result = await db.execute(select(Attendee).where(Attendee.event_id == event_id))
    attendees_count = len(result.scalars().all())

    if attendees_count >= db_event.max_attendees:
        raise HTTPException(status_code=400, detail="Max attendees reached")

    db_attendee = Attendee(**attendee.dict(), event_id=event_id)
    db.add(db_attendee)
    await db.commit()
    await db.refresh(db_attendee)
    return db_attendee


@app.post("/attendees/{event_id}/check_in/{attendee_id}")
async def check_in_attendee(event_id: int, attendee_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Attendee).where(Attendee.attendee_id == attendee_id, Attendee.event_id == event_id))
    db_attendee = result.scalars().first()

    if not db_attendee:
        raise HTTPException(status_code=404, detail="Attendee not found")

    db_attendee.check_in_status = True
    await db.commit()
    return db_attendee


@app.get("/events/", response_model=List[EventCreate])
async def list_events(status: EventStatus = Query(None), location: str = Query(None),
                      db: AsyncSession = Depends(get_db)):
    query = select(Event)

    if status:
        query = query.where(Event.status == status)
    if location:
        query = query.where(Event.location == location)

    result = await db.execute(query)
    return result.scalars().all()


@app.get("/attendees/{event_id}", response_model=List[AttendeeCreate])
async def list_attendees(event_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Attendee).where(Attendee.event_id == event_id))
    return result.scalars().all()


@app.post("/attendees/bulk_check_in/")
async def bulk_check_in(file: UploadFile = File(...), db: AsyncSession = Depends(get_db)):
    contents = await file.read()
    attendees_data = io.StringIO(contents.decode("utf-8"))
    reader = csv.DictReader(attendees_data)

    for row in reader:
        attendee_id = int(row['attendee_id'])
        event_id = int(row['event_id'])

        result = await db.execute(
            select(Attendee).where(Attendee.attendee_id == attendee_id, Attendee.event_id == event_id))
        db_attendee = result.scalars().first()

        if db_attendee:
            db_attendee.check_in_status = True

    await db.commit()
    return {"message": "Bulk check-in completed"}
