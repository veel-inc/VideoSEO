import logging
import os
import traceback
from datetime import datetime, timezone

from opentelemetry import trace
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.semconv.resource import ResourceAttributes

from src.domain.models import ExceptionLogData, LogRecord

LOG_LEVEL_MAPPER = {
    "NOTSET": 0,
    "DEBUG": 1,
    "INFO": 2,
    "WARNING": 3,
    "ERROR": 4,
    "CRITICAL": 5,
}


class JsonConsoleHandler(logging.StreamHandler):
    """
    ECS optimized OpenTelemetry logging handler that outputs JSON logs to stdout.
    """

    def __init__(self):
        super().__init__()
        self.sequence = 0

    def emit(self, record):
        try:
            self.sequence += 1
            span = trace.get_current_span()
            context = span.get_span_context()
            trace_id = (
                f"{context.trace_id:032x}" if context and context.is_valid else ""
            )
            span_id = f"{context.span_id:016x}" if context and context.is_valid else ""
            xray_id = f"00-{trace_id}-{span_id}-01" if trace_id and span_id else ""

            exception = None
            if record.exc_info:
                exc_type, exc, tb = record.exc_info
                exception = ExceptionLogData(
                    type=exc_type.__name__,
                    message=str(exc),
                    assembly=exc.__class__.__module__,
                    method=tb.tb_frame.f_code.co_name if tb else None,
                    stack_trace="".join(traceback.format_exception(*record.exc_info)),
                )

            log_model = LogRecord(
                sequence=self.sequence,
                timestamp=datetime.fromtimestamp(
                    record.created, tz=timezone.utc
                ).isoformat(),
                message=record.getMessage(),
                level=LOG_LEVEL_MAPPER.get(record.levelname),
                event_id=0,
                trace_id=trace_id,
                span_id=span_id,
                xray=xray_id,
                category_name=os.path.splitext(
                    os.path.relpath(record.pathname, start=os.getcwd())
                )[0].replace(os.sep, "."),
                exception=exception,
            )

            json_log = log_model.model_dump_json(exclude_none=True)
            self.stream.write(json_log + "\n")
            self.flush()
        except Exception:
            self.handleError(record)


def server_request_hook(span, scope):
    """
    Generates a stable request ID from the current server span and stores it in the request scope
    """
    if span and span.get_span_context().is_valid:
        ctx = span.get_span_context()
        trace_id = f"{ctx.trace_id:032x}"
        span_id = f"{ctx.span_id:016x}"
        request_id = f"00-{trace_id}-{span_id}-01"
        scope["request_id"] = request_id  # stash in scope


def setup_opentelemetry_and_logger(app, service_name: str) -> logging.Logger:
    """
    Setup OpenTelemetry and logging for ECS environment
    """
    trace.set_tracer_provider(
        TracerProvider(
            resource=Resource.create(
                {
                    ResourceAttributes.SERVICE_NAME: service_name,
                }
            )
        )
    )
    FastAPIInstrumentor.instrument_app(app, server_request_hook)

    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    for handler in logger.handlers[:]:  # Clear any existing handlers
        logger.removeHandler(handler)

    logger.addHandler(JsonConsoleHandler())
    logger.info(f"Logging initialized for service: {service_name}.")

    return logger
