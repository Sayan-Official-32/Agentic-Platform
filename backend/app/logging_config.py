# logging_config.py
# This module implements a highly customized logging system for the application.
# It makes use of python's 'contextvars' (context variables), which are similar to thread-local variables
# but designed specifically to support concurrent async/await tasks. This allows us to track metadata
# like session_id, user_id, current agent, and active route across async functions without passing them
# explicitly to every single log statement.

import contextvars
import json
import logging
import os
import sys
import uuid
from datetime import datetime
from logging.handlers import RotatingFileHandler
from typing import Any, Dict, Optional

# Colors class contains ANSI escape codes for colorizing console output,
# making logs significantly easier to scan and read during development.
class Colors:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    
    # Severity Level colors
    DEBUG = "\033[36m"      # Cyan
    INFO = "\033[32m"       # Green
    WARNING = "\033[33m"    # Yellow
    ERROR = "\033[31m"      # Red
    CRITICAL = "\033[35m"   # Magenta
    
    # Metadata component colors
    TIMESTAMP = "\033[90m"  # Gray
    LOGGER = "\033[94m"     # Blue
    SESSION = "\033[96m"    # Bright Cyan
    AGENT = "\033[95m"      # Bright Magenta
    ROUTE = "\033[93m"      # Bright Yellow

# _log_context holds contextual data for logs (like current session, user, etc.)
# using contextvars.ContextVar. Because FastAPI handles requests asynchronously,
# contextvars ensures each incoming HTTP request thread/task gets its own isolated context.
_log_context: contextvars.ContextVar[Dict[str, Any]] = contextvars.ContextVar(
    "log_context", default={}
)

# Load configuration values from environment variables or use sensible defaults.
LOG_FILE = os.getenv("LOG_FILE", "multi-agent-starter.log")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_HANDLERS = [
    item.strip()
    for item in os.getenv("LOG_HANDLERS", "console,file").split(",")
    if item.strip()
]
LOG_FORMAT_JSON = os.getenv("LOG_FORMAT_JSON", "false").lower() == "true"
MAX_LOG_SIZE = int(os.getenv("MAX_LOG_SIZE", str(10 * 1024 * 1024)))  # Default 10 MB per log file
BACKUP_COUNT = int(os.getenv("BACKUP_COUNT", "3"))  # Keeps last 3 rotated log files


class JSONFormatter(logging.Formatter):
    """
    JSONFormatter converts python log records into JSON strings.
    This is standard in production environments (like Datadog, ELK, GCP Cloud Logging)
    since structured JSON logs can be easily queried and filtered.
    """
    def format(self, record: logging.LogRecord) -> str:
        # Retrieve the current contextvars state
        context = _log_context.get()
        
        # Build the structured JSON payload
        payload: Dict[str, Any] = {
            "timestamp": datetime.utcfromtimestamp(record.created).isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "session_id": context.get("session_id", "-"),
            "transaction_id": context.get("transaction_id", "-"),
            "agent_type": context.get("agent_type", "-"),
            "user_id": context.get("user_id", "-"),
            "route": context.get("route", "-"),
        }

        # Include traceback details if an exception was caught
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        # Exclude standard properties we already processed or don't want in our JSON payload
        excluded_fields = {
            "name", "msg", "args", "created", "filename", "funcName", "levelname",
            "levelno", "lineno", "module", "msecs", "message", "pathname", "process",
            "processName", "relativeCreated", "thread", "threadName", "exc_info",
            "exc_text", "stack_info", "session_id", "transaction_id", "agent_type",
            "user_id", "route",
        }

        # Inject any dynamic extra parameters supplied in logger.info("...", extra={"foo": "bar"})
        for key, value in record.__dict__.items():
            if key not in excluded_fields and not key.startswith("_"):
                payload[key] = value

        return json.dumps(payload)
    

class ContextFormatter(logging.Formatter):
    """
    ContextFormatter injects our async context attributes (session_id, user_id, route, etc.)
    directly into the standard log record properties so that default text-based formatters
    can output them.
    """
    def format(self, record: logging.LogRecord) -> str:
        context = _log_context.get()
        record.session_id = context.get("session_id", "-")
        record.transaction_id = context.get("transaction_id", "-")
        record.agent_type = context.get("agent_type", "-")
        record.user_id = context.get("user_id", "-")
        record.route = context.get("route", "-")
        # Let the superclass standard format run with these newly attached fields
        return super().format(record)
    

class ColoredFormatter(ContextFormatter):
    """
    ColoredFormatter formats log lines as colorized text for the local console.
    Extends ContextFormatter to fetch contextual info, and then surrounds segments
    with ANSI escape codes for colored terminal visualization.
    """
    
    # Map severity levels to Colors
    LEVEL_COLORS = {
        'DEBUG': Colors.DEBUG,
        'INFO': Colors.INFO,
        'WARNING': Colors.WARNING,
        'ERROR': Colors.ERROR,
        'CRITICAL': Colors.CRITICAL,
    }
    
    def format(self, record: logging.LogRecord) -> str:
        context = _log_context.get()
        record.session_id = context.get("session_id", "-")
        record.transaction_id = context.get("transaction_id", "-")
        record.agent_type = context.get("agent_type", "-")
        record.user_id = context.get("user_id", "-")
        record.route = context.get("route", "-")
        
        level_color = self.LEVEL_COLORS.get(record.levelname, Colors.RESET)
        
        # Colorize components
        timestamp = self.formatTime(record, "%Y-%m-%d %H:%M:%S")
        colored_timestamp = f"{Colors.TIMESTAMP}{timestamp}{Colors.RESET}"
        colored_level = f"{level_color}{record.levelname:<8}{Colors.RESET}"
        colored_logger = f"{Colors.LOGGER}{record.name}{Colors.RESET}"
        
        # Shorten UUIDs to first 8 characters for console brevity
        session_short = record.session_id[:8] if record.session_id != "-" else "-"
        txn_short = record.transaction_id[:8] if record.transaction_id != "-" else "-"
        
        colored_context = (
            f"[{Colors.SESSION}session={session_short}{Colors.RESET}] "
            f"[{Colors.SESSION}txn={txn_short}{Colors.RESET}] "
            f"[{Colors.AGENT}agent={record.agent_type}{Colors.RESET}] "
            f"[user={record.user_id}] "
            f"[{Colors.ROUTE}route={record.route}{Colors.RESET}]"
        )
        
        message = record.getMessage()
        
        # Build final colored line
        log_line = (
            f"{colored_timestamp} - {colored_level} - "
            f"[{record.filename}:{record.lineno}] - {colored_logger} - "
            f"{colored_context} - {message}"
        )
        
        # Append formatted exception stack trace if present
        if record.exc_info:
            log_line += "\n" + self.formatException(record.exc_info)
        
        return log_line
    
    
