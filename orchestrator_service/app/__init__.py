from flask import Flask
from flasgger import Swagger
from app.config import Config
from app.routes.orchestrator_routes import orchestrator_bp


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.from_object(Config)
    if test_config:
        app.config.update(test_config)

    app.config["SWAGGER"] = {
        "title": "EventHub - Orchestrator Service API",
        "uiversion": 3,
        "securityDefinitions": {
            "Bearer": {
                "type": "apiKey",
                "name": "Authorization",
                "in": "header",
                "description": "JWT Authorization header: Bearer <token>"
            }
        }
    }

    Swagger(app)
    app.register_blueprint(orchestrator_bp)
    return app
