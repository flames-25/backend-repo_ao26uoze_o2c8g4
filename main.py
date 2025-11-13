import os
from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from database import db, create_document, get_documents
from schemas import Driver, Device, HealthRecord, SleepRecord, Event, User

app = FastAPI(title="Smart Wearable Platform API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {"message": "Smart Wearable Platform API running"}

# ------------------------- Auth (basic demo) -------------------------
class LoginRequest(BaseModel):
    email: str
    password: str

class LoginResponse(BaseModel):
    token: str
    name: str
    role: str

@app.post("/auth/login", response_model=LoginResponse)
def login(req: LoginRequest):
    # Demo login: accept any email/password, issue a fake token
    # In real scenario, validate against User collection with password hashing
    name = req.email.split("@")[0].title()
    return LoginResponse(token="demo-token", name=name, role="admin")

# ------------------------- Helpers -------------------------

def to_collection(name: str) -> str:
    return name.lower()

# ------------------------- Seed/Test Data -------------------------

@app.post("/seed")
def seed():
    """Seed minimal demo data if collections are empty."""
    # Create a couple drivers/devices
    if len(get_documents(to_collection("driver"))) == 0:
        d1 = Driver(name="Budi Santoso", employee_id="DRV001", phone="081234567890")
        d2 = Driver(name="Siti Aminah", employee_id="DRV002", phone="081298765432")
        create_document(to_collection("driver"), d1)
        create_document(to_collection("driver"), d2)

    if len(get_documents(to_collection("device"))) == 0:
        dev1 = Device(device_id="DEV-1001", driver_name="Budi Santoso", is_online=True, battery=87,
                      last_location={"lat": -6.2, "lng": 106.82, "address": "Jakarta"})
        dev2 = Device(device_id="DEV-1002", driver_name="Siti Aminah", is_online=False, battery=22,
                      last_location={"lat": -6.21, "lng": 106.85, "address": "Jakarta"})
        create_document(to_collection("device"), dev1)
        create_document(to_collection("device"), dev2)

    # Health records (latest)
    today = datetime.utcnow()
    if len(get_documents(to_collection("healthrecord"))) == 0:
        hr1 = HealthRecord(
            driver_id="DRV001", driver_name="Budi Santoso", device_id="DEV-1001", timestamp=today,
            heart_rate=78, bp_systolic=145, bp_diastolic=95, temperature=36.8, calories=1200,
            steps=9500, duration_minutes=75, kilometers=6.8
        )
        hr2 = HealthRecord(
            driver_id="DRV002", driver_name="Siti Aminah", device_id="DEV-1002", timestamp=today,
            heart_rate=82, bp_systolic=118, bp_diastolic=78, temperature=36.6, calories=980,
            steps=7200, duration_minutes=60, kilometers=4.9
        )
        create_document(to_collection("healthrecord"), hr1)
        create_document(to_collection("healthrecord"), hr2)

    # Sleep per day
    if len(get_documents(to_collection("sleeprecord"))) == 0:
        s1 = SleepRecord(
            driver_id="DRV001", driver_name="Budi Santoso", device_id="DEV-1001", date=today.strftime("%Y-%m-%d"),
            score=58, duration_minutes=320, segments=[
                {"start": today - timedelta(hours=7), "end": today - timedelta(hours=6, minutes=45), "type": "light"},
                {"start": today - timedelta(hours=6, minutes=45), "end": today - timedelta(hours=5), "type": "deep"},
                {"start": today - timedelta(hours=5), "end": today - timedelta(hours=4, minutes=30), "type": "rem"},
                {"start": today - timedelta(hours=4, minutes=30), "end": today - timedelta(hours=4, minutes=15), "type": "awake"}
            ]
        )
        s2 = SleepRecord(
            driver_id="DRV002", driver_name="Siti Aminah", device_id="DEV-1002", date=today.strftime("%Y-%m-%d"),
            score=82, duration_minutes=420, segments=[
                {"start": today - timedelta(hours=8), "end": today - timedelta(hours=6), "type": "deep"},
                {"start": today - timedelta(hours=6), "end": today - timedelta(hours=5), "type": "light"},
                {"start": today - timedelta(hours=5), "end": today - timedelta(hours=4), "type": "rem"}
            ]
        )
        create_document(to_collection("sleeprecord"), s1)
        create_document(to_collection("sleeprecord"), s2)

    # Events
    if len(get_documents(to_collection("event"))) == 0:
        e1 = Event(driver_id="DRV001", driver_name="Budi Santoso", device_id="DEV-1001", timestamp=today,
                   status_event="Low Battery", location={"lat": -6.2, "lng": 106.82, "address": "Jakarta"})
        e2 = Event(driver_id="DRV002", driver_name="Siti Aminah", device_id="DEV-1002", timestamp=today,
                   status_event="SOS", location={"lat": -6.21, "lng": 106.85, "address": "Jakarta"})
        create_document(to_collection("event"), e1)
        create_document(to_collection("event"), e2)

    return {"status": "ok"}

# ------------------------- Dashboard Endpoints -------------------------

class DashboardSummary(BaseModel):
    high_bp_count: int
    low_sleep_score_count: int
    under_sleep_duration_count: int
    online_devices: int
    offline_devices: int

@app.get("/dashboard/summary", response_model=DashboardSummary)
def dashboard_summary(
    bp_sys_threshold: int = Query(140, description="Systolic threshold"),
    bp_dia_threshold: int = Query(90, description="Diastolic threshold"),
    sleep_score_threshold: int = Query(60),
    sleep_duration_threshold: int = Query(360)  # minutes
):
    today = datetime.utcnow().strftime("%Y-%m-%d")

    health = get_documents(to_collection("healthrecord"))
    sleep = get_documents(to_collection("sleeprecord"), {"date": today})
    devices = get_documents(to_collection("device"))

    high_bp = [h for h in health if h.get("bp_systolic", 0) > bp_sys_threshold or h.get("bp_diastolic", 0) > bp_dia_threshold]
    low_sleep_score = [s for s in sleep if s.get("score", 0) < sleep_score_threshold]
    under_sleep = [s for s in sleep if s.get("duration_minutes", 0) < sleep_duration_threshold]
    online = [d for d in devices if d.get("is_online")]
    offline = [d for d in devices if not d.get("is_online")]

    return DashboardSummary(
        high_bp_count=len(high_bp),
        low_sleep_score_count=len(low_sleep_score),
        under_sleep_duration_count=len(under_sleep),
        online_devices=len(online),
        offline_devices=len(offline),
    )

# Table A: Driver daily readiness
class DriverReadiness(BaseModel):
    datetime: datetime
    driver_name: str
    device_id: str
    last_sleep_score: int
    last_bp_systolic: int
    last_bp_diastolic: int
    status: str  # approved or not approved

@app.get("/dashboard/readiness")
def driver_readiness(q: Optional[str] = None, status: Optional[str] = None):
    health = get_documents(to_collection("healthrecord"))
    sleep = get_documents(to_collection("sleeprecord"))
    sleep_by_driver = {}
    for s in sleep:
        sleep_by_driver[s["driver_id"]] = s
    rows = []
    for h in health:
        s = sleep_by_driver.get(h["driver_id"]) or {}
        readiness_ok = h.get("bp_systolic",0) < 140 and h.get("bp_diastolic",0) < 90 and s.get("score",100) >= 60
        row = {
            "datetime": h.get("timestamp"),
            "driver_name": h.get("driver_name"),
            "device_id": h.get("device_id"),
            "last_sleep_score": s.get("score"),
            "last_bp_systolic": h.get("bp_systolic"),
            "last_bp_diastolic": h.get("bp_diastolic"),
            "status": "approved" if readiness_ok else "not approved"
        }
        rows.append(row)

    if q:
        rows = [r for r in rows if q.lower() in (r["driver_name"] or "").lower()]
    if status:
        rows = [r for r in rows if r["status"].lower() == status.lower()]

    return {"items": rows}

# Table B: Event summary
@app.get("/dashboard/events")
def events_table(q: Optional[str] = None, status_event: Optional[str] = None):
    events = get_documents(to_collection("event"))
    rows = []
    for e in events:
        rows.append({
            "datetime": e.get("timestamp"),
            "driver_name": e.get("driver_name"),
            "device_id": e.get("device_id"),
            "status_event": e.get("status_event"),
            "address": (e.get("location") or {}).get("address")
        })
    if q:
        rows = [r for r in rows if q.lower() in (r["driver_name"] or "").lower()]
    if status_event:
        rows = [r for r in rows if r["status_event"].lower() == status_event.lower()]
    return {"items": rows}

# Map view points
@app.get("/dashboard/map")
def map_points():
    devices = get_documents(to_collection("device"))
    health = get_documents(to_collection("healthrecord"))
    events = get_documents(to_collection("event"))
    health_by_device = {h["device_id"]: h for h in health}
    latest_event_by_device = {}
    for e in events:
        latest_event_by_device[e["device_id"]] = e

    points = []
    for d in devices:
        loc = d.get("last_location") or {}
        h = health_by_device.get(d.get("device_id")) or {}
        ev = latest_event_by_device.get(d.get("device_id")) or {}
        points.append({
            "device_id": d.get("device_id"),
            "driver_name": d.get("driver_name"),
            "battery": d.get("battery"),
            "event": ev.get("status_event"),
            "address": loc.get("address"),
            "lat": loc.get("lat"),
            "lng": loc.get("lng"),
        })
    return {"items": points}

# ------------------------- Devices -------------------------

@app.get("/devices")
def devices_list(q: Optional[str] = None):
    devices = get_documents(to_collection("device"))
    if q:
        devices = [d for d in devices if q.lower() in (d.get("device_id", "")+" "+(d.get("driver_name","") or "")).lower()]
    # Add simple id
    for i, d in enumerate(devices, start=1):
        d["no"] = i
    return {"items": devices}

@app.get("/devices/{device_id}")
def device_detail(device_id: str):
    devices = get_documents(to_collection("device"), {"device_id": device_id})
    if not devices:
        raise HTTPException(status_code=404, detail="Device not found")
    device = devices[0]
    health = get_documents(to_collection("healthrecord"), {"device_id": device_id})
    health = health[0] if health else None
    sleep_today = get_documents(to_collection("sleeprecord"), {"device_id": device_id})
    events = get_documents(to_collection("event"), {"device_id": device_id})
    return {"device": device, "health": health, "sleep": sleep_today, "events": events}

# Sleep history list by device + date filters
@app.get("/devices/{device_id}/sleep")
def device_sleep(device_id: str, date: Optional[str] = None):
    filt = {"device_id": device_id}
    if date:
        filt["date"] = date
    items = get_documents(to_collection("sleeprecord"), filt)
    return {"items": items}

# ECG streaming simulation (returns small wave array)
@app.get("/devices/{device_id}/ecg")
def device_ecg(device_id: str):
    # Simple synthetic waveform
    import math
    now = datetime.utcnow()
    points = [int(50 + 30 * math.sin(i/6.0) + 10 * math.sin(i/1.3)) for i in range(60)]
    return {"timestamp": now.isoformat(), "samples": points}

# ------------------------- System -------------------------

@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }
    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Configured"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"

    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"
    return response

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
