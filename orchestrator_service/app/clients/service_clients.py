import requests
from flask import current_app


class OrchestrationError(Exception):
    def __init__(self, status_code, code, message, details=None):
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details or {}


def _internal_headers():
    return {
        "Content-Type": "application/json",
        "X-Internal-Token": current_app.config["INTERNAL_SERVICE_TOKEN"],
    }


def get_event_details(event_id):
    url = f"{current_app.config['EVENTS_SERVICE_URL']}/internal/events/{event_id}"
    try:
        resp = requests.get(url, headers=_internal_headers(), timeout=5)
    except requests.RequestException:
        raise OrchestrationError(503, "EVENTS_SERVICE_UNAVAILABLE", "MS Events is currently unavailable.")

    if resp.status_code == 404:
        raise OrchestrationError(404, "EVENT_NOT_FOUND", "Event was not found.")
    if resp.status_code != 200:
        raise OrchestrationError(502, "EVENTS_SERVICE_ERROR", "Failed to fetch event details.")
    return resp.json()


def create_domain_registration(event_id, participant_id, capacity):
    url = f"{current_app.config['REGISTRATIONS_SERVICE_URL']}/internal/registrations"
    payload = {
        "event_id": event_id,
        "participant_id": participant_id,
        "capacity": capacity,
    }
    try:
        resp = requests.post(url, json=payload, headers=_internal_headers(), timeout=5)
    except requests.RequestException:
        raise OrchestrationError(
            503, "REGISTRATIONS_SERVICE_UNAVAILABLE", "MS Registrations is currently unavailable."
        )

    if resp.status_code in (400, 404, 409):
        err_body = resp.json().get("error", {})
        raise OrchestrationError(
            resp.status_code,
            err_body.get("code", "REGISTRATION_ERROR"),
            err_body.get("message", "Could not complete registration."),
            err_body.get("details", {}),
        )
    if resp.status_code != 201:
        raise OrchestrationError(502, "REGISTRATIONS_SERVICE_ERROR", "Unexpected response from MS Registrations.")
    return resp.json()


def send_registration_notification(user_id, event_data, registration_data):
    url = f"{current_app.config['NOTIFICATION_SERVICE_URL']}/internal/notifications"
    payload = {
        "user_id": user_id,
        "type": "REGISTRATION_CONFIRMED",
        "title": f"Inscrição confirmada: {event_data.get('title')}",
        "message": f"Sua inscrição no evento '{event_data.get('title')}' foi confirmada.",
        "metadata": {
            "event_id": event_data.get("event_id"),
            "registration_id": registration_data.get("registration_id"),
        },
    }
    try:
        resp = requests.post(url, json=payload, headers=_internal_headers(), timeout=5)
        if resp.status_code in (200, 201):
            return "SENT"
        return "FAILED"
    except requests.RequestException:
        return "FAILED"
