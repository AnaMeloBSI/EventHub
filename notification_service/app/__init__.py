from flask import Flask
from app.config import Config
from app.extensions import db, swagger
from app.routes.notification_routes import notif_bp

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    swagger.init_app(app)

    app.register_blueprint(notif_bp)

    with app.app_context():
        db.create_all()

    return app