class ContextFilter(logging.Filter):
    """
    ContextFilter is a logging filter. Filters can either block log records or enrich them.
    This filter enriches every LogRecord by injecting context details if not already present.
    """
    def filter(self, record: logging.LogRecord) -> bool:
        context = _log_context.get()
        record.session_id = context.get("session_id", "-")
        record.transaction_id = context.get("transaction_id", "-")
        record.agent_type = context.get("agent_type", "-")
        record.user_id = context.get("user_id", "-")
        record.route = context.get("route", "-")
        return True


# --- Helper methods to modify the active request/thread context ---

def set_log_context(
    thread_id: str,
    agent_type: Optional[str] = None,
    user_id: Optional[str] = None,
    route: Optional[str] = None,
) -> None:
    """Sets/replaces the entire contextvar dictionary for the current execution flow."""
    context: Dict[str, Any] = {
        "session_id": thread_id,
        "transaction_id": str(uuid.uuid4()), # Generate a unique transaction id for tracing
    }
    if agent_type:
        context["agent_type"] = agent_type
    if user_id:
        context["user_id"] = user_id
    if route:
        context["route"] = route
    _log_context.set(context)
    
def update_log_context(**kwargs: Any) -> None:
    """Updates the existing context variables (e.g. updating route after supervisor routing)."""
    current_context = _log_context.get().copy()
    current_context.update(kwargs)
    _log_context.set(current_context)
    
def clear_log_context() -> None:
    """Resets context back to empty (useful at request termination)."""
    _log_context.set({})


def _get_log_level() -> int:
    """Converts LOG_LEVEL string (like 'INFO') to the logging module's internal integer value."""
    try:
        return getattr(logging, LOG_LEVEL.upper())
    except AttributeError:
        return logging.INFO


def _create_file_handler(formatter: logging.Formatter) -> logging.Handler:
    """Creates a thread-safe rotating file handler that writes logs to disk."""
    os.makedirs("logs", exist_ok=True)
    handler = RotatingFileHandler(
        os.path.join("logs", LOG_FILE),
        maxBytes=MAX_LOG_SIZE,
        backupCount=BACKUP_COUNT,
    )
    handler.setFormatter(formatter)
    return handler

def configure_root_logger() -> logging.Logger:
    """
    Configures python's root logger.
    Removes existing handlers, attaches ContextFilter and registers selected handlers (file and console).
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(_get_log_level())

    # Flush out standard handlers to avoid duplicate log outputs
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    for current_filter in root_logger.filters[:]:
        root_logger.removeFilter(current_filter)

    # Register our ContextFilter to attach context variables to all logs
    root_logger.addFilter(ContextFilter())

    # Pick the base formatter
    formatter: logging.Formatter
    if LOG_FORMAT_JSON:
        formatter = JSONFormatter()
    else:
        formatter = ContextFormatter(
            "%(asctime)s - %(levelname)-8s - [%(filename)s:%(lineno)d] - %(name)s - "
            "[session=%(session_id)s] [txn=%(transaction_id)s] [agent=%(agent_type)s] "
            "[user=%(user_id)s] [route=%(route)s] - %(message)s"
        )

    # Attach file writing handler if configured
    if "file" in LOG_HANDLERS:
        root_logger.addHandler(_create_file_handler(formatter))

    # Attach terminal writing handler if configured
    if "console" in LOG_HANDLERS:
        console_handler = logging.StreamHandler(sys.stdout)
        # Use colored formatting only if writing to an interactive terminal (isatty) and JSON is not requested
        if sys.stdout.isatty() and not LOG_FORMAT_JSON:
            console_formatter = ColoredFormatter(
                "%(asctime)s - %(levelname)-8s - [%(filename)s:%(lineno)d] - %(name)s - "
                "[session=%(session_id)s] [txn=%(transaction_id)s] [agent=%(agent_type)s] "
                "[user=%(user_id)s] [route=%(route)s] - %(message)s"
            )
            console_handler.setFormatter(console_formatter)
        else:
            console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

    return root_logger

def configure_uvicorn_logging() -> bool:
    """
    Hooks our custom logging configuration into the web server (Uvicorn).
    This ensures that internal uvicorn server startup and route logs follow our formatting rules.
    """
    configure_root_logger()

    # Route uvicorn logs through the root logger by removing their default handlers
    for logger_name in ["uvicorn", "uvicorn.error", "uvicorn.access"]:
        logger = logging.getLogger(logger_name)
        logger.propagate = True
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)

    return True

