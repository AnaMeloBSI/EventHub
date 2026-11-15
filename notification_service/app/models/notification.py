import uuid
import json
from datetime import datetime, timezone
from app.extensions import db

class Notification(db.Model):
    __tablename__ = "notifications"

    notification_id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.String(36), nullable=False)
    type = db.Column(db.String(50), nullable=False)
    title = db.Column(db.String(150), nullable=False)
    message = db.Column(db.Text, nullable=False)
    metadata_json = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), nullable=False, default="SENT")
    created_at = db.Column(db.String(30), nullable=False, default=lambda: datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"))

    def to_dict(self):
        return {
            "notification_id": self.notification_id,
            "user_id": self.user_id,
            "type": self.type,
            "title": self.title,
            "message": self.message,
            "metadata": json.loads(self.metadata_json) if self.metadata_json else {},
            "status": self.status,
            "created_at": self.created_at,
        }