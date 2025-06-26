from autogen_core import (
    DefaultTopicId,
    MessageContext,
    RoutedAgent,
    message_handler,
)
from autogen_core.models import (
    UserMessage,
)
from data_agents.messages import GroupChatMessage, RequestToSpeak
import asyncio
from typing import Optional, Callable

class UserAgent(RoutedAgent):
    def __init__(self, 
                 description: str, 
                 group_chat_topic_type: str,
                 output_message_queue: asyncio.Queue[GroupChatMessage | None],
                 input_func: Optional[Callable] = None
                ) -> None:
        super().__init__(description=description)
        self._group_chat_topic_type = group_chat_topic_type
        self.output_message_queue = output_message_queue
        self.input_func = input_func

    @message_handler
    async def handle_message(self, message: GroupChatMessage, ctx: MessageContext) -> None:
        # When integrating with a frontend, this is where group chat message would be sent to the frontend.
        assert isinstance(message.body, UserMessage)
        await self.output_message_queue.put(message.body)
    
    @message_handler
    async def handle_request_to_speak(self, message: RequestToSpeak, ctx: MessageContext) -> None:
        # print(f"\n{'-'*80}\n{self.id.type} speaking:", flush=True)
        user_input = await self.input_func(prompt="Enter your message, type 'APPROVE' to conclude the task: ", cancellation_token=None)
        await self.publish_message(
            GroupChatMessage(body=UserMessage(content=user_input, source=self.id.type)),
            DefaultTopicId(type=self._group_chat_topic_type),
        )