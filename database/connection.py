"""
MySQL connection pool with auto-reconnect and context manager support.
"""

import mysql.connector
from mysql.connector import pooling, Error as MySQLError
from config import Config


class DatabaseConnection:
    """Manages a MySQL connection pool for the application."""

    _pool = None

    @classmethod
    def initialize_pool(cls, pool_size: int = 5):
        """Create the connection pool. Call once at app startup."""
        if cls._pool is not None:
            return
        try:
            cls._pool = pooling.MySQLConnectionPool(
                pool_name="chatbot_pool",
                pool_size=pool_size,
                pool_reset_session=True,
                host=Config.MYSQL_HOST,
                port=Config.MYSQL_PORT,
                user=Config.MYSQL_USER,
                password=Config.MYSQL_PASSWORD,
                database=Config.MYSQL_DATABASE,
                charset="utf8mb4",
                collation="utf8mb4_unicode_ci",
                autocommit=False,
            )
            print(f"[DB] Connection pool created  (size={pool_size})")
        except MySQLError as e:
            print(f"[DB] Failed to create pool: {e}")
            raise

    @classmethod
    def get_connection(cls):
        """Get a connection from the pool."""
        if cls._pool is None:
            cls.initialize_pool()
        return cls._pool.get_connection()

    @classmethod
    def execute_query(cls, query: str, params: tuple = None, fetch: bool = True):
        """
        Execute a single query.
        - fetch=True  → returns list of dicts
        - fetch=False → returns lastrowid (for INSERT) or rowcount
        """
        conn = cls.get_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(query, params)
            if fetch:
                result = cursor.fetchall()
            else:
                conn.commit()
                result = cursor.lastrowid if cursor.lastrowid else cursor.rowcount
            return result
        except MySQLError as e:
            conn.rollback()
            print(f"[DB] Query error: {e}")
            raise
        finally:
            cursor.close()
            conn.close()

    @classmethod
    def execute_many(cls, query: str, data_list: list):
        """Execute a query with multiple parameter sets."""
        conn = cls.get_connection()
        cursor = conn.cursor()
        try:
            cursor.executemany(query, data_list)
            conn.commit()
            return cursor.rowcount
        except MySQLError as e:
            conn.rollback()
            print(f"[DB] Batch query error: {e}")
            raise
        finally:
            cursor.close()
            conn.close()

    @classmethod
    def run_schema(cls, schema_path: str):
        """Execute a .sql schema file to bootstrap tables."""
        conn = cls.get_connection()
        cursor = conn.cursor()
        try:
            with open(schema_path, "r", encoding="utf-8") as f:
                sql = f.read()
            for statement in sql.split(";"):
                stmt = statement.strip()
                if stmt:
                    cursor.execute(stmt)
            conn.commit()
            print("[DB] Schema applied successfully")
        except MySQLError as e:
            conn.rollback()
            print(f"[DB] Schema error: {e}")
            raise
        finally:
            cursor.close()
            conn.close()
