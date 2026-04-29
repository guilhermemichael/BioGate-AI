from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest

REQUEST_COUNT = Counter(
    "biogate_http_requests_total",
    "Total HTTP requests processed by BioGate AI.",
    ["method", "path", "status"],
)

REQUEST_LATENCY = Histogram(
    "biogate_http_request_duration_seconds",
    "Latency of HTTP requests handled by BioGate AI.",
    ["method", "path"],
)

WEBSOCKET_CONNECTIONS = Gauge(
    "biogate_websocket_connections",
    "Active websocket connections for biometric realtime sessions.",
)


def render_metrics() -> tuple[bytes, str]:
    return generate_latest(), CONTENT_TYPE_LATEST
