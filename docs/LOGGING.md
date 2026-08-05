# Secure Logging Guide

EcoBuddy AI centralizes log redaction and correlation IDs so logs remain useful
without exposing credentials, personal data, or uploaded content.

## Setup

Existing startup calls remain compatible:

```python
from logging_config import setup_logging

setup_logging()
```

Text is the default format. Enable structured JSON with:

```powershell
$env:LOG_FORMAT = "json"
streamlit run app.py
```

## Correlation IDs

Use one operation ID for related logs:

```python
import logging
from log_sanitizer import operation_context

logger = logging.getLogger(__name__)

with operation_context() as operation_id:
    logger.info(
        "Assessment started",
        extra={
            "event": "assessment_started",
            "assessment_id": 42,
        },
    )
    run_assessment()
    logger.info(
        "Assessment completed",
        extra={
            "event": "assessment_completed",
            "assessment_id": 42,
        },
    )
```

Both records include the same `operation_id`. Independent contexts get
different IDs.

## Automatic redaction

The filter recursively redacts sensitive keys, including:

```text
api_key
authorization
access_token
refresh_token
password
password_hash
secret
otp
jwt
private_key
database_url
cookie
session
```

It also redacts common string patterns:

```text
Authorization: Bearer [REDACTED]
api_key=[REDACTED]
password=[REDACTED]
postgresql://[REDACTED]
?token=[REDACTED]
```

Emails are masked by default:

```text
jidnyasa@example.com -> j***@example.com
```

## Structured context

Use safe fields through `extra`:

```python
logger.error(
    "Background task failed",
    extra={
        "event": "task_failed",
        "task_id": task.task_id,
        "attempt_count": task.attempt_count,
    },
)
```

Nested dictionaries and lists are sanitized without mutating the original
objects.

## Exceptions

Normal tracebacks remain available, while sensitive values in the complete
rendered traceback are redacted:

```python
try:
    call_provider()
except Exception:
    logger.exception(
        "Provider call failed",
        extra={"event": "provider_failed"},
    )
```

Do not place full uploaded documents, raw provider responses, passwords,
tokens, or OTPs in exception messages.

## Contributor checklist

- Log IDs and counts instead of full records.
- Never log passwords, hashes, tokens, OTPs, or authorization headers.
- Avoid complete uploaded files and extracted document content.
- Wrap multi-step work in `operation_context()`.
- Use stable event names through `extra={"event": "..."}`.
- Keep email masking enabled in shared environments.
- Add tests for every new sensitive field or pattern.

## Tests

```powershell
python -m pytest test_logging_security.py -v
```
