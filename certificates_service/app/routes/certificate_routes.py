import jwt
import requests
from functools import wraps
from flask import Blueprint, request, jsonify, current_app
from app.extensions import db
from app.models.certificate import Certificate

cert_bp = Blueprint("certificates", __name__)

def error_response(code: str, message: str, status: int, details=None):
    return jsonify({"error": {"code": code, "message": message, "details": details or {}}}), status

def require_auth(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return error_response("UNAUTHORIZED", "Missing or invalid Authorization header.", 401)
        token = auth_header.split(" ", 1)[1].strip()
        try:
            request.current_user = jwt.decode(token, current_app.config["JWT_SECRET_KEY"], algorithms=["HS256"])
        except jwt.InvalidTokenError:
            return error_response("INVALID_TOKEN", "Invalid or expired access token.", 401)
        return fn(*args, **kwargs)
    return wrapper

@cert_bp.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "UP", "service": "certificates-service"}), 200

@cert_bp.route("/certificates/issue", methods=["POST"])
@require_auth
def issue_certificate():
    """
    Emite certificado após validar presença no serviço de inscrições
    ---
    tags:
      - Certificates
    parameters:
      - in: header
        name: Authorization
        type: string
        required: true
        description: "Bearer <access_token>"
      - in: body
        name: body
        required: true
        schema:
          type: object
          required: [event_id, participant_id, participant_name, event_title]
          properties:
            event_id: {type: string, example: "evt-001"}
            participant_id: {type: string, example: "7d0a0a3d-f61f-4b09-96d3-fb70cd84e711"}
            participant_name: {type: string, example: "Maísa Pinheiro"}
            event_title: {type: string, example: "Semana de Tecnologia IFNMG"}
            workload_hours: {type: integer, example: 8}
    responses:
      201:
        description: Certificado emitido com sucesso
      403:
        description: Participante sem presença confirmada
      502:
        description: Falha ao comunicar com o serviço de inscrições
    """
    data = request.get_json(silent=True) or {}
    event_id = (data.get("event_id") or "").strip()
    participant_id = (data.get("participant_id") or "").strip()
    participant_name = (data.get("participant_name") or "").strip()
    event_title = (data.get("event_title") or "").strip()
    workload_hours = int(data.get("workload_hours") or 4)

    if not event_id or not participant_id or not participant_name or not event_title:
        return error_response("VALIDATION_ERROR", "Fields event_id, participant_id, participant_name and event_title are required.", 400)

    existing = Certificate.query.filter_by(event_id=event_id, participant_id=participant_id).first()
    if existing:
        return jsonify(existing.to_dict()), 200

    check_url = f"{current_app.config['REGISTRATIONS_SERVICE_URL']}/internal/registrations/check-attendance"
    try:
        resp = requests.get(
            check_url,
            params={"event_id": event_id, "participant_id": participant_id},
            headers={"X-Internal-Token": current_app.config["INTERNAL_SERVICE_TOKEN"]},
            timeout=5
        )
    except requests.RequestException:
        return error_response("UPSTREAM_UNAVAILABLE", "Could not reach Registrations Service to verify attendance.", 502)

    if resp.status_code != 200:
        return error_response("ATTENDANCE_CHECK_FAILED", "Registrations service rejected attendance check.", resp.status_code)

    att_data = resp.json()
    if not att_data.get("attended", False):
        return error_response("ATTENDANCE_NOT_CONFIRMED", "Participant attendance was not confirmed for this event.", 403)

    cert = Certificate(
        event_id=event_id,
        participant_id=participant_id,
        participant_name=participant_name,
        event_title=event_title,
        workload_hours=workload_hours
    )
    db.session.add(cert)
    db.session.commit()

    return jsonify(cert.to_dict()), 201

@cert_bp.route("/certificates/validate/<validation_code>", methods=["GET"])
def validate_certificate(validation_code: str):
    """
    Valida autenticidade de um certificado pelo código público
    ---
    tags:
      - Certificates
    parameters:
      - in: path
        name: validation_code
        type: string
        required: true
    responses:
      200:
        description: Certificado válido
      404:
        description: Código de validação não encontrado
    """
    cert = Certificate.query.filter_by(validation_code=validation_code.strip().upper()).first()
    if not cert:
        return error_response("CERTIFICATE_NOT_FOUND", "Invalid validation code.", 404)

    return jsonify({"valid": True, "certificate": cert.to_dict()}), 200