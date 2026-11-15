from flask import Flask
from flasgger import Swagger
from app.config import Config
from app.routes.gateway_routes import gateway_bp

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    Swagger(app)
    app.register_blueprint(gateway_bp)

    return app