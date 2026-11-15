from flask import Blueprint, request, jsonify, g
from app.auth import require_role, require_internal_service, error_response
from app.services import registration_service
from app.services.registration_service import BusinessError

registration_bp = Blueprint("registrations", __name__)


@registration_bp.errorhandler(BusinessError)
def handle_business_error(err):
    return error_response(err.status_code, err.code, err.message, err.details)


@registration_bp.get("/health")
def health():
    return jsonify({"status": "ok", "service": "registrations-service"}), 200


@registration_bp.post("/internal/registrations")
@require_internal_service
def internal_create_registration():
    data = request.get_json(silent=True) or {}
    reg = registration_service.create_registration(
        event_id=data.get("event_id"),
        participant_id=data.get("participant_id"),
        capacity=data.get("capacity"),
    )
    return jsonify(reg.to_dict()), 201


@registration_bp.get("/internal/registrations/check-attendance")
@require_internal_service
def internal_check_attendance():
    event_id = request.args.get("event_id")
    participant_id = request.args.get("participant_id")
    if not event_id or not participant_id:
        return error_response(400, "MISSING_PARAMS", "event_id and participant_id query params are required.")
    result = registration_service.check_attendance(event_id, participant_id)
    return jsonify(result), 200


@registration_bp.get("/registrations/me")
@require_role("PARTICIPANT")
def get_my_registrations():
    """
    List registrations for the authenticated participant
    ---
    tags:
      - Registrations
    security:
      - Bearer: []
    responses:
      200:
        description: List of participant registrations
    """
    regs = registration_service.list_my_registrations(g.current_user["user_id"])
    return jsonify([r.to_dict() for r in regs]), 200


@registration_bp.delete("/registrations/<string:registration_id>")
@require_role("PARTICIPANT", "ADMIN")
def delete_registration(registration_id):
    """
    Cancel a registration (owner PARTICIPANT or ADMIN)
    ---
    tags:
      - Registrations
    security:
      - Bearer: []
    parameters:
      - name: registration_id
        in: path
        type: string
        required: true
    responses:
      200:
        description: Registration cancelled
      403:
        description: Forbidden
      404:
        description: Not found
      409:
        description: Already cancelled
    """
    reg = registration_service.cancel_registration(registration_id, g.current_user)
    return jsonify(reg.to_dict()), 200


@registration_bp.get("/events/<string:event_id>/registrations")
@require_role("ORGANIZER", "ADMIN")
def get_event_registrations(event_id):
    """
    List registrations for an event (owner ORGANIZER or ADMIN)
    ---
    tags:
      - Registrations
    security:
      - Bearer: []
    parameters:
      - name: event_id
        in: path
        type: string
        required: true
    responses:
      200:
        description: List of event registrations
      403:
        description: Forbidden
    """
    regs = registration_service.list_event_registrations(event_id, g.current_user)
    return jsonify([r.to_dict() for r in regs]), 200


@registration_bp.patch("/registrations/<string:registration_id>/attendance")
@require_role("ORGANIZER", "ADMIN")
def patch_attendance(registration_id):
    """
    Mark attendance as PRESENT or ABSENT (owner ORGANIZER or ADMIN)
    ---
    tags:
      - Registrations
    security:
      - Bearer: []
    parameters:
      - name: registration_id
        in: path
        type: string
        required: true
    responses:
      200:
        description: Attendance updated
      400:
        description: Invalid status
      403:
        description: Forbidden
      404:
        description: Not found
    """
    data = request.get_json(silent=True) or {}
    reg = registration_service.mark_attendance(
        registration_id, data.get("attendance_status"), g.current_user
    )
    return jsonify(reg.to_dict()), 200
