import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    PORT = int(os.getenv("GATEWAY_PORT", 5000))
    IDENTITY_SERVICE_URL = os.getenv("IDENTITY_SERVICE_URL", "http://localhost:5001")
    NOTIFICATION_SERVICE_URL = os.getenv("NOTIFICATION_SERVICE_URL", "http://localhost:5002")
    ORCHESTRATOR_SERVICE_URL = os.getenv("ORCHESTRATOR_SERVICE_URL", "http://localhost:5003")
    EVENTS_SERVICE_URL = os.getenv("EVENTS_SERVICE_URL", "http://localhost:5004")
    REGISTRATIONS_SERVICE_URL = os.getenv("REGISTRATIONS_SERVICE_URL", "http://localhost:5005")
    CERTIFICATES_SERVICE_URL = os.getenv("CERTIFICATES_SERVICE_URL", "http://localhost:5006")