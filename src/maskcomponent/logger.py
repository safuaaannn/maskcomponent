"""
Structured JSON logging for maskcomponent service
"""
import logging
import json
import sys
from datetime import datetime
from typing import Any, Dict, Optional
from functools import wraps
import traceback


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging"""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON"""
        log_data: Dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        
        # Add extra fields if present
        if hasattr(record, "request_id"):
            log_data["request_id"] = record.request_id
        if hasattr(record, "user_id"):
            log_data["user_id"] = record.user_id
        if hasattr(record, "stage"):
            log_data["stage"] = record.stage
        if hasattr(record, "event"):
            log_data["event"] = record.event
        
        # Add exception info if present
        if record.exc_info:
            log_data["error"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "traceback": traceback.format_exception(*record.exc_info),
            }
        
        return json.dumps(log_data)


def setup_logger(name: str = "maskcomponent", level: str = "INFO") -> logging.Logger:
    """Setup structured JSON logger"""
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))
    
    # Remove existing handlers
    logger.handlers.clear()
    
    # Add console handler with JSON formatter
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONFormatter())
    logger.addHandler(handler)
    
    # Prevent propagation to root logger
    logger.propagate = False
    
    return logger


def log_with_context(
    request_id: Optional[str] = None,
    user_id: Optional[str] = None,
    stage: Optional[str] = None,
    event: Optional[str] = None,
):
    """Decorator to add context to log records"""
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            logger = logging.getLogger("maskcomponent")
            old_factory = logging.getLogRecordFactory()
            
            def record_factory(*args_factory, **kwargs_factory):
                record = old_factory(*args_factory, **kwargs_factory)
                if request_id:
                    record.request_id = request_id
                if user_id:
                    record.user_id = user_id
                if stage:
                    record.stage = stage
                if event:
                    record.event = event
                return record
            
            logging.setLogRecordFactory(record_factory)
            try:
                return await func(*args, **kwargs)
            finally:
                logging.setLogRecordFactory(old_factory)
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            logger = logging.getLogger("maskcomponent")
            old_factory = logging.getLogRecordFactory()
            
            def record_factory(*args_factory, **kwargs_factory):
                record = old_factory(*args_factory, **kwargs_factory)
                if request_id:
                    record.request_id = request_id
                if user_id:
                    record.user_id = user_id
                if stage:
                    record.stage = stage
                if event:
                    record.event = event
                return record
            
            logging.setLogRecordFactory(record_factory)
            try:
                return func(*args, **kwargs)
            finally:
                logging.setLogRecordFactory(old_factory)
        
        # Return appropriate wrapper based on function type
        import inspect
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    
    return decorator



