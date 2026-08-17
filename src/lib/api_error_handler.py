"""
API Error Handler for AI Chat and Eco-Tips
Provides comprehensive error handling, retry logic, and graceful degradation.
"""

import time
import logging
import json
from typing import Dict, Any, Optional, Callable, Tuple
from dataclasses import dataclass, field
from enum import Enum
import streamlit as st

logger = logging.getLogger(__name__)


class ErrorSeverity(Enum):
    """Error severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorType(Enum):
    """Types of API errors."""
    NETWORK = "network"
    TIMEOUT = "timeout"
    AUTH = "authentication"
    RATE_LIMIT = "rate_limit"
    SERVER = "server"
    CLIENT = "client"
    PARSE = "parse"
    UNKNOWN = "unknown"


@dataclass
class APIError:
    """Structured API error information."""
    error_type: ErrorType
    message: str
    severity: ErrorSeverity
    status_code: Optional[int] = None
    retryable: bool = True
    original_error: Optional[Exception] = None
    timestamp: float = field(default_factory=time.time)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary."""
        return {
            "error_type": self.error_type.value,
            "message": self.message,
            "severity": self.severity.value,
            "status_code": self.status_code,
            "retryable": self.retryable,
            "timestamp": self.timestamp
        }
    
    def to_user_message(self) -> str:
        """Convert error to user-friendly message."""
        messages = {
            ErrorType.NETWORK: "📡 Network connection issue. Please check your internet and try again.",
            ErrorType.TIMEOUT: "⏱️ The request took too long. Please try again.",
            ErrorType.AUTH: "🔑 Authentication failed. Please log in again.",
            ErrorType.RATE_LIMIT: "⏳ Too many requests. Please wait a moment and try again.",
            ErrorType.SERVER: "🖥️ Server issue. Our team has been notified. Please try again later.",
            ErrorType.CLIENT: "⚠️ Something went wrong. Please check your input and try again.",
            ErrorType.PARSE: "📄 Unable to process the response. Please try again.",
            ErrorType.UNKNOWN: "❌ An unexpected error occurred. Please try again."
        }
        return messages.get(self.error_type, "❌ An unexpected error occurred. Please try again.")


@dataclass
class RetryConfig:
    """Configuration for retry logic."""
    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 30.0
    backoff_factor: float = 2.0
    retryable_status_codes: Tuple[int, ...] = (408, 425, 429, 500, 502, 503, 504)


