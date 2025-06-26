from autogen_ext.models.openai import AzureOpenAIChatCompletionClient
import asyncio
from autogen_core.tools import FunctionTool, Tool
from autogen_core.tool_agent import ToolAgent
from typing import List, Any, AsyncGenerator, Optional, Callable
from autogen_core import (
    SingleThreadedAgentRuntime,
    TopicId,
    TypeSubscription,
    AgentId,
    CancellationToken,
)
from autogen_core.models import (
    UserMessage,
)
from data_agents.utils.tools.load_samples import (
    get_sample_categorys,
    get_sample_dataset_category,
    query_samples,
)

from data_agents.messages import GroupChatMessage, TerminateMessage

from data_agents.utils.tools.functionality import (
    get_ops,
    get_single_op,
    get_tools,
    get_single_tool,
)
from data_agents.teacher_agent import TeacherAssistant
from data_agents.administrator_agent import AdministratorAssistant
from data_agents.user_agent import UserAgent
from data_agents.groupchat_manager import GroupChatManager
import uuid
from autogen_core.base.intervention import DefaultInterventionHandler
from data_agents.persistence.localfile import LocalFilePersistence

class TerminationHandler(DefaultInterventionHandler):
    def __init__(self):
        self.terminateMessage: TerminateMessage | None = None

    async def on_publish(self, message: Any, *, sender: AgentId | None) -> Any:
        if isinstance(message, TerminateMessage):
            self.terminateMessage = message
        return message

    @property
    def is_terminated(self) -> bool:
        return self.terminateMessage is not None

    @property
    def termination_msg(self) -> str | None:
        if self.terminateMessage is None:
            return None
        return self.terminateMessage.content
    
