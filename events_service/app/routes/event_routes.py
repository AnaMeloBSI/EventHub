from flask import Blueprint, request, jsonify, g
from app.auth import require_role, require_internal_service, error_response
from app.services import event_service
from app.services.event_service import BusinessError

event_bp = Blueprint("events", __name__)


@event_bp.errorhandler(BusinessError)
def handle_business_error(err):
    return error_response(err.status_code, err.code, err.message, err.details)


@event_bp.get("/health")
def health():
    return jsonify({"status": "ok", "service": "events-service"}), 200


@event_bp.get("/events")
def get_events():
    """
    List approved events
    ---
    tags:
      - Events
    responses:
      200:
        description: List of approved events
    """
    events = event_service.list_events(only_approved=True)
    return jsonify([e.to_dict() for e in events]), 200


@event_bp.get("/events/<string:event_id>")
def get_event(event_id):
    """
    Get approved event details by ID
    ---
    tags:
      - Events
    parameters:
      - name: event_id
        in: path
        type: string
        required: true
    responses:
      200:
        description: Event details
      404:
        description: Event not found
    """
    event = event_service.get_event_by_id(event_id, only_approved=True)
    return jsonify(event.to_dict()), 200


@event_bp.post("/events")
@require_role("ORGANIZER")
def create_event():
    """
    Create a new event (status PENDING)
    ---
    tags:
      - Events
    security:
      - Bearer: []
    responses:
      201:
        description: Event created
      400:
        description: Invalid payload
      403:
        description: Forbidden
    """
    data = request.get_json(silent=True)
    event = event_service.create_event(data, organizer_id=g.current_user["user_id"])
    return jsonify(event.to_dict()), 201


@event_bp.put("/events/<string:event_id>")
@require_role("ORGANIZER", "ADMIN")
def update_event(event_id):
    """
    Update an existing event (owner ORGANIZER or ADMIN)
    ---
    tags:
      - Events
    security:
      - Bearer: []
    parameters:
      - name: event_id
        in: path
        type: string
        required: true
    responses:
      200:
        description: Event updated
      403:
        description: Forbidden
      404:
        description: Event not found
    """
    data = request.get_json(silent=True)
    event = event_service.update_event(event_id, data, g.current_user)
    return jsonify(event.to_dict()), 200


@event_bp.patch("/events/<string:event_id>/approve")
@require_role("ADMIN")
def approve_event(event_id):
    """
    Approve an event (ADMIN only)
    ---
    tags:
      - Events
    security:
      - Bearer: []
    parameters:
      - name: event_id
        in: path
        type: string
        required: true
    responses:
      200:
        description: Event approved
      403:
        description: Forbidden
      404:
        description: Event not found
      409:
        description: Already approved
    """
    event = event_service.approve_event(event_id)
    return jsonify(event.to_dict()), 200


@event_bp.patch("/events/<string:event_id>/reject")
@require_role("ADMIN")
def reject_event(event_id):
    """
    Reject an event (ADMIN only)
    ---
    tags:
      - Events
    security:
      - Bearer: []
    parameters:
      - name: event_id
        in: path
        type: string
        required: true
    responses:
      200:
        description: Event rejected
      403:
        description: Forbidden
      404:
        description: Event not found
      409:
        description: Already rejected
    """
    event = event_service.reject_event(event_id)
    return jsonify(event.to_dict()), 200


@event_bp.get("/internal/events/<string:event_id>")
@require_internal_service
def internal_get_event(event_id):
    event = event_service.get_event_by_id(event_id, only_approved=False)
    return jsonify(event.to_dict()), 200
