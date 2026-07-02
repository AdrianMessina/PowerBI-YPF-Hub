"""
Sistema de logging de uso para YPF BI Monitor
Soporta múltiples backends: Archivos locales, SQLite, PostgreSQL
"""

import json
import os
import socket
from pathlib import Path
from datetime import datetime
import uuid
from typing import Optional, Dict, Any, List
from enum import Enum


class LogBackend(Enum):
    """Tipos de backend de almacenamiento de logs"""
    FILE = "file"  # Archivos JSONL locales (default)
    SQLITE = "sqlite"  # Base de datos SQLite
    POSTGRES = "postgres"  # PostgreSQL (producción cloud)


class LogConfig:
    """Configuración de logging desde variables de entorno"""

    def __init__(self):
        # Backend de almacenamiento
        self.backend = LogBackend(os.getenv('LOG_BACKEND', 'file').lower())

        # File backend config
        self.file_log_dir = os.getenv('LOG_FILE_DIR', '')  # Default: logs/ en raíz del proyecto

        # SQLite backend config
        self.sqlite_db_path = os.getenv('LOG_SQLITE_PATH', 'logs/usage.db')

        # PostgreSQL backend config
        self.postgres_host = os.getenv('LOG_POSTGRES_HOST', 'localhost')
        self.postgres_port = int(os.getenv('LOG_POSTGRES_PORT', '5432'))
        self.postgres_db = os.getenv('LOG_POSTGRES_DB', 'ypf_bi_monitor')
        self.postgres_user = os.getenv('LOG_POSTGRES_USER', '')
        self.postgres_password = os.getenv('LOG_POSTGRES_PASSWORD', '')
        self.postgres_table = os.getenv('LOG_POSTGRES_TABLE', 'usage_events')

        # General config
        self.enabled = os.getenv('LOG_ENABLED', 'true').lower() == 'true'


def _get_username() -> str:
    """Get current username (Windows or Unix)"""
    return os.environ.get('USERNAME', os.environ.get('USER', 'unknown'))


def _get_hostname() -> str:
    """Get machine hostname"""
    try:
        return socket.gethostname()
    except Exception:
        return 'unknown'