async def run_stream(
        user_id: str, 
        task: str,
        cancellation_token: CancellationToken | None = None,
        input_func: Optional[Callable] = None
        ) -> AsyncGenerator[UserMessage | TerminateMessage, None]:
    output_message_queue: asyncio.Queue[UserMessage | None] = asyncio.Queue()
    state_persister = LocalFilePersistence()
    termination_handler = TerminationHandler()
    # Create an local embedded runtime.
    runtime = SingleThreadedAgentRuntime(intervention_handlers=[termination_handler])

    teacher_topic_type = "Teacher"
    administrator_topic_type = "Administrator"
    user_topic_type = "User"
    group_chat_topic_type = "group_chat"

    teacher_description = "A person who knows everything about data-flow and enjoys guiding and answering questions using examples can be called upon for specific examples related to an open-source dataset."
    administrator_description = "A system administrator who manages data-flow can be tasked with performing various operations provided by the data flow system. For example, they can be asked about the number and functionality of the operations (Ops) available."
    user_description = "User for providing final approval."

    # Create llm client
    llm_client = AzureOpenAIChatCompletionClient(
        azure_deployment="csg-gpt4",
        model="gpt-4-0613",
        api_version="2024-02-15-preview",
        azure_endpoint="https://opencsg-us.openai.azure.com",
        api_key="af7aabe2e77b41b1a89452ce694658b5",
    )

    # Registe Teacher assistant
    # Create the tools.
    teacher_tools: List[Tool] = [
        FunctionTool(get_sample_categorys, description="Get sample category, The dataflow divides samples into different types, such as 'refine', which means refining the existing open-source data."),
        FunctionTool(get_sample_dataset_category, description="By using the category parameter, you can retrieve the open-source datasets processed by samples of that type. These datasets are well-known and often have subdatasets. The return value also includes a readme document providing instructions and explanations."),
        FunctionTool(query_samples, description="By using the 'dataset', 'sub_dataset' and 'category' as parameter, to get a 'plan', this plan is for handling raw data, include 'recipe' and 'tools', also include 'readme' for description."),

    ]
    await ToolAgent.register(runtime, "tool_executor_agent_4_teacher", lambda: ToolAgent("tool executor agent", teacher_tools))
    # Register the assistant and executor agents by providing
    # their agent types, the factory functions for creating instance and subscriptions.
    teacher_agent_type = await TeacherAssistant.register(
        runtime,
        teacher_topic_type,
        lambda: TeacherAssistant(
            description=teacher_description,
            group_chat_topic_type=group_chat_topic_type,
            model_client=llm_client,
            tool_schema=[tool.schema for tool in teacher_tools],
            tool_agent_type="tool_executor_agent_4_teacher"
        ),
    )
    await runtime.add_subscription(TypeSubscription(topic_type=teacher_topic_type, agent_type=teacher_agent_type.type))
    await runtime.add_subscription(TypeSubscription(topic_type=group_chat_topic_type, agent_type=teacher_agent_type.type))

    # Registe Administrator assistant
    # Create the tools.
    administrator_tools: List[Tool] = [
        FunctionTool(get_ops, description="Get list of Ops in data-flow, each item has 'name', 'type' and 'description'"),
        FunctionTool(get_single_op, description="By using name of Op, get details of this Ops, include 'description', 'samples'(demonstrate the effectiveness of Op) and 'params'(input params of the Op)."),
        FunctionTool(get_tools, description="Get list of Tools in data-flow, each item has 'name', 'type' and 'description'"),
        FunctionTool(get_single_tool, description="By using name of Tool, get details of this Tool, include 'description' and 'params'(input params of the Op)."),
    ]
    await ToolAgent.register(runtime, "tool_executor_agent_4_administrator", lambda: ToolAgent("tool executor agent", administrator_tools))
    # Register the assistant and executor agents by providing
    # their agent types, the factory functions for creating instance and subscriptions.
    administrator_agent_type = await AdministratorAssistant.register(
        runtime,
        administrator_topic_type,
        lambda: AdministratorAssistant(
            description=administrator_description,
            group_chat_topic_type=group_chat_topic_type,
            model_client=llm_client,
            tool_schema=[tool.schema for tool in administrator_tools],
            tool_agent_type="tool_executor_agent_4_administrator",
        ),
    )
    await runtime.add_subscription(TypeSubscription(topic_type=administrator_topic_type, agent_type=administrator_agent_type.type))
    await runtime.add_subscription(TypeSubscription(topic_type=group_chat_topic_type, agent_type=administrator_agent_type.type))

    # Registe User assistant
    user_agent_type = await UserAgent.register(
        runtime,
        user_topic_type,
        lambda: UserAgent(
            description=user_description, 
            group_chat_topic_type=group_chat_topic_type,
            input_func=input_func,
            output_message_queue=output_message_queue
        ),
    )
    await runtime.add_subscription(TypeSubscription(topic_type=user_topic_type, agent_type=user_agent_type.type))
    await runtime.add_subscription(TypeSubscription(topic_type=group_chat_topic_type, agent_type=user_agent_type.type))

    # Registe groupchat manager assistant
    group_chat_manager_type = await GroupChatManager.register(
        runtime,
        "group_chat_manager",
        lambda: GroupChatManager(
            participant_topic_types=[teacher_topic_type, administrator_topic_type, user_topic_type],
            model_client=llm_client,
            participant_descriptions=[teacher_description, administrator_description, user_description],
            group_chat_topic_type=group_chat_topic_type,
        ),
    )
    await runtime.add_subscription(
        TypeSubscription(topic_type=group_chat_topic_type, agent_type=group_chat_manager_type.type)
    )
    # Start the runtime and publish a message to the assistant.
    session_id = state_persister.get_uuid(user_id)
    if not session_id:
        session_id = user_id + str(uuid.uuid4())

    state = state_persister.load_content(uuid=session_id)
    if state:
        await runtime.load_state(state)

    runtime.start()

    # Start a coroutine to stop the runtime and signal the output message queue is complete.
    async def stop_runtime() -> None:
        await runtime.stop_when(lambda: termination_handler.is_terminated)
        await output_message_queue.put(None)

    shutdown_task = asyncio.create_task(stop_runtime())

    try:
        await runtime.publish_message(
            GroupChatMessage(
                body=UserMessage(
                    content=task,
                    source="User",
                )
            ),
            TopicId(type=group_chat_topic_type, source=session_id),
        )

        # Yield the messsages until the queue is empty.
        while True:
            message_future = asyncio.ensure_future(output_message_queue.get())
            if cancellation_token is not None:
                cancellation_token.link_future(message_future)
            # Wait for the next message, this will raise an exception if the task is cancelled.
            message = await message_future
            if message is None:
                break
            yield message

        # Yield the termination.
        yield TerminateMessage(content=f"Conversation Terminated - {termination_handler.termination_msg}")
    finally:
        # Wait for the shutdown task to finish.
        await shutdown_task
        state_to_persist = await runtime.save_state()
        state_persister.save_content(uuid=session_id, content=state_to_persist)

async def main():
    async def input_handler(prompt: str = "", cancellation_token: Optional[CancellationToken] = None) -> str:
        async def ainput(prompt: str) -> str:
            return await asyncio.to_thread(input, f"{prompt} ")
        
        user_input = await ainput("Enter your message, type 'APPROVE' to conclude the task: ")
        return user_input

    async for message in run_stream(user_id="pengli", task="I want a sample, maybe for dataset pile.",
                                    input_func=input_handler):
        if not isinstance(message, TerminateMessage):
            print(f"\n{'-'*80}\n{message.source} speaking:", flush=True)
            print(f"\n{message.content}")
        else:
            print(f"communicate close.")

if __name__ == '__main__':
    asyncio.run(main())
