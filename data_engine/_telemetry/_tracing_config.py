import logging
from abc import ABC, abstractmethod
from typing import Dict, Generic, List, Literal, TypedDict, TypeVar

from opentelemetry.trace import SpanKind
from opentelemetry.util import types
from typing_extensions import NotRequired

Operation = TypeVar("Operation", bound=str)
ExtraAttributes = TypeVar("ExtraAttributes")
NAMESPACE = "dataflow"

class TracingConfig(ABC, Generic[Operation, ExtraAttributes]):
    """
    A protocol that defines the configuration for instrumentation.

    This protocol specifies the required properties and methods that any
    instrumentation configuration class must implement. It includes a
    property to get the name of the module being instrumented and a method
    to build attributes for the instrumentation configuration.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """
        Returns:
            The name of the module that is being instrumented.
        """
        ...

    @abstractmethod
    def build_attributes(
        self,
        operation: Operation,
        extraAttributes: ExtraAttributes | None,
    ) -> Dict[str, types.AttributeValue]:
        """
        Builds the attributes for the instrumentation configuration.

        Returns:
            Dict[str, str]: The attributes for the instrumentation configuration.
        """
        ...

    @abstractmethod
    def get_span_name(
        self,
        operation: Operation,
    ) -> str:
        """
        Returns the span name based on the given operation and destination.

        Parameters:
            operation (MessagingOperation): The messaging operation.
            destination (Optional[MessagingDestination]): The messaging destination.

        Returns:
            str: The span name.
        """
        ...

    @abstractmethod
    def get_span_kind(
        self,
        operation: Operation,
    ) -> SpanKind:
        """
        Determines the span kind based on the given messaging operation.

        Parameters:
            operation (MessagingOperation): The messaging operation.

        Returns:
            SpanKind: The span kind based on the messaging operation.
        """


class ExtraDatasetExecutorAttributes(TypedDict):
    dataset_count: NotRequired[int]
    cpu: NotRequired[int]
    gpu: NotRequired[int]
    operation_name: NotRequired[str]
    # operation_type: NotRequired[Literal["mapper", "filter", "deduplicator", "selector"]]

DatasetExecutorOperation = Literal["start", "ingest", "format", "run", "op", "export"]


class ExecutorTracingConfig(
    TracingConfig[DatasetExecutorOperation, ExtraDatasetExecutorAttributes]
):
    """
    A class that defines the configuration for message runtime instrumentation.

    This class implements the TracingConfig protocol and provides
    the name of the module being instrumented and the attributes for the
    instrumentation configuration.
    """

    def __init__(self, executor_name: str) -> None:
        self._executor_name = executor_name

    @property
    def name(self) -> str:
        return self._executor_name

    def build_attributes(
        self,
        operation: DatasetExecutorOperation,
        extraAttributes: ExtraDatasetExecutorAttributes | None,
    ) -> Dict[str, types.AttributeValue]:
        attrs: Dict[str, types.AttributeValue] = {
            "messaging.operation": operation,
        }
        if extraAttributes:
            # TODO: Make this more pythonic?
            if "dataset_count" in extraAttributes:
                attrs["messaging.message.dataset_count"] = extraAttributes["dataset_count"]
            if "cpu" in extraAttributes:
                attrs["messaging.message.cpu"] = extraAttributes["cpu"]
            if "gpu" in extraAttributes:
                attrs["messaging.message.gpu"] = extraAttributes["gpu"]
            if "operation_name" in extraAttributes:
                attrs["messaging.message.operation_name"] = extraAttributes["operation_name"]
        return attrs

    def get_span_name(
        self,
        operation: DatasetExecutorOperation,
    ) -> str:
        """
        Returns the span name based on the given operation.
        Semantic Conventions - https://opentelemetry.io/docs/specs/semconv/messaging/messaging-spans/#span-name

        Parameters:
            operation (MessagingOperation): The messaging operation.

        Returns:
            str: The span name.
        """
        span_parts: List[str] = [operation]
        span_name = " ".join(span_parts)
        return f"{NAMESPACE} {self.name.lower()} {span_name}"

    def get_span_kind(
        self,
        operation: DatasetExecutorOperation,
    ) -> SpanKind:
        """
        Determines the span kind based on the given messaging operation.
        Semantic Conventions - https://opentelemetry.io/docs/specs/semconv/messaging/messaging-spans/#span-kind

        Parameters:
            operation (MessagingOperation): The messaging operation.

        Returns:
            SpanKind: The span kind based on the messaging operation.
        """
        
        return SpanKind.INTERNAL