class APIErrorHandler:
    """Handles API errors with retry logic and graceful degradation."""
    
    def __init__(self, config: Optional[RetryConfig] = None):
        self.config = config or RetryConfig()
        self._error_history: list = []
        self._circuit_breaker = CircuitBreaker()
    
    def classify_error(self, error: Exception, status_code: Optional[int] = None) -> APIError:
        """Classify an error into a structured APIError."""
        error_str = str(error).lower()
        
        # Network errors
        if any(keyword in error_str for keyword in ["network", "connection", "refused", "unreachable", "dns"]):
            return APIError(
                error_type=ErrorType.NETWORK,
                message=str(error),
                severity=ErrorSeverity.HIGH,
                status_code=status_code,
                retryable=True,
                original_error=error
            )
        
        # Timeout errors
        if any(keyword in error_str for keyword in ["timeout", "timed out", "deadline"]):
            return APIError(
                error_type=ErrorType.TIMEOUT,
                message=str(error),
                severity=ErrorSeverity.MEDIUM,
                status_code=status_code,
                retryable=True,
                original_error=error
            )
        
        # Rate limit errors
        if status_code == 429 or "rate limit" in error_str:
            return APIError(
                error_type=ErrorType.RATE_LIMIT,
                message=str(error),
                severity=ErrorSeverity.MEDIUM,
                status_code=status_code,
                retryable=True,
                original_error=error
            )
        
        # Authentication errors
        if status_code in (401, 403) or any(keyword in error_str for keyword in ["auth", "unauthorized", "forbidden", "permission"]):
            return APIError(
                error_type=ErrorType.AUTH,
                message=str(error),
                severity=ErrorSeverity.HIGH,
                status_code=status_code,
                retryable=False,
                original_error=error
            )
        
        # Server errors
        if status_code in (500, 502, 503, 504):
            return APIError(
                error_type=ErrorType.SERVER,
                message=str(error),
                severity=ErrorSeverity.HIGH,
                status_code=status_code,
                retryable=True,
                original_error=error
            )
        
        # Client errors
        if status_code and 400 <= status_code < 500:
            return APIError(
                error_type=ErrorType.CLIENT,
                message=str(error),
                severity=ErrorSeverity.MEDIUM,
                status_code=status_code,
                retryable=False,
                original_error=error
            )
        
        # Parse errors
        if "parse" in error_str or "json" in error_str:
            return APIError(
                error_type=ErrorType.PARSE,
                message=str(error),
                severity=ErrorSeverity.LOW,
                status_code=status_code,
                retryable=True,
                original_error=error
            )
        
        # Unknown errors
        return APIError(
            error_type=ErrorType.UNKNOWN,
            message=str(error),
            severity=ErrorSeverity.MEDIUM,
            status_code=status_code,
            retryable=True,
            original_error=error
        )
    
    def is_retryable(self, api_error: APIError) -> bool:
        """Determine if an error is retryable."""
        if not api_error.retryable:
            return False
        if self._circuit_breaker.is_open():
            return False
        return True
    
    def get_retry_delay(self, attempt: int) -> float:
        """Calculate retry delay with exponential backoff and jitter."""
        delay = min(
            self.config.base_delay * (self.config.backoff_factor ** attempt),
            self.config.max_delay
        )
        # Add jitter
        import random
        jitter = random.uniform(0, 0.1 * delay)
        return delay + jitter
    
    def execute_with_retry(
        self,
        func: Callable,
        *args,
        error_message: str = "API request failed",
        show_error: bool = True,
        **kwargs
    ) -> Tuple[Any, Optional[APIError]]:
        """
        Execute a function with retry logic.
        
        Args:
            func: Function to execute
            *args: Positional arguments
            error_message: User-friendly error message
            show_error: Whether to show error in UI
            **kwargs: Keyword arguments
        
        Returns:
            Tuple of (result, error)
        """
        if self._circuit_breaker.is_open():
            error = APIError(
                error_type=ErrorType.SERVER,
                message="Service temporarily unavailable",
                severity=ErrorSeverity.HIGH,
                retryable=False
            )
            if show_error:
                self.show_error(error)
            return None, error
        
        for attempt in range(self.config.max_retries + 1):
            try:
                result = func(*args, **kwargs)
                self._circuit_breaker.record_success()
                return result, None
                
            except Exception as e:
                # Classify error
                api_error = self.classify_error(e)
                self._error_history.append(api_error)
                
                # Check if retryable
                if not self.is_retryable(api_error) or attempt >= self.config.max_retries:
                    if show_error:
                        self.show_error(api_error, custom_message=error_message)
                    return None, api_error
                
                # Wait before retry
                delay = self.get_retry_delay(attempt)
                logger.warning(
                    f"API call failed (attempt {attempt + 1}/{self.config.max_retries + 1}): "
                    f"{api_error.message}. Retrying in {delay:.2f}s"
                )
                
                if show_error:
                    self.show_retry_status(attempt + 1, self.config.max_retries + 1, delay)
                
                time.sleep(delay)
        
        return None, None
    
    def show_error(self, api_error: APIError, custom_message: str = None) -> None:
        """Display user-friendly error message."""
        if api_error.error_type == ErrorType.NETWORK:
            st.error(f"🌐 {custom_message or api_error.to_user_message()}")
        elif api_error.error_type == ErrorType.TIMEOUT:
            st.error(f"⏱️ {custom_message or api_error.to_user_message()}")
        elif api_error.error_type == ErrorType.AUTH:
            st.error(f"🔑 {custom_message or api_error.to_user_message()}")
        elif api_error.error_type == ErrorType.RATE_LIMIT:
            st.warning(f"⏳ {custom_message or api_error.to_user_message()}")
        elif api_error.error_type == ErrorType.SERVER:
            st.error(f"🖥️ {custom_message or api_error.to_user_message()}")
        else:
            st.error(f"❌ {custom_message or api_error.to_user_message()}")
    
    def show_retry_status(self, attempt: int, max_attempts: int, delay: float) -> None:
        """Show retry status."""
        st.info(f"🔄 Retrying... (Attempt {attempt}/{max_attempts})")
    
    def get_error_summary(self) -> Dict[str, Any]:
        """Get error summary statistics."""
        if not self._error_history:
            return {"total_errors": 0}
        
        error_counts = {}
        for error in self._error_history:
            error_type = error.error_type.value
            error_counts[error_type] = error_counts.get(error_type, 0) + 1
        
        return {
            "total_errors": len(self._error_history),
            "error_counts": error_counts,
            "circuit_state": self._circuit_breaker.state
        }
    
    def clear_history(self) -> None:
        """Clear error history."""
        self._error_history.clear()
        self._circuit_breaker.reset()


