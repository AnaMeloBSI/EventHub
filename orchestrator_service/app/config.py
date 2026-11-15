import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    PORT = int(os.getenv("PORT", 5003))
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "change-this-local-secret")
    INTERNAL_SERVICE_TOKEN = os.getenv("INTERNAL_SERVICE_TOKEN", "change-this-internal-token")
    EVENTS_SERVICE_URL = os.getenv("EVENTS_SERVICE_URL", "http://localhost:5004")
    REGISTRATIONS_SERVICE_URL = os.getenv("REGISTRATIONS_SERVICE_URL", "http://localhost:5005")
    NOTIFICATION_SERVICE_URL = os.getenv("NOTIFICATION_SERVICE_URL", "http://localhost:5002")
