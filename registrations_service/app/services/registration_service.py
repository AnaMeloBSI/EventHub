import requests
from flask import current_app
from app.extensions import db
from app.models.registration import Registration, utc_now_iso

ALLOWED_ATTENDANCE = {"PRESENT", "ABSENT"}


class BusinessError(Exception):
    def __init__(self, status_code, code, message, details=None):
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details or {}


def _fetch_event_from_service(event_id):
    base_url = current_app.config["EVENTS_SERVICE_URL"]
    headers = {"X-Internal-Token": current_app.config["INTERNAL_SERVICE_TOKEN"]}
    try:
        resp = requests.get(f"{base_url}/internal/events/{event_id}", headers=headers, timeout=5)
    except requests.RequestException:
        raise BusinessError(503, "EVENTS_SERVICE_UNAVAILABLE", "Could not reach MS Events.")

    if resp.status_code == 404:
        raise BusinessError(404, "EVENT_NOT_FOUND", "Event was not found.")
    if resp.status_code != 200:
        raise BusinessError(502, "EVENTS_SERVICE_ERROR", "Failed to validate event details.")
    return resp.json()


def create_registration(event_id, participant_id, capacity=None):
    if not event_id or not participant_id:
        raise BusinessError(400, "MISSING_FIELDS", "event_id and participant_id are required.")

    existing = Registration.query.filter_by(
        event_id=event_id, participant_id=participant_id, status="CONFIRMED"
    ).first()
    if existing:
        raise BusinessError(409, "DUPLICATE_REGISTRATION", "Participant is already registered for this event.")

    if capacity is None:
        event_data = _fetch_event_from_service(event_id)
        if event_data.get("status") != "APPROVED":
            raise BusinessError(409, "EVENT_NOT_APPROVED", "Event is not approved for registration.")
        capacity = event_data.get("capacity", 0)

    confirmed_count = Registration.query.filter_by(event_id=event_id, status="CONFIRMED").count()
    if confirmed_count >= capacity:
        raise BusinessError(409, "EVENT_FULL", "Event has reached maximum capacity.")

    registration = Registration(
        event_id=event_id,
        participant_id=participant_id,
        status="CONFIRMED",
        attendance_status="PENDING",
    )
    db.session.add(registration)
    db.session.commit()
    return registration


def list_my_registrations(participant_id):
    return Registration.query.filter_by(participant_id=participant_id).order_by(Registration.registered_at.desc()).all()


def cancel_registration(registration_id, current_user):
    reg = db.session.get(Registration, registration_id)
    if not reg:
        raise BusinessError(404, "REGISTRATION_NOT_FOUND", "Registration was not found.")

    if current_user["role"] != "ADMIN" and reg.participant_id != current_user["user_id"]:
        raise BusinessError(403, "FORBIDDEN", "You can only cancel your own registration.")

    if reg.status == "CANCELLED":
        raise BusinessError(409, "ALREADY_CANCELLED", "Registration is already cancelled.")

    reg.status = "CANCELLED"
    reg.cancelled_at = utc_now_iso()
    db.session.commit()
    return reg


def _verify_event_ownership(event_id, current_user):
    if current_user["role"] == "ADMIN":
        return
    event_data = _fetch_event_from_service(event_id)
    if event_data.get("organizer_id") != current_user["user_id"]:
        raise BusinessError(403, "FORBIDDEN", "You do not own this event.")


def list_event_registrations(event_id, current_user):
    _verify_event_ownership(event_id, current_user)
    return Registration.query.filter_by(event_id=event_id).order_by(Registration.registered_at.asc()).all()


def mark_attendance(registration_id, attendance_status, current_user):
    if attendance_status not in ALLOWED_ATTENDANCE:
        raise BusinessError(400, "INVALID_ATTENDANCE_STATUS", "attendance_status must be PRESENT or ABSENT.")

    reg = db.session.get(Registration, registration_id)
    if not reg:
        raise BusinessError(404, "REGISTRATION_NOT_FOUND", "Registration was not found.")

    if reg.status != "CONFIRMED":
        raise BusinessError(409, "REGISTRATION_NOT_CONFIRMED", "Cannot mark attendance for a cancelled registration.")

    _verify_event_ownership(reg.event_id, current_user)

    reg.attendance_status = attendance_status
    db.session.commit()
    return reg


def check_attendance(event_id, participant_id):
    reg = Registration.query.filter_by(
        event_id=event_id, participant_id=participant_id, status="CONFIRMED"
    ).first()
    if not reg:
        return {"eligible": False, "reason": "REGISTRATION_NOT_FOUND"}
    return {
        "eligible": reg.attendance_status == "PRESENT",
        "registration_id": reg.registration_id,
        "attendance_status": reg.attendance_status,
    }
