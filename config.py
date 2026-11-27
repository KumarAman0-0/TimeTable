"""Application configuration — loaded from .env via python-dotenv."""
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///timetable.db")
SECRET_KEY   = os.getenv("SECRET_KEY", "change-me-in-production")
FLASK_ENV    = os.getenv("FLASK_ENV", "development")
DEBUG        = FLASK_ENV == "development"

# Solver defaults
DEFAULT_SOLVER     = os.getenv("DEFAULT_SOLVER", "heuristic")  # heuristic | cpsat
CPSAT_TIME_LIMIT   = int(os.getenv("CPSAT_TIME_LIMIT", "60"))  # seconds
HEURISTIC_TRIES    = int(os.getenv("HEURISTIC_TRIES", "400"))
OUTPUT_DIR         = os.getenv("OUTPUT_DIR", "outputs")
