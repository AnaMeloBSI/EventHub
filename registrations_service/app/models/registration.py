import uuid
from datetime import datetime, timezone
from app.extensions import db


def utc_now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class Registration(db.Model):
    __tablename__ = "registrations"

    registration_id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    event_id = db.Column(db.String(36), nullable=False, index=True)
    participant_id = db.Column(db.String(36), nullable=False, index=True)
    status = db.Column(db.String(20), nullable=False, default="CONFIRMED")
    attendance_status = db.Column(db.String(20), nullable=False, default="PENDING")
    registered_at = db.Column(db.String(30), nullable=False, default=utc_now_iso)
    cancelled_at = db.Column(db.String(30), nullable=True)

    def to_dict(self):
        return {
            "registration_id": self.registration_id,
            "event_id": self.event_id,
            "participant_id": self.participant_id,
            "status": self.status,
            "attendance_status": self.attendance_status,
            "registered_at": self.registered_at,
            "cancelled_at": self.cancelled_at,
        }
