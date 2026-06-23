from fastapi import FastAPI

from src.apps import get_all_routers
from src.core.exception_handlers import register_exception_handlers

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

app = FastAPI()

# ---------------- App setup ----------------
register_exception_handlers(app)
app.include_router(get_all_routers())

# ---------------- OpenTelemetry ----------------
provider = TracerProvider()

otlp_exporter = OTLPSpanExporter(
    endpoint="otel-collector:4317",
    insecure=True
)

provider.add_span_processor(
    BatchSpanProcessor(otlp_exporter)
)

trace.set_tracer_provider(provider)

tracer = trace.get_tracer("my.tracer.name")

# auto-instrument FastAPI
FastAPIInstrumentor.instrument_app(app)