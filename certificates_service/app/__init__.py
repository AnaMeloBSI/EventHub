from flask import Flask
from app.config import Config
from app.extensions import db, swagger
from app.routes.certificate_routes import cert_bp

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    swagger.init_app(app)

    app.register_blueprint(cert_bp)

    with app.app_context():
        db.create_all()

    return app