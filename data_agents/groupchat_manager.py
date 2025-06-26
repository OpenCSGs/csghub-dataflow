import string
from typing import List, Mapping, Any
from autogen_core import (
    DefaultTopicId,
    MessageContext,
    RoutedAgent,
    message_handler,
)
from autogen_core.models import (
    ChatCompletionClient,
    SystemMessage,
    UserMessage,
)
from data_agents.messages import GroupChatMessage, RequestToSpeak, TerminateMessage
from autogen_core.model_context import BufferedChatCompletionContext
import time

class GroupChatManager(RoutedAgent):
    def __init__(
        self,
        participant_topic_types: List[str],
        model_client: ChatCompletionClient,
        participant_descriptions: List[str],
        group_chat_topic_type: str,
        max_rounds: int = 20,
        max_time: float = float("inf"),
    ) -> None:
        super().__init__("Group chat manager")
        self._participant_topic_types = participant_topic_types
        self._model_client = model_client
        self._participant_descriptions = participant_descriptions
        self._previous_participant_topic_type: str | None = None
        self._group_chat_topic_type = group_chat_topic_type
        self._model_context = BufferedChatCompletionContext(buffer_size=100)
        self._max_rounds = max_rounds
        self._max_time = max_time
        self._num_rounds = 0
        self._start_time: float = -1.0

    @message_handler
    async def handle_message(self, message: GroupChatMessage, ctx: MessageContext) -> None:
        assert isinstance(message.body, UserMessage)
        await self._model_context.add_message(message.body)

        # First broadcast sets the timer
        if self._start_time < 0:
            self._start_time = time.time()

        # Termination conditions
        # If the message is an approval message from the user, stop the chat.
        if message.body.source == "User":
            assert isinstance(message.body.content, str)
            if message.body.content.lower().strip(string.punctuation).endswith("approve"):
                # Send termination message to tell runtime stop and save history
                await self.publish_message(
                    TerminateMessage(f"{self.id.type} (termination condition): User terminated"),
                    topic_id=DefaultTopicId(type=self._group_chat_topic_type),
                )
                return

        if self._num_rounds >= self._max_rounds:
            await self.publish_message(
                TerminateMessage(f"{self.id.type} (termination condition): Max rounds ({self._max_rounds}) reached."),
                topic_id=DefaultTopicId(type=self._group_chat_topic_type),
            )
            return

        if time.time() - self._start_time >= self._max_time:
            await self.publish_message(
                TerminateMessage(f"{self.id.type} (termination condition): Max time ({self._max_time}s) reached."),
                topic_id=DefaultTopicId(type=self._group_chat_topic_type),
            )
            return
        
        # Format message history.
        # TODO, when items in history is too long and the history may exceed the context length of llm.
        messages: List[str] = []
        for msg in (await self._model_context.get_messages()):
            if isinstance(msg.content, str):
                messages.append(f"{msg.source}: {msg.content}")
            elif isinstance(msg.content, list):
                line: List[str] = []
                for item in msg.content:
                    if isinstance(item, str):
                        line.append(item)
                messages.append(f"{msg.source}: {', '.join(line)}")
        history = "\n".join(messages)

        # Format roles.
        roles = "\n".join(
            [
                f"{topic_type}: {description}".strip()
                for topic_type, description in zip(
                    self._participant_topic_types, self._participant_descriptions, strict=True
                )
                # previous speacker is not condidate
                if topic_type != self._previous_participant_topic_type
            ]
        )
        selector_prompt = """You are in a role play game. The following roles are available:
{roles}.
Read the following conversation. Then select the next role from {participants} to play. Only return the role.

{history}

Read the above conversation. Then select the next role from {participants} to play. Only return the role.
"""
        system_message = SystemMessage(
            content=selector_prompt.format(
                roles=roles,
                history=history,
                participants=str(
                    [
                        topic_type
                        for topic_type in self._participant_topic_types
                        if topic_type != self._previous_participant_topic_type
                    ]
                ),
            )
        )
        completion = await self._model_client.create([system_message], cancellation_token=ctx.cancellation_token)
        assert isinstance(completion.content, str)
        selected_topic_type: str
        for topic_type in self._participant_topic_types:
            if topic_type.lower() in completion.content.lower():
                selected_topic_type = topic_type
                self._previous_participant_topic_type = selected_topic_type
                self._num_rounds += 1  # Call before sending the message
                await self.publish_message(RequestToSpeak(), DefaultTopicId(type=selected_topic_type))
                return
        raise ValueError(f"Invalid role selected: {completion.content}")
    
    async def save_state(self) -> Mapping[str, Any]:
        return {
            "memory": self._model_context.save_state(),
        }

    async def load_state(self, state: Mapping[str, Any]) -> None:
        self._model_context.load_state({**state["memory"], "messages": [m for m in state["memory"]["messages"]]})

