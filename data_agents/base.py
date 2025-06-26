from typing import List, Optional
from autogen_core import (
    DefaultTopicId,
    MessageContext,
    RoutedAgent,
    message_handler,
    AgentId,
)
from autogen_core.models import (
    AssistantMessage,
    ChatCompletionClient,
    LLMMessage,
    SystemMessage,
    UserMessage,
)
from data_agents.messages import GroupChatMessage, RequestToSpeak
from autogen_core.tools import ToolSchema
import warnings
warnings.simplefilter("ignore", UserWarning)
from autogen_core.tool_agent import tool_agent_caller_loop


class BaseGroupChatAgent(RoutedAgent):
    """A group chat participant using an LLM."""

    def __init__(
        self,
        description: str,
        group_chat_topic_type: str,
        model_client: ChatCompletionClient,
        system_message: str,
        tool_schema: Optional[List[ToolSchema]] = None,
        tool_agent_type: Optional[str] = None
    ) -> None:
        super().__init__(description=description)
        self._group_chat_topic_type = group_chat_topic_type
        self._model_client = model_client
        self._system_message = SystemMessage(content=system_message)
        self._chat_history: List[LLMMessage] = []
        self._tool_schema = tool_schema
        self._tool_agent_id = AgentId(tool_agent_type, self.id.key) if tool_agent_type else None 

    @message_handler
    async def handle_message(self, message: GroupChatMessage, ctx: MessageContext) -> None:
        self._chat_history.extend(
            [
                UserMessage(content=f"Transferred to {message.body.source}", source="system"),
                message.body,
            ]
        )

    @message_handler
    async def handle_request_to_speak(self, message: RequestToSpeak, ctx: MessageContext) -> None:
        # print(f"\n{'-'*80}\n{self.id.type} speaking:", flush=True)
        self._chat_history.append(
            UserMessage(content=f"Transferred to {self.id.type}, adopt the persona immediately.", source="system")
        )

        # Run the caller loop to handle tool calls.
        messages = await tool_agent_caller_loop(
            self,
            tool_agent_id=self._tool_agent_id,
            model_client=self._model_client,
            input_messages=[self._system_message] + self._chat_history,
            tool_schema=self._tool_schema,
            cancellation_token=ctx.cancellation_token,
        )
        # Return the final response.
        assert isinstance(messages[-1].content, str)
        # print(f"\n{messages[-1].content}")
        self._chat_history.append(AssistantMessage(content=messages[-1].content, source=self.id.type))  # type: ignore
        
        await self.publish_message(
            GroupChatMessage(body=UserMessage(content=messages[-1].content, source=self.id.type)),
            topic_id=DefaultTopicId(type=self._group_chat_topic_type),
        )