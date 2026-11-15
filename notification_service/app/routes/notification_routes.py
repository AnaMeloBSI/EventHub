import json
from flask import Blueprint, request, jsonify, current_app
from app.extensions import db
from app.models.notification import Notification

notif_bp = Blueprint("notifications", __name__)

def error_response(code: str, message: str, status: int, details=None):
    return jsonify({"error": {"code": code, "message": message, "details": details or {}}}), status

@notif_bp.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "UP", "service": "notification-service"}), 200

@notif_bp.route("/internal/notifications", methods=["POST"])
def send_notification():
    """
    Recebe solicitação interna de envio/registro de notificação
    ---
    tags:
      - Notifications
    parameters:
      - in: header
        name: X-Internal-Token
        type: string
        required: true
        example: "internal-secret-token"
      - in: body
        name: body
        required: true
        schema:
          type: object
          required: [user_id, type, title, message]
          properties:
            user_id: {type: string, example: "7d0a0a3d-f61f-4b09-96d3-fb70cd84e711"}
            type: {type: string, example: "REGISTRATION_CONFIRMED"}
            title: {type: string, example: "Inscrição Confirmada"}
            message: {type: string, example: "Sua inscrição no evento foi confirmada com sucesso."}
            metadata: {type: object, example: {"event_id": "123", "registration_id": "456"}}
    responses:
      201:
        description: Notificação registrada e enviada
      400:
        description: Dados inválidos
      401:
        description: Token interno ausente ou inválido
    """
    internal_token = request.headers.get("X-Internal-Token", "")
    if internal_token != current_app.config["INTERNAL_SERVICE_TOKEN"]:
        return error_response("UNAUTHORIZED_SERVICE", "Invalid or missing X-Internal-Token.", 401)

    data = request.get_json(silent=True) or {}
    user_id = (data.get("user_id") or "").strip()
    notif_type = (data.get("type") or "").strip()
    title = (data.get("title") or "").strip()
    message = (data.get("message") or "").strip()
    metadata = data.get("metadata") or {}

    if not user_id or not notif_type or not title or not message:
        return error_response("VALIDATION_ERROR", "Fields user_id, type, title and message are required.", 400)

    notif = Notification(
        user_id=user_id,
        type=notif_type,
        title=title,
        message=message,
        metadata_json=json.dumps(metadata),
        status="SENT"
    )
    db.session.add(notif)
    db.session.commit()

    print(f"[NOTIFICATION SENT] User: {user_id} | {title}: {message}")
    return jsonify(notif.to_dict()), 201

@notif_bp.route("/internal/notifications", methods=["GET"])
def list_notifications():
    """
    Lista notificações registradas (útil para auditoria e demonstração)
    ---
    tags:
      - Notifications
    parameters:
      - in: header
        name: X-Internal-Token
        type: string
        required: true
        example: "internal-secret-token"
    responses:
      200:
        description: Lista de notificações
      401:
        description: Token interno ausente ou inválido
    """
    internal_token = request.headers.get("X-Internal-Token", "")
    if internal_token != current_app.config["INTERNAL_SERVICE_TOKEN"]:
        return error_response("UNAUTHORIZED_SERVICE", "Invalid or missing X-Internal-Token.", 401)

    notifications = Notification.query.order_by(Notification.created_at.desc()).all()
    return jsonify([n.to_dict() for n in notifications]), 200