class FileLogBackend:
    """Backend que almacena logs en archivos JSONL"""

    def __init__(self, log_dir: str):
        if not log_dir:
            # Default: logs/ en raíz del proyecto
            self.logs_dir = Path(__file__).parent.parent / "logs"
        else:
            self.logs_dir = Path(log_dir)

        self.logs_dir.mkdir(exist_ok=True, parents=True)

    def log_event(self, event: Dict[str, Any]):
        """Escribir evento a archivo JSONL diario"""
        log_file = self.logs_dir / f"usage_{datetime.now().strftime('%Y%m%d')}.jsonl"
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(event, ensure_ascii=False) + '\n')

    def get_events(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Leer todos los eventos desde archivos JSONL"""
        all_events = []
        log_files = sorted(self.logs_dir.glob("usage_*.jsonl"))

        for log_file in log_files:
            try:
                with open(log_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        if line.strip():
                            event = json.loads(line)
                            all_events.append(event)
            except Exception as e:
                print(f"Error reading {log_file.name}: {e}")

        # Ordenar por timestamp desc
        all_events.sort(key=lambda x: x.get('timestamp', ''), reverse=True)

        if limit:
            return all_events[:limit]
        return all_events


class SQLiteLogBackend:
    """Backend que almacena logs en SQLite"""

    def __init__(self, db_path: str):
        try:
            import sqlite3
        except ImportError:
            raise ImportError("SQLite backend requires sqlite3 (should be included with Python)")

        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(exist_ok=True, parents=True)

        # Inicializar base de datos
        self._init_db()

    def _init_db(self):
        """Crear tabla si no existe"""
        import sqlite3

        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS usage_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                session_id TEXT NOT NULL,
                username TEXT NOT NULL,
                hostname TEXT NOT NULL,
                suite TEXT NOT NULL,
                version TEXT NOT NULL,
                event TEXT NOT NULL,
                data TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Índices para mejorar performance
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON usage_events(timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_username ON usage_events(username)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_event ON usage_events(event)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_session_id ON usage_events(session_id)")

        conn.commit()
        conn.close()

    def log_event(self, event: Dict[str, Any]):
        """Escribir evento a SQLite"""
        import sqlite3

        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO usage_events
            (timestamp, session_id, username, hostname, suite, version, event, data)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            event['timestamp'],
            event['session_id'],
            event['username'],
            event['hostname'],
            event['suite'],
            event['version'],
            event['event'],
            json.dumps(event['data'], ensure_ascii=False)
        ))

        conn.commit()
        conn.close()

    def get_events(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Leer eventos desde SQLite"""
        import sqlite3

        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        query = "SELECT timestamp, session_id, username, hostname, suite, version, event, data FROM usage_events ORDER BY timestamp DESC"
        if limit:
            query += f" LIMIT {limit}"

        cursor.execute(query)
        rows = cursor.fetchall()
        conn.close()

        events = []
        for row in rows:
            events.append({
                'timestamp': row[0],
                'session_id': row[1],
                'username': row[2],
                'hostname': row[3],
                'suite': row[4],
                'version': row[5],
                'event': row[6],
                'data': json.loads(row[7]) if row[7] else {}
            })

        return events


class PostgresLogBackend:
    """Backend que almacena logs en PostgreSQL"""

    def __init__(self, config: LogConfig):
        try:
            import psycopg2
        except ImportError:
            raise ImportError("PostgreSQL backend requires psycopg2. Install: pip install psycopg2-binary")

        self.config = config
        self._init_db()

    def _get_connection(self):
        """Crear conexión a PostgreSQL"""
        import psycopg2

        return psycopg2.connect(
            host=self.config.postgres_host,
            port=self.config.postgres_port,
            database=self.config.postgres_db,
            user=self.config.postgres_user,
            password=self.config.postgres_password
        )

    def _init_db(self):
        """Crear tabla si no existe"""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS {self.config.postgres_table} (
                id SERIAL PRIMARY KEY,
                timestamp TIMESTAMP NOT NULL,
                session_id VARCHAR(255) NOT NULL,
                username VARCHAR(255) NOT NULL,
                hostname VARCHAR(255) NOT NULL,
                suite VARCHAR(255) NOT NULL,
                version VARCHAR(50) NOT NULL,
                event VARCHAR(255) NOT NULL,
                data JSONB NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Índices
        cursor.execute(f"CREATE INDEX IF NOT EXISTS idx_{self.config.postgres_table}_timestamp ON {self.config.postgres_table}(timestamp)")
        cursor.execute(f"CREATE INDEX IF NOT EXISTS idx_{self.config.postgres_table}_username ON {self.config.postgres_table}(username)")
        cursor.execute(f"CREATE INDEX IF NOT EXISTS idx_{self.config.postgres_table}_event ON {self.config.postgres_table}(event)")
        cursor.execute(f"CREATE INDEX IF NOT EXISTS idx_{self.config.postgres_table}_session_id ON {self.config.postgres_table}(session_id)")

        conn.commit()
        conn.close()

    def log_event(self, event: Dict[str, Any]):
        """Escribir evento a PostgreSQL"""
        import psycopg2.extras

        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(f"""
            INSERT INTO {self.config.postgres_table}
            (timestamp, session_id, username, hostname, suite, version, event, data)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            event['timestamp'],
            event['session_id'],
            event['username'],
            event['hostname'],
            event['suite'],
            event['version'],
            event['event'],
            psycopg2.extras.Json(event['data'])
        ))

        conn.commit()
        conn.close()

    def get_events(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Leer eventos desde PostgreSQL"""
        conn = self._get_connection()
        cursor = conn.cursor()

        query = f"SELECT timestamp, session_id, username, hostname, suite, version, event, data FROM {self.config.postgres_table} ORDER BY timestamp DESC"
        if limit:
            query += f" LIMIT {limit}"

        cursor.execute(query)
        rows = cursor.fetchall()
        conn.close()

        events = []
        for row in rows:
            events.append({
                'timestamp': row[0].isoformat() if hasattr(row[0], 'isoformat') else str(row[0]),
                'session_id': row[1],
                'username': row[2],
                'hostname': row[3],
                'suite': row[4],
                'version': row[5],
                'event': row[6],
                'data': row[7] if isinstance(row[7], dict) else {}
            })

        return events


class UsageLogger:
    """Logger centralizado con soporte para múltiples backends"""

    def __init__(self, suite_name: str, version: str, config: Optional[LogConfig] = None):
        self.config = config or LogConfig()
        self.suite_name = suite_name
        self.version = version
        self.session_id = str(uuid.uuid4())
        self.username = _get_username()
        self.hostname = _get_hostname()

        # Inicializar backend según configuración
        if not self.config.enabled:
            self.backend = None
        elif self.config.backend == LogBackend.FILE:
            self.backend = FileLogBackend(self.config.file_log_dir)
        elif self.config.backend == LogBackend.SQLITE:
            self.backend = SQLiteLogBackend(self.config.sqlite_db_path)
        elif self.config.backend == LogBackend.POSTGRES:
            self.backend = PostgresLogBackend(self.config)
        else:
            raise ValueError(f"Unknown log backend: {self.config.backend}")

        # Log session start
        if self.backend:
            self.log_event('session_started', {})

    def log_event(self, event_name: str, data: dict):
        """
        Log event to configured backend

        Args:
            event_name: Name of the event
            data: Dictionary with event data
        """
        if not self.backend:
            return  # Logging disabled

        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'session_id': self.session_id,
            'username': self.username,
            'hostname': self.hostname,
            'suite': self.suite_name,
            'version': self.version,
            'event': event_name,
            'data': data
        }

        try:
            self.backend.log_event(log_entry)
        except Exception as e:
            # No fallar si falla el logging
            print(f"Warning: Failed to log event: {e}")

    def end_session(self):
        """Log session end"""
        if self.backend:
            self.log_event('session_ended', {})

    def get_all_events(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Obtener todos los eventos desde el backend

        Args:
            limit: Número máximo de eventos a retornar

        Returns:
            Lista de eventos
        """
        if not self.backend:
            return []

        try:
            return self.backend.get_events(limit)
        except Exception as e:
            print(f"Error getting events: {e}")
            return []


def get_logger() -> UsageLogger:
    """
    Get or create logger instance from Streamlit session state

    Returns:
        UsageLogger instance
    """
    import streamlit as st
    if 'logger' not in st.session_state:
        st.session_state.logger = UsageLogger("YPF_BI_Monitor", "1.0")
    return st.session_state.logger
