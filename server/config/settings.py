import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Server settings
SERVER_HOST = ""
SERVER_PORT = 4321

# Atlas server address and password
ATLAS_SERVER_ADDRESS = os.getenv("ATLAS_SERVER_ADDRESS")
ATLAS_SERVER_PASSWORD = os.getenv("ATLAS_SERVER_PASSWORD")

# Textfully configuration
TEXTFULLY_PHONE_NUMBER = os.getenv("TEXTFULLY_PHONE_NUMBER")
TEXTFULLY_EMAIL_ADDRESS = os.getenv("TEXTFULLY_EMAIL_ADDRESS")

# Supabase configuration
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
SUPABASE_JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET")

# Redis configuration
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_SSL = os.getenv("REDIS_SSL", "False") == "True"
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD")

if REDIS_SSL:
    REDIS_URL = f"rediss://{REDIS_HOST}:{REDIS_PORT}"
else:
    REDIS_URL = f"redis://{REDIS_HOST}:{REDIS_PORT}"

# API server settings
API_HOST = "0.0.0.0"
API_PORT = 8000

# Featurebase Identity Verification
FEATUREBASE_IDENTITY_VERIFICATION_SECRET = os.getenv(
    "FEATUREBASE_IDENTITY_VERIFICATION_SECRET"
)