class CircuitBreaker:
    """Simple circuit breaker to prevent repeated calls to failing services."""
    
    STATES = {
        "CLOSED": "closed",
        "OPEN": "open",
        "HALF_OPEN": "half_open"
    }
    
    def __init__(self, failure_threshold: int = 5, timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failure_count = 0
        self.state = self.STATES["CLOSED"]
        self._last_failure_time = 0
    
    def is_open(self) -> bool:
        """Check if circuit is open."""
        if self.state == self.STATES["CLOSED"]:
            return False
        
        if self.state == self.STATES["OPEN"]:
            # Check if timeout has elapsed
            if time.time() - self._last_failure_time > self.timeout:
                self.state = self.STATES["HALF_OPEN"]
                return False
            return True
        
        return False
    
    def record_success(self) -> None:
        """Record a successful call."""
        self.failure_count = 0
        if self.state == self.STATES["HALF_OPEN"]:
            self.state = self.STATES["CLOSED"]
    
    def record_failure(self) -> None:
        """Record a failed call."""
        self.failure_count += 1
        self._last_failure_time = time.time()
        if self.failure_count >= self.failure_threshold:
            self.state = self.STATES["OPEN"]
    
    def reset(self) -> None:
        """Reset circuit breaker."""
        self.failure_count = 0
        self.state = self.STATES["CLOSED"]
        self._last_failure_time = 0


# ============================================================================
# GLOBAL INSTANCE
# ============================================================================

_error_handler: Optional[APIErrorHandler] = None


def get_error_handler() -> APIErrorHandler:
    """Get global error handler instance."""
    global _error_handler
    if _error_handler is None:
        _error_handler = APIErrorHandler()
    return _error_handler


def safe_api_call(func: Callable, *args, **kwargs) -> Tuple[Any, Optional[APIError]]:
    """
    Decorator for safe API calls with error handling.
    
    Usage:
        result, error = safe_api_call(api_function, arg1, arg2)
        if error:
            # Handle error
            pass
    """
    handler = get_error_handler()
    return handler.execute_with_retry(func, *args, **kwargs)


def with_error_handling(error_message: str = "API request failed"):
    """
    Decorator for functions that need error handling.
    
    Usage:
        @with_error_handling("Failed to get eco tips")
        def get_eco_tips():
            # API call
            pass
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            handler = get_error_handler()
            result, error = handler.execute_with_retry(
                func, *args, **kwargs,
                error_message=error_message
            )
            if error:
                return None, error
            return result, None
        return wrapper
    return decorator