from datetime import datetime
from app.extensions import db
from app.models.event import Event, utc_now_iso

ALLOWED_EVENT_TYPES = {"LECTURE", "WORKSHOP", "COURSE", "ACADEMIC_WEEK", "OTHER"}
REQUIRED_FIELDS = {"title", "description", "event_type", "location", "start_at", "end_at", "capacity"}


class BusinessError(Exception):
    def __init__(self, status_code, code, message, details=None):
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details or {}


def _parse_iso_datetime(value, field_name):
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        raise BusinessError(400, "INVALID_DATETIME", f"Field '{field_name}' must be ISO 8601 UTC.")


def _validate_event_payload(data, partial=False):
    if not isinstance(data, dict):
        raise BusinessError(400, "INVALID_JSON", "Request body must be a valid JSON object.")

    if not partial:
        missing = [f for f in REQUIRED_FIELDS if f not in data or data[f] in (None, "")]
        if missing:
            raise BusinessError(400, "MISSING_FIELDS", "Missing required fields.", {"missing": missing})

    if "event_type" in data and data["event_type"] not in ALLOWED_EVENT_TYPES:
        raise BusinessError(
            400,
            "INVALID_EVENT_TYPE",
            f"event_type must be one of {sorted(ALLOWED_EVENT_TYPES)}."
        )

    if "capacity" in data:
        if not isinstance(data["capacity"], int) or isinstance(data["capacity"], bool) or data["capacity"] <= 0:
            raise BusinessError(400, "INVALID_CAPACITY", "capacity must be an integer greater than zero.")

    if "start_at" in data and "end_at" in data:
        start_dt = _parse_iso_datetime(data["start_at"], "start_at")
        end_dt = _parse_iso_datetime(data["end_at"], "end_at")
        if end_dt <= start_dt:
            raise BusinessError(400, "INVALID_DATE_RANGE", "end_at must be later than start_at.")


def create_event(data, organizer_id):
    _validate_event_payload(data, partial=False)
    event = Event(
        title=data["title"].strip(),
        description=data["description"].strip(),
        event_type=data["event_type"],
        location=data["location"].strip(),
        start_at=data["start_at"],
        end_at=data["end_at"],
        capacity=data["capacity"],
        organizer_id=organizer_id,
        status="PENDING",
    )
    db.session.add(event)
    db.session.commit()
    return event


def list_events(only_approved=True):
    query = Event.query
    if only_approved:
        query = query.filter_by(status="APPROVED")
    return query.order_by(Event.start_at.asc()).all()


def get_event_by_id(event_id, only_approved=True):
    event = db.session.get(Event, event_id)
    if not event or (only_approved and event.status != "APPROVED"):
        raise BusinessError(404, "EVENT_NOT_FOUND", "Event was not found.")
    return event


def update_event(event_id, data, current_user):
    event = db.session.get(Event, event_id)
    if not event:
        raise BusinessError(404, "EVENT_NOT_FOUND", "Event was not found.")

    if current_user["role"] != "ADMIN" and event.organizer_id != current_user["user_id"]:
        raise BusinessError(403, "FORBIDDEN", "You can only edit your own events.")

    _validate_event_payload(data, partial=True)

    merged_start = data.get("start_at", event.start_at)
    merged_end = data.get("end_at", event.end_at)
    if _parse_iso_datetime(merged_end, "end_at") <= _parse_iso_datetime(merged_start, "start_at"):
        raise BusinessError(400, "INVALID_DATE_RANGE", "end_at must be later than start_at.")

    for field in ("title", "description", "event_type", "location", "start_at", "end_at", "capacity"):
        if field in data:
            val = data[field].strip() if isinstance(data[field], str) else data[field]
            setattr(event, field, val)

    event.updated_at = utc_now_iso()
    db.session.commit()
    return event


def approve_event(event_id):
    event = db.session.get(Event, event_id)
    if not event:
        raise BusinessError(404, "EVENT_NOT_FOUND", "Event was not found.")
    if event.status == "APPROVED":
        raise BusinessError(409, "ALREADY_APPROVED", "Event is already approved.")
    event.status = "APPROVED"
    event.updated_at = utc_now_iso()
    db.session.commit()
    return event


def reject_event(event_id):
    event = db.session.get(Event, event_id)
    if not event:
        raise BusinessError(404, "EVENT_NOT_FOUND", "Event was not found.")
    if event.status == "REJECTED":
        raise BusinessError(409, "ALREADY_REJECTED", "Event is already rejected.")
    event.status = "REJECTED"
    event.updated_at = utc_now_iso()
    db.session.commit()
    return event
