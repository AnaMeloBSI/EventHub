import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    PORT = int(os.getenv("PORT", 5006))
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "eventhub-jwt-secret-2026")
    INTERNAL_SERVICE_TOKEN = os.getenv("INTERNAL_SERVICE_TOKEN", "internal-secret-token")
    REGISTRATIONS_SERVICE_URL = os.getenv("REGISTRATIONS_SERVICE_URL", "http://localhost:5005")

    BASE_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
    INSTANCE_DIR = os.path.join(BASE_DIR, "instance")
    os.makedirs(INSTANCE_DIR, exist_ok=True)

    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL",
        f"sqlite:///{os.path.join(INSTANCE_DIR, 'certificates.db')}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False