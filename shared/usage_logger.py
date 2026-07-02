"""
Sistema de logging de uso para YPF BI Monitor
Centraliza el tracking de todas las apps
"""

import json
import os
import socket
from pathlib import Path
from datetime import datetime
import uuid


def _get_username() -> str:
    """Get Windows username automatically"""
    return os.environ.get('USERNAME', os.environ.get('USER', 'unknown'))


def _get_hostname() -> str:
    """Get machine hostname"""
    try:
        return socket.gethostname()
    except Exception:
        return 'unknown'


class UsageLogger:
    """Logger centralizado para todas las apps de YPF BI Monitor"""

    def __init__(self, suite_name: str, version: str):
        self.suite_name = suite_name
        self.version = version
        self.session_id = str(uuid.uuid4())
        self.username = _get_username()
        self.hostname = _get_hostname()
        self.logs_dir = Path(__file__).parent.parent / "logs"
        self.logs_dir.mkdir(exist_ok=True)

        # Log session start
        self.log_event('session_started', {})

    def log_event(self, event_name: str, data: dict):
        """
        Log event to JSON file

        Args:
            event_name: Name of the event
            data: Dictionary with event data
        """
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

        # Append to daily log file
        log_file = self.logs_dir / f"usage_{datetime.now().strftime('%Y%m%d')}.jsonl"
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')

    def end_session(self):
        """Log session end"""
        self.log_event('session_ended', {})

    def log_file_analyzed(self, filename: str, file_size_mb: float = 0,
                          file_type: str = 'pbip', analysis_duration_seconds: float = 0,
                          score=None, recommendations_count: int = 0):
        """Compat method - delegates to log_event"""
        self.log_event('file_analyzed', {
            'filename': filename,
            'file_size_mb': file_size_mb,
            'file_type': file_type,
            'duration_seconds': analysis_duration_seconds,
            'score': score,
            'recommendations_count': recommendations_count
        })

    def log_dax_measures_analyzed(self, measures_count: int = 0, critical_count: int = 0,
                                   high_count: int = 0, medium_count: int = 0, low_count: int = 0,
                                   filename: str = None, avg_risk_score: float = None):
        """Compat method - delegates to log_event"""
        self.log_event('dax_analysis_completed', {
            'filename': filename,
            'measures_count': measures_count,
            'critical_count': critical_count,
            'high_count': high_count,
            'medium_count': medium_count,
            'low_count': low_count,
            'score': avg_risk_score
        })

    def get_all_events(self) -> list:
        """
        Read all logged events from all daily log files

        Returns:
            List of event dictionaries
        """
        events = []
        if not self.logs_dir.exists():
            return events

        for log_file in sorted(self.logs_dir.glob("usage_*.jsonl")):
            try:
                with open(log_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            try:
                                events.append(json.loads(line))
                            except json.JSONDecodeError:
                                continue
            except Exception:
                continue

        return events


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
