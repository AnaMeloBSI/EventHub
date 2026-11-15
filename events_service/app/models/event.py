import uuid
from datetime import datetime, timezone
from app.extensions import db


def utc_now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class Event(db.Model):
    __tablename__ = "events"

    event_id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    event_type = db.Column(db.String(50), nullable=False)
    location = db.Column(db.String(200), nullable=False)
    start_at = db.Column(db.String(30), nullable=False)
    end_at = db.Column(db.String(30), nullable=False)
    capacity = db.Column(db.Integer, nullable=False)
    organizer_id = db.Column(db.String(36), nullable=False)
    status = db.Column(db.String(20), nullable=False, default="PENDING")
    created_at = db.Column(db.String(30), nullable=False, default=utc_now_iso)
    updated_at = db.Column(db.String(30), nullable=False, default=utc_now_iso, onupdate=utc_now_iso)

    def to_dict(self):
        return {
            "event_id": self.event_id,
            "title": self.title,
            "description": self.description,
            "event_type": self.event_type,
            "location": self.location,
            "start_at": self.start_at,
            "end_at": self.end_at,
            "capacity": self.capacity,
            "organizer_id": self.organizer_id,
            "status": self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
