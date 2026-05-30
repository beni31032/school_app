import os


DATABASE_URL = os.getenv("DATABASE_URL", "").strip()

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_NAME = os.getenv("DB_NAME", "school_management")
DB_USER = os.getenv("DB_USER", "beni")
DB_PASSWORD = os.getenv("DB_PASSWORD", "orbitb4")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_SSLMODE = os.getenv("DB_SSLMODE", "").strip()
