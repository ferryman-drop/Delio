
import logging
import json
from datetime import datetime
from logging.handlers import RotatingFileHandler
import os
import sys

class JSONFormatter(logging.Formatter):
    """
    Formatter that outputs JSON strings for structured logging.
    Includes trace_id if available in the record.
    """
    def format(self, record):
        log_record = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
            "line": record.lineno,
            "trace_id": getattr(record, "trace_id", None) or self._get_context_trace()
        }
        
        # Add exception info if present
        if record.exc_info:
            log_record["exception"] = self.formatException(record.exc_info)
            
        return json.dumps(log_record)

    def _get_context_trace(self):
        try:
            from core.context import trace_var
            return trace_var.get()
        except (ImportError, LookupError):
            return None

def setup_logging(log_file: str, level: str = "INFO"):
    """
    Configures the root logger with JSON file handler and Console handler.
    """
    # Ensure log directory exists
    log_dir = os.path.dirname(log_file)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir)

    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper()))
    
    # Clear existing handlers to avoid duplicates
    if root_logger.handlers:
        root_logger.handlers = []

    # 1. JSON File Handler
    file_handler = RotatingFileHandler(
        log_file, 
        maxBytes=10*1024*1024, # 10MB
        backupCount=5
    )
    file_handler.setFormatter(JSONFormatter())
    root_logger.addHandler(file_handler)
    
    # 2. Console Handler (Human readable)
    console_handler = logging.StreamHandler(sys.stdout)
    console_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)
    
    # Mute noisy libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    
    return root_logger
