import psycopg2
from psycopg2.extras import RealDictCursor


def get_connection():
    return psycopg2.connect(
        host="localhost",
        database="saas_audit",
        user="postgres",
        password="vaishvee",
        cursor_factory=RealDictCursor
    )
