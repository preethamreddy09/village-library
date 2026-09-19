import os
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

def get_database_uri():
    url = os.environ.get("DATABASE_URL")
    if not url:
        # Local fallback: SQLite file, same as before
        return "sqlite:///" + os.path.join(BASE_DIR, "instance", "library.db")
    # Fix older-style Postgres URLs so SQLAlchemy accepts them
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    return url

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "fallback-secret-key")
    ADMIN_PASSCODE = os.environ.get("ADMIN_PASSCODE", "1234")

    SUPABASE_URL = os.environ.get("SUPABASE_URL")
    SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")
    SUPABASE_BUCKET = "book-images"

    SQLALCHEMY_DATABASE_URI = get_database_uri()
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "uploads")
    ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}