import requests
from flask import Blueprint, request, jsonify, Response, current_app

gateway_bp = Blueprint("gateway", __name__)

EXCLUDED_HEADERS = {"host", "content-length", "connection", "transfer-encoding"}

def forward_request(target_base_url: str, subpath: str):
    url = f"{target_base_url.rstrip('/')}/{subpath.lstrip('/')}"
    headers = {
        k: v for k, v in request.headers.items()
        if k.lower() not in EXCLUDED_HEADERS
    }
    try:
        resp = requests.request(
            method=request.method,
            url=url,
            headers=headers,
            params=request.args,
            data=request.get_data(),
            timeout=10
        )
        response_headers = [
            (k, v) for k, v in resp.raw.headers.items()
            if k.lower() not in EXCLUDED_HEADERS
        ]
        return Response(resp.content, status=resp.status_code, headers=response_headers)
    except requests.RequestException:
        return jsonify({
            "error": {
                "code": "BAD_GATEWAY",
                "message": f"Target service at {target_base_url} is unavailable.",
                "details": {}
            }
        }), 502

@gateway_bp.route("/health", methods=["GET"])
def health():
    """
    Verifica saúde do API Gateway e dos microsserviços conectados
    ---
    tags:
      - Gateway
    responses:
      200:
        description: Status geral do Gateway
    """
    services = {
        "identity": current_app.config["IDENTITY_SERVICE_URL"],
        "notifications": current_app.config["NOTIFICATION_SERVICE_URL"],
        "orchestrator": current_app.config["ORCHESTRATOR_SERVICE_URL"],
        "events": current_app.config["EVENTS_SERVICE_URL"],
        "registrations": current_app.config["REGISTRATIONS_SERVICE_URL"],
        "certificates": current_app.config["CERTIFICATES_SERVICE_URL"],
    }
    statuses = {}
    for name, base_url in services.items():
        try:
            r = requests.get(f"{base_url}/health", timeout=2)
            statuses[name] = "UP" if r.status_code == 200 else f"DOWN ({r.status_code})"
        except requests.RequestException:
            statuses[name] = "UNREACHABLE"

    return jsonify({"status": "UP", "service": "api-gateway", "downstream": statuses}), 200

@gateway_bp.route("/auth", defaults={"path": ""}, methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
@gateway_bp.route("/auth/<path:path>", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
@gateway_bp.route("/api/auth", defaults={"path": ""}, methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
@gateway_bp.route("/api/auth/<path:path>", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
def proxy_auth(path):
    subpath = f"auth/{path}" if path else "auth"
    return forward_request(current_app.config["IDENTITY_SERVICE_URL"], subpath)

@gateway_bp.route("/events", defaults={"path": ""}, methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
@gateway_bp.route("/events/<path:path>", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
@gateway_bp.route("/api/events", defaults={"path": ""}, methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
@gateway_bp.route("/api/events/<path:path>", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
def proxy_events(path):
    subpath = f"events/{path}" if path else "events"
    return forward_request(current_app.config["EVENTS_SERVICE_URL"], subpath)

@gateway_bp.route("/registrations", defaults={"path": ""}, methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
@gateway_bp.route("/registrations/<path:path>", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
@gateway_bp.route("/api/registrations", defaults={"path": ""}, methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
@gateway_bp.route("/api/registrations/<path:path>", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
def proxy_registrations(path):
    subpath = f"registrations/{path}" if path else "registrations"
    return forward_request(current_app.config["REGISTRATIONS_SERVICE_URL"], subpath)

@gateway_bp.route("/orchestrator", defaults={"path": ""}, methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
@gateway_bp.route("/orchestrator/<path:path>", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
@gateway_bp.route("/api/orchestrator", defaults={"path": ""}, methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
@gateway_bp.route("/api/orchestrator/<path:path>", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
def proxy_orchestrator(path):
    subpath = f"orchestrator/{path}" if path else "orchestrator"
    return forward_request(current_app.config["ORCHESTRATOR_SERVICE_URL"], subpath)

@gateway_bp.route("/certificates", defaults={"path": ""}, methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
@gateway_bp.route("/certificates/<path:path>", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
@gateway_bp.route("/api/certificates", defaults={"path": ""}, methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
@gateway_bp.route("/api/certificates/<path:path>", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
def proxy_certificates(path):
    subpath = f"certificates/{path}" if path else "certificates"
    return forward_request(current_app.config["CERTIFICATES_SERVICE_URL"], subpath)