from flask import Blueprint, request, jsonify, g
from app.auth import require_role, error_response
from app.clients import service_clients
from app.clients.service_clients import OrchestrationError

orchestrator_bp = Blueprint("orchestrator", __name__)


@orchestrator_bp.errorhandler(OrchestrationError)
def handle_orchestration_error(err):
    return error_response(err.status_code, err.code, err.message, err.details)


@orchestrator_bp.get("/health")
def health():
    return jsonify({"status": "ok", "service": "orchestrator-service"}), 200


@orchestrator_bp.post("/registrations")
@require_role("PARTICIPANT")
def orchestrate_registration():
    """
    Orchestrate event registration flow (Validate Event -> Register -> Notify)
    ---
    tags:
      - Orchestrator
    security:
      - Bearer: []
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - event_id
          properties:
            event_id:
              type: string
    responses:
      201:
        description: Registration confirmed with notification status
      400:
        description: Missing event_id
      404:
        description: Event not found
      409:
        description: Event not approved, full, or duplicate registration
    """
    data = request.get_json(silent=True) or {}
    event_id = data.get("event_id")
    if not event_id:
        return error_response(400, "MISSING_FIELDS", "Field 'event_id' is required.")

    participant_id = g.current_user["user_id"]

    event_data = service_clients.get_event_details(event_id)
    if event_data.get("status") != "APPROVED":
        return error_response(409, "EVENT_NOT_APPROVED", "Event is not open for registration.")

    registration_data = service_clients.create_domain_registration(
        event_id=event_id,
        participant_id=participant_id,
        capacity=event_data.get("capacity", 0),
    )

    notification_status = service_clients.send_registration_notification(
        user_id=participant_id,
        event_data=event_data,
        registration_data=registration_data,
    )

    response_payload = {
        **registration_data,
        "notification_status": notification_status,
    }
    return jsonify(response_payload), 201
