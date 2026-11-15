from flask import Flask
from app.config import Config
from app.extensions import db, swagger
from app.routes.registration_routes import registration_bp


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.from_object(Config)
    if test_config:
        app.config.update(test_config)

    app.config["SWAGGER"] = {
        "title": "EventHub - MS Registrations API",
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

    db.init_app(app)
    swagger.init_app(app)
    app.register_blueprint(registration_bp)

    with app.app_context():
        db.create_all()

    return app
