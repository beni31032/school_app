from urllib.parse import urlparse

import psycopg2
from psycopg2 import extensions
from psycopg2.pool import SimpleConnectionPool

from config import *


_POOL = None


class _PooledConnection:
    def __init__(self, pool, raw_conn):
        self._pool = pool
        self._raw_conn = raw_conn
        self._returned = False

    def close(self):
        if self._returned:
            return

        try:
            status = self._raw_conn.get_transaction_status()
            if status != extensions.TRANSACTION_STATUS_IDLE:
                self._raw_conn.rollback()
        except Exception:
            try:
                self._pool.putconn(self._raw_conn, close=True)
            finally:
                self._returned = True
            return

        self._pool.putconn(self._raw_conn)
        self._returned = True

    def __getattr__(self, item):
        return getattr(self._raw_conn, item)


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
    if DB_CONNECT_TIMEOUT:
        kwargs["connect_timeout"] = DB_CONNECT_TIMEOUT

    return kwargs


def _get_pool():
    global _POOL
    if _POOL is None:
        _POOL = SimpleConnectionPool(
            minconn=DB_POOL_MINCONN,
            maxconn=DB_POOL_MAXCONN,
            **_connection_kwargs(),
        )
    return _POOL


def get_connection():
    try:
        pool = _get_pool()
        raw_conn = pool.getconn()

        if raw_conn.closed:
            pool.putconn(raw_conn, close=True)
            raw_conn = psycopg2.connect(**_connection_kwargs())

        return _PooledConnection(pool, raw_conn)
    except Exception as e:
        print("Erreur de connexion :", e)
        return None
