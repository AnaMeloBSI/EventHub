import io
import jwt
import requests
from functools import wraps
from flask import Blueprint, request, jsonify, current_app, send_file
from fpdf import FPDF
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

def generate_certificate_pdf(cert: Certificate) -> io.BytesIO:
    pdf = FPDF(orientation="L", unit="mm", format="A4")
    pdf.add_page()
    pdf.set_auto_page_break(auto=False)

    # Borda decorativa
    pdf.set_draw_color(25, 65, 120)
    pdf.set_line_width(1.5)
    pdf.rect(10, 10, 277, 190)
    pdf.set_line_width(0.5)
    pdf.rect(13, 13, 271, 184)

    # Cabeçalho
    pdf.set_font("Helvetica", "B", 26)
    pdf.set_text_color(25, 65, 120)
    pdf.ln(22)
    pdf.cell(0, 14, "CERTIFICADO DE PARTICIPACAO", align="C", new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("Helvetica", "", 12)
    pdf.set_text_color(90, 90, 90)
    pdf.cell(0, 8, "EventHub - Plataforma de Eventos Academicos", align="C", new_x="LMARGIN", new_y="NEXT")

    # Corpo
    pdf.ln(18)
    pdf.set_font("Helvetica", "", 14)
    pdf.set_text_color(40, 40, 40)
    pdf.cell(0, 10, "Certificamos que", align="C", new_x="LMARGIN", new_y="NEXT")

    pdf.ln(4)
    pdf.set_font("Helvetica", "B", 22)
    pdf.set_text_color(15, 15, 15)
    pdf.cell(0, 12, cert.participant_name.encode("latin-1", "replace").decode("latin-1"), align="C", new_x="LMARGIN", new_y="NEXT")

    pdf.ln(6)
    pdf.set_font("Helvetica", "", 14)
    pdf.set_text_color(40, 40, 40)
    texto = (
        f"participou do evento \"{cert.event_title}\", "
        f"com carga horaria total de {cert.workload_hours} horas."
    ).encode("latin-1", "replace").decode("latin-1")
    pdf.multi_cell(0, 9, texto, align="C")

    # Rodapé com código de validação
    pdf.ln(24)
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 6, f"Emitido em: {cert.issued_at}", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(25, 65, 120)
    pdf.cell(0, 7, f"Codigo de Validacao: {cert.validation_code}", align="C", new_x="LMARGIN", new_y="NEXT")

    buffer = io.BytesIO()
    pdf.output(buffer)
    buffer.seek(0)
    return buffer

@cert_bp.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "UP", "service": "certificates-service"}), 200

@cert_bp.route("/certificates/issue", methods=["POST"])
@require_auth
def issue_certificate():
    """
    Emite certificado para o participante autenticado após validar presença
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
          required: [event_id, participant_name, event_title]
          properties:
            event_id: {type: string, example: "evt-001"}
            participant_name: {type: string, example: "Maisa Pinheiro"}
            event_title: {type: string, example: "Semana de Tecnologia IFNMG"}
            workload_hours: {type: integer, example: 8}
    responses:
      201:
        description: Certificado emitido com sucesso
      200:
        description: Certificado já emitido anteriormente
      403:
        description: Participante sem presença confirmada
      502:
        description: Falha ao comunicar com o serviço de inscrições
    """
    data = request.get_json(silent=True) or {}
    participant_id = request.current_user.get("sub")
    event_id = (data.get("event_id") or "").strip()
    participant_name = (data.get("participant_name") or "").strip()
    event_title = (data.get("event_title") or "").strip()
    workload_hours = int(data.get("workload_hours") or 4)

    if not participant_id:
        return error_response("INVALID_TOKEN_PAYLOAD", "Token subject (sub) missing.", 401)
    if not event_id or not participant_name or not event_title:
        return error_response("VALIDATION_ERROR", "Fields event_id, participant_name and event_title are required.", 400)

    existing = Certificate.query.filter_by(event_id=event_id, participant_id=participant_id).first()
    if existing:
        res = existing.to_dict()
        res["pdf_url"] = f"/certificates/{existing.certificate_id}/pdf"
        return jsonify(res), 200

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

    res = cert.to_dict()
    res["pdf_url"] = f"/certificates/{cert.certificate_id}/pdf"
    return jsonify(res), 201

@cert_bp.route("/certificates/my", methods=["GET"])
@require_auth
def list_my_certificates():
    """
    Lista todos os certificados do participante autenticado
    ---
    tags:
      - Certificates
    parameters:
      - in: header
        name: Authorization
        type: string
        required: true
    responses:
      200:
        description: Lista de certificados do usuário
    """
    participant_id = request.current_user.get("sub")
    certs = Certificate.query.filter_by(participant_id=participant_id).order_by(Certificate.issued_at.desc()).all()
    items = []
    for c in certs:
        d = c.to_dict()
        d["pdf_url"] = f"/certificates/{c.certificate_id}/pdf"
        items.append(d)
    return jsonify(items), 200

@cert_bp.route("/certificates/<certificate_id>", methods=["GET"])
@require_auth
def get_certificate(certificate_id: str):
    """
    Consulta detalhes de um certificado específico (dono ou ADMIN)
    ---
    tags:
      - Certificates
    parameters:
      - in: header
        name: Authorization
        type: string
        required: true
      - in: path
        name: certificate_id
        type: string
        required: true
    responses:
      200:
        description: Dados do certificado
      403:
        description: Sem permissão para visualizar este certificado
      404:
        description: Certificado não encontrado
    """
    cert = Certificate.query.filter_by(certificate_id=certificate_id).first()
    if not cert:
        return error_response("CERTIFICATE_NOT_FOUND", "Certificate not found.", 404)

    user_id = request.current_user.get("sub")
    role = request.current_user.get("role")
    if cert.participant_id != user_id and role != "ADMIN":
        return error_response("FORBIDDEN", "You do not have permission to view this certificate.", 403)

    res = cert.to_dict()
    res["pdf_url"] = f"/certificates/{cert.certificate_id}/pdf"
    return jsonify(res), 200

@cert_bp.route("/certificates/<certificate_id>/pdf", methods=["GET"])
@require_auth
def download_certificate_pdf(certificate_id: str):
    """
    Gera e faz download do certificado em PDF (dono ou ADMIN)
    ---
    tags:
      - Certificates
    parameters:
      - in: header
        name: Authorization
        type: string
        required: true
      - in: path
        name: certificate_id
        type: string
        required: true
    responses:
      200:
        description: Arquivo PDF do certificado
      403:
        description: Sem permissão
      404:
        description: Certificado não encontrado
    """
    cert = Certificate.query.filter_by(certificate_id=certificate_id).first()
    if not cert:
        return error_response("CERTIFICATE_NOT_FOUND", "Certificate not found.", 404)

    user_id = request.current_user.get("sub")
    role = request.current_user.get("role")
    if cert.participant_id != user_id and role != "ADMIN":
        return error_response("FORBIDDEN", "You do not have permission to download this certificate.", 403)

    pdf_buffer = generate_certificate_pdf(cert)
    return send_file(
        pdf_buffer,
        mimetype="application/pdf",
        as_attachment=True,
        download_name=f"certificado_{cert.validation_code}.pdf"
    )

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