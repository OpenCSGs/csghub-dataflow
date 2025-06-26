from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from ._tracing import TraceHelper
from ._tracing_config import ExecutorTracingConfig
from data_engine.utils.env import OpentelemetryEnable

def configure_oltp_tracing(endpoint: str = None) -> trace.TracerProvider:
    # Configure Tracing
    tracer_provider = TracerProvider(resource=Resource({"service.name": "dataflow"}))
    processor = BatchSpanProcessor(OTLPSpanExporter())
    tracer_provider.add_span_processor(processor)
    trace.set_tracer_provider(tracer_provider)

    return tracer_provider

TRACE_HELPER = TraceHelper(configure_oltp_tracing() if OpentelemetryEnable() else None, ExecutorTracingConfig("PipelineExecutor"))
TRACE_HELPER_TOOL = TraceHelper(configure_oltp_tracing() if OpentelemetryEnable() else None, ExecutorTracingConfig("ToolExecutor"))

