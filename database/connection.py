import psycopg2
from urllib.parse import urlparse

from config import *


def _connection_kwargs():
    if DATABASE_URL:
        parsed = urlparse(DATABASE_URL)
        kwargs = {
            "host": parsed.hostname,
            "database": (parsed.path or "/").lstrip("/"),
            "user": parsed.username,
            "password": parsed.password,
            "port": parsed.port or 5432,
        }
    else:
        kwargs = {
            "host": DB_HOST,
            "database": DB_NAME,
            "user": DB_USER,
            "password": DB_PASSWORD,
            "port": DB_PORT,
        }

    if DB_SSLMODE:
        kwargs["sslmode"] = DB_SSLMODE

    return kwargs


def get_connection():
    try:
        conn = psycopg2.connect(**_connection_kwargs())
        return conn
    except Exception as e:
        print("Erreur de connexion :", e)
        return None
