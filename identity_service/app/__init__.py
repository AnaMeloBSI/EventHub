from flask import Flask
from app.config import Config
from app.extensions import db, swagger
from app.routes.auth_routes import auth_bp
from app.services.auth_service import seed_default_admin

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    swagger.init_app(app)

    app.register_blueprint(auth_bp)

    with app.app_context():
        db.create_all()
        seed_default_admin()

    return app