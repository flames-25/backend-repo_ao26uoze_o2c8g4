"""
Database Schemas for Smart Wearable Platform

Each Pydantic model represents a collection (collection name will be the lowercase of class name)
- Driver -> "driver"
- Device -> "device"
- HealthRecord -> "healthrecord"
- SleepRecord -> "sleeprecord"
- Event -> "event"
- User -> "user"
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Literal
from datetime import datetime

# Authentication user (simple demo user)
class User(BaseModel):
    email: str
    password_hash: str
    name: str
    role: Literal["admin", "dispatcher", "driver"] = "admin"

# Driver master data
class Driver(BaseModel):
    name: str
    employee_id: str
    phone: Optional[str] = None
    status: Literal["active", "inactive"] = "active"

# Device master data
class Device(BaseModel):
    device_id: str
    driver_id: Optional[str] = None
    driver_name: Optional[str] = None
    battery: int = 100
    is_online: bool = True
    last_location: Optional[dict] = None  # {lat: float, lng: float, address: str}

# Health snapshot (latest metrics)
class HealthRecord(BaseModel):
    driver_id: str
    driver_name: str
    device_id: str
    timestamp: datetime
    heart_rate: int
    bp_systolic: int
    bp_diastolic: int
    temperature: float
    calories: int
    steps: int
    duration_minutes: int
    kilometers: float

# ECG samples for quick charting (lightweight series)
class ECGSample(BaseModel):
    device_id: str
    timestamp: datetime
    samples: List[int]  # simple integer series for demo

# Sleep timeline segment
class SleepSegment(BaseModel):
    start: datetime
    end: datetime
    type: Literal["light", "deep", "awake", "rem"]

class SleepRecord(BaseModel):
    driver_id: str
    driver_name: str
    device_id: str
    date: str  # YYYY-MM-DD (per-day aggregation)
    score: int
    duration_minutes: int
    segments: List[SleepSegment]

# Device events (SOS, Fall, etc.)
class Event(BaseModel):
    driver_id: str
    driver_name: str
    device_id: str
    timestamp: datetime
    status_event: Literal["SOS", "Fall Down", "Low Battery", "Remove Smart Wearable"]
    location: Optional[dict] = None  # {lat, lng, address}
