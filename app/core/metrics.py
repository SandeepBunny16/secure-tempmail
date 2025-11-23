"""
Prometheus Metrics

Defines application metrics for monitoring:
- Request counters
- Duration histograms
- Gauge metrics
- Custom business metrics
"""

from prometheus_client import Counter, Histogram, Gauge, Info


# ===================================
# HTTP Metrics
# ===================================

requests_total = Counter(
    "tempmail_requests_total",
    "Total number of HTTP requests",
    ["method", "endpoint", "status"],
)

requests_duration = Histogram(
    "tempmail_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint"],
    buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
)

active_requests = Gauge(
    "tempmail_active_requests",
    "Number of active HTTP requests",
)


# ===================================
# Business Metrics
# ===================================

inboxes_total = Counter(
    "tempmail_inboxes_total",
    "Total number of inboxes created",
)

inboxes_active = Gauge(
    "tempmail_inboxes_active",
    "Number of currently active inboxes",
)

inboxes_expired = Counter(
    "tempmail_inboxes_expired",
    "Total number of expired inboxes",
)

messages_total = Counter(
    "tempmail_messages_total",
    "Total number of messages received",
)

messages_active = Gauge(
    "tempmail_messages_active",
    "Number of messages currently stored",
)

messages_size_bytes = Histogram(
    "tempmail_message_size_bytes",
    "Message size in bytes",
    buckets=[1024, 10240, 102400, 1024000, 10240000],  # 1KB to 10MB
)


# ===================================
# SMTP Metrics
# ===================================

smtp_connections_total = Counter(
    "tempmail_smtp_connections_total",
    "Total number of SMTP connections",
)

smtp_messages_received = Counter(
    "tempmail_smtp_messages_received",
    "Total number of messages received via SMTP",
    ["status"],  # accepted, rejected, error
)

smtp_messages_rejected = Counter(
    "tempmail_smtp_messages_rejected",
    "Total number of rejected SMTP messages",
    ["reason"],  # invalid_recipient, quota_exceeded, too_large
)

smtp_processing_duration = Histogram(
    "tempmail_smtp_processing_duration_seconds",
    "SMTP message processing duration in seconds",
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 5.0],
)


# ===================================
# Database Metrics
# ===================================

db_connections_active = Gauge(
    "tempmail_db_connections_active",
    "Number of active database connections",
)

db_query_duration = Histogram(
    "tempmail_db_query_duration_seconds",
    "Database query duration in seconds",
    ["operation"],  # select, insert, update, delete
    buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0],
)

db_errors_total = Counter(
    "tempmail_db_errors_total",
    "Total number of database errors",
    ["operation"],
)


# ===================================
# Redis Metrics
# ===================================

redis_operations_total = Counter(
    "tempmail_redis_operations_total",
    "Total number of Redis operations",
    ["operation"],  # get, set, delete, incr
)

redis_operation_duration = Histogram(
    "tempmail_redis_operation_duration_seconds",
    "Redis operation duration in seconds",
    ["operation"],
    buckets=[0.001, 0.005, 0.01, 0.05, 0.1],
)

redis_errors_total = Counter(
    "tempmail_redis_errors_total",
    "Total number of Redis errors",
    ["operation"],
)


# ===================================
# Worker Metrics
# ===================================

worker_cleanup_runs_total = Counter(
    "tempmail_worker_cleanup_runs_total",
    "Total number of cleanup worker runs",
)

worker_cleanup_duration = Histogram(
    "tempmail_worker_cleanup_duration_seconds",
    "Cleanup worker run duration in seconds",
    buckets=[1.0, 5.0, 10.0, 30.0, 60.0, 300.0],
)

worker_inboxes_cleaned = Counter(
    "tempmail_worker_inboxes_cleaned",
    "Total number of inboxes cleaned by worker",
)

worker_messages_cleaned = Counter(
    "tempmail_worker_messages_cleaned",
    "Total number of messages cleaned by worker",
)

worker_errors_total = Counter(
    "tempmail_worker_errors_total",
    "Total number of worker errors",
    ["worker"],
)


# ===================================
# Application Info
# ===================================

app_info = Info(
    "tempmail_app",
    "Application information",
)

# Set application info
app_info.info({
    "version": "1.0.0",
    "name": "SecureTempMail",
})


# ===================================
# Helper Functions
# ===================================

def record_request(method: str, endpoint: str, status: int, duration: float):
    """
    Record HTTP request metrics.
    
    Args:
        method: HTTP method
        endpoint: Endpoint path
        status: HTTP status code
        duration: Request duration in seconds
    """
    requests_total.labels(method=method, endpoint=endpoint, status=status).inc()
    requests_duration.labels(method=method, endpoint=endpoint).observe(duration)


def record_inbox_created():
    """Record inbox creation."""
    inboxes_total.inc()
    inboxes_active.inc()


def record_inbox_expired():
    """Record inbox expiration."""
    inboxes_expired.inc()
    inboxes_active.dec()


def record_message_received(size_bytes: int):
    """
    Record message reception.
    
    Args:
        size_bytes: Message size in bytes
    """
    messages_total.inc()
    messages_active.inc()
    messages_size_bytes.observe(size_bytes)


def record_message_deleted():
    """Record message deletion."""
    messages_active.dec()


def record_smtp_connection():
    """Record SMTP connection."""
    smtp_connections_total.inc()


def record_smtp_message(status: str, duration: float):
    """
    Record SMTP message processing.
    
    Args:
        status: Message status (accepted, rejected, error)
        duration: Processing duration in seconds
    """
    smtp_messages_received.labels(status=status).inc()
    smtp_processing_duration.observe(duration)


def record_smtp_rejection(reason: str):
    """
    Record SMTP message rejection.
    
    Args:
        reason: Rejection reason
    """
    smtp_messages_rejected.labels(reason=reason).inc()