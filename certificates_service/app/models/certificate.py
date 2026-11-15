import uuid
from datetime import datetime, timezone
from app.extensions import db

class Certificate(db.Model):
    __tablename__ = "certificates"

    certificate_id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    validation_code = db.Column(db.String(32), unique=True, nullable=False, index=True, default=lambda: uuid.uuid4().hex[:12].upper())
    event_id = db.Column(db.String(36), nullable=False)
    participant_id = db.Column(db.String(36), nullable=False)
    participant_name = db.Column(db.String(120), nullable=False)
    event_title = db.Column(db.String(150), nullable=False)
    workload_hours = db.Column(db.Integer, nullable=False, default=4)
    issued_at = db.Column(db.String(30), nullable=False, default=lambda: datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"))

    def to_dict(self):
        return {
            "certificate_id": self.certificate_id,
            "validation_code": self.validation_code,
            "event_id": self.event_id,
            "participant_id": self.participant_id,
            "participant_name": self.participant_name,
            "event_title": self.event_title,
            "workload_hours": self.workload_hours,
            "issued_at": self.issued_at,
        }