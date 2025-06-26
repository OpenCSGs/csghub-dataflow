from typing import List

from autogen_core.models import (
    ChatCompletionClient,
)
from autogen_core.tools import ToolSchema
from typing import Optional
from data_agents.base import BaseGroupChatAgent

class AdministratorAssistant(BaseGroupChatAgent):
    def __init__(
        self,
        description: str,
        group_chat_topic_type: str,
        model_client: ChatCompletionClient,
        tool_schema: Optional[List[ToolSchema]] = None,
        tool_agent_type: Optional[str] = None
    ) -> None:
        super().__init__(
            description=description,
            group_chat_topic_type=group_chat_topic_type,
            model_client=model_client,
            system_message="""As a data processing expert, 
                you have extensive experience in preparing training data for LLM models. 
                Now, as a consultant for a comprehensive data processing software called 'Data-flow', 
                you are very familiar with the functionalities provided by the software." 
                your role is to provide users with practical advice based on the existing functionality within the Data-flow software, 
                It is important to stay within the scope of the Dataflow software itself and not deviate from it. 
                You should know that: 'Recipe' is a pipeline consisting of ops, where each op is an operation on the data. The ops are categorized as 'mapper', 'filter', 'deduplicator', and 'selector'. 'Tool' is another concept that operates on the data but is more independent. 
                Together, they make the dataset more suitable for training a large model.
                """,
            tool_schema=tool_schema,
            tool_agent_type=tool_agent_type
        )


