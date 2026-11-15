from flask import Blueprint, request, jsonify
from app.extensions import db
from app.models.user import User
from app.services.auth_service import generate_access_token, require_role, VALID_ROLES

auth_bp = Blueprint("auth", __name__)

def error_response(code: str, message: str, status: int, details=None):
    return jsonify({"error": {"code": code, "message": message, "details": details or {}}}), status

@auth_bp.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "UP", "service": "identity-service"}), 200

@auth_bp.route("/auth/register", methods=["POST"])
def register():
    """
    Cadastro público de participante
    ---
    tags:
      - Identity
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required: [name, email, password]
          properties:
            name: {type: string, example: "Maísa Pinheiro"}
            email: {type: string, example: "maisa@aluno.ifnmg.edu.br"}
            password: {type: string, example: "Senha123"}
    responses:
      201:
        description: Participante criado com sucesso
      400:
        description: Dados inválidos
      409:
        description: E-mail já cadastrado
    """
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if not name or not email or not password:
        return error_response("VALIDATION_ERROR", "Fields name, email and password are required.", 400)

    if User.query.filter_by(email=email).first():
        return error_response("EMAIL_ALREADY_EXISTS", "A user with this email already exists.", 409)

    user = User(name=name, email=email, role="PARTICIPANT")
    user.set_password(password)
    db.session.add(user)
    db.session.commit()

    return jsonify(user.to_dict()), 201

@auth_bp.route("/auth/login", methods=["POST"])
def login():
    """
    Autenticação e emissão de JWT
    ---
    tags:
      - Identity
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required: [email, password]
          properties:
            email: {type: string, example: "admin@eventhub.edu.br"}
            password: {type: string, example: "Admin@123"}
    responses:
      200:
        description: Token JWT emitido
      401:
        description: Credenciais inválidas
    """
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if not email or not password:
        return error_response("VALIDATION_ERROR", "Fields email and password are required.", 400)

    user = User.query.filter_by(email=email).first()
    if not user or not user.check_password(password) or not user.is_active:
        return error_response("INVALID_CREDENTIALS", "Invalid email or password.", 401)

    token = generate_access_token(user)
    return jsonify({
        "access_token": token,
        "token_type": "Bearer",
        "user": user.to_dict()
    }), 200

@auth_bp.route("/auth/me", methods=["GET"])
@require_role("ADMIN", "ORGANIZER", "PARTICIPANT")
def get_me():
    """
    Retorna dados do usuário autenticado
    ---
    tags:
      - Identity
    parameters:
      - in: header
        name: Authorization
        type: string
        required: true
        description: "Bearer <access_token>"
    responses:
      200:
        description: Dados do usuário
      401:
        description: Token ausente ou inválido
    """
    user_id = request.current_user["sub"]
    user = User.query.get(user_id)
    if not user:
        return error_response("USER_NOT_FOUND", "User not found.", 404)
    return jsonify(user.to_dict()), 200

@auth_bp.route("/auth/users", methods=["POST"])
@require_role("ADMIN")
def create_privileged_user():
    """
    Criação administrativa de usuários (ADMIN, ORGANIZER ou PARTICIPANT)
    ---
    tags:
      - Identity
    parameters:
      - in: header
        name: Authorization
        type: string
        required: true
      - in: body
        name: body
        required: true
        schema:
          type: object
          required: [name, email, password, role]
          properties:
            name: {type: string, example: "Ana Clara"}
            email: {type: string, example: "ana.org@ifnmg.edu.br"}
            password: {type: string, example: "Org@123"}
            role: {type: string, example: "ORGANIZER"}
    responses:
      201:
        description: Usuário criado pelo administrador
      403:
        description: Acesso restrito a ADMIN
    """
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    role = (data.get("role") or "").strip().upper()

    if not name or not email or not password or role not in VALID_ROLES:
        return error_response("VALIDATION_ERROR", "Valid name, email, password and role are required.", 400)

    if User.query.filter_by(email=email).first():
        return error_response("EMAIL_ALREADY_EXISTS", "A user with this email already exists.", 409)

    user = User(name=name, email=email, role=role)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()

    return jsonify(user.to_dict()), 201