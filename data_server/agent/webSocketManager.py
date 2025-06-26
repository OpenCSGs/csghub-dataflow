from typing import Dict, Callable, Optional, Any
from fastapi import WebSocket, WebSocketDisconnect
from autogen_core import CancellationToken
import asyncio
from loguru import logger
from data_agents.app import run_stream
from .models import TaskResult, Message
from data_agents.messages import TerminateMessage
from autogen_core.models import (
    UserMessage,
)


class WebSocketManager:
    """Manages WebSocket connections and message streaming for team task execution"""

    def __init__(self):
        self._connections: Dict[str, WebSocket] = {}
        self._cancellation_tokens: Dict[str, CancellationToken] = {}
        # Track explicitly closed connections
        self._input_responses: Dict[str, asyncio.Queue] = {}

    async def connect(self, websocket: WebSocket, user_id: str) -> bool:
        try:
            await websocket.accept()
            self._connections[user_id] = websocket
            # Initialize input queue for this connection
            self._input_responses[user_id] = asyncio.Queue()
            await self._send_message(
                user_id, Message(
                    type="system",
                    status="connected",
                ).model_dump()
            )

            return True
        except Exception as e:
            logger.error(f"Connection error for run {user_id}: {e}")
            return False

    async def start_stream(self, user_id: str, task: str) -> None:
        """Start streaming task execution with proper run management"""
        if user_id not in self._connections:
            raise ValueError(f"No active connection for run {user_id}")

        cancellation_token = CancellationToken()
        self._cancellation_tokens[user_id] = cancellation_token

        try:
            input_func = self.create_input_func(user_id)

            async for message in run_stream(
                user_id=user_id, task=task, input_func=input_func, cancellation_token=cancellation_token
            ):
                if cancellation_token.is_cancelled():
                    logger.info(
                        f"Stream cancelled or connection closed for run {user_id}")
                    break

                formatted_message = self._format_message(message)
                if formatted_message:
                    await self._send_message(user_id, formatted_message)

        except Exception as e:
            logger.error(f"Stream error for run {user_id}: {e}")
            await self._handle_stream_error(user_id, e)
        finally:
            self._cancellation_tokens.pop(user_id, None)

    def create_input_func(self, user_id: str) -> Callable:
        """Creates an input function for a specific run"""

        async def input_handler(prompt: str = "", cancellation_token: Optional[CancellationToken] = None) -> str:
            try:
                # Send input request to client
                await self._send_message(
                    user_id,
                    Message(
                        type="input_request",
                        data=UserMessage(
                            content=prompt,
                            source="Assistant",
                        ),
                        status="running",
                    ).model_dump()
                )
                # Wait for response
                if user_id in self._input_responses:
                    response = await self._input_responses[user_id].get()
                    return response
                else:
                    raise ValueError(f"No input queue for run {user_id}")

            except Exception as e:
                logger.error(f"Error handling input for run {user_id}: {e}")
                raise

        return input_handler

    async def handle_input_response(self, user_id: str, response: str) -> None:
        """Handle input response from client"""
        if user_id in self._input_responses:
            await self._input_responses[user_id].put(response)
        else:
            logger.warning(
                f"Received input response for inactive run {user_id}")

    def _get_stop_message(self, reason: str) -> dict:
        return TaskResult(
            stop_reason=reason,
            usage="",
            duration=0,
        )

    async def stop_run(self, user_id: str, reason: str) -> None:
        if user_id in self._cancellation_tokens:
            logger.info(f"Stopping run {user_id}")

            stop_message = self._get_stop_message(reason)

            try:
                # Then handle websocket communication if connection is active
                if user_id in self._connections:
                    await self._send_message(
                        user_id,
                        Message(
                            type="system",
                            data=stop_message,
                            status="cancelled",
                        ).model_dump()
                    )

                # Finally cancel the token
                self._cancellation_tokens[user_id].cancel()

            except Exception as e:
                logger.error(f"Error stopping run {user_id}: {e}")
                # await self.disconnect(user_id)  # Optional

    async def disconnect(self, user_id: str) -> None:
        """Clean up connection and associated resources"""
        logger.info(f"Disconnecting run {user_id}")

        # Cancel any running tasks
        await self.stop_run(user_id, "Connection closed")

        # Clean up resources
        self._connections.pop(user_id, None)
        self._cancellation_tokens.pop(user_id, None)
        self._input_responses.pop(user_id, None)

    async def _send_message(self, user_id: str, message: dict) -> None:
        """Send a message through the WebSocket with connection state checking

        Args:
            user_id: user id
            message: Message dictionary to send
        """
        try:
            if user_id in self._connections:
                websocket = self._connections[user_id]
                await websocket.send_json(message)
        except WebSocketDisconnect:
            logger.warning(
                f"WebSocket disconnected while sending message for run {user_id}")
            await self.disconnect(user_id)
        except Exception as e:
            logger.error(
                f"Error sending message for run {user_id}: {e}, {message}")
            # Don't try to send error message here to avoid potential recursive loop
            await self.disconnect(user_id)

    async def _handle_stream_error(self, user_id: str, error: Exception) -> None:
        """Handle stream errors with proper run updates"""
        error_result = TaskResult(
            stop_reason=str(error),
            usage="",
            duration=0,
        )

        await self._send_message(
            user_id,
            Message(
                type="system",
                data=error_result,
                status="complete"
            ).model_dump()
        )

    def _format_message(self, message: Any) -> Optional[dict]:
        """Format message for WebSocket transmission

        Args:
            message: Message to format

        Returns:
            Optional[dict]: Formatted message or None if formatting fails
        """

        try:
            if isinstance(message, TerminateMessage):
                result_msg = TaskResult(
                    stop_reason=message.content,
                )

                return Message(
                    type="system",
                    data=result_msg,
                    status="complete",
                ).model_dump()
            else:  # UserMessage
                return Message(
                    type="message",
                    data=message,
                    status="running",
                ).model_dump()
        except Exception as e:
            logger.error(f"Message formatting error: {e}")
            return None

    async def cleanup(self) -> None:
        """Clean up all active connections and resources when server is shutting down"""
        logger.info(
            f"Cleaning up {len(self.active_connections)} active connections")

        try:
            # First cancel all running tasks
            for user_id in self.active_runs.copy():
                if user_id in self._cancellation_tokens:
                    self._cancellation_tokens[user_id].cancel()

            # Then disconnect all websockets with timeout
            # 10 second timeout for entire cleanup
            async with asyncio.timeout(10):
                for user_id in self.active_connections.copy():
                    try:
                        # Give each disconnect operation 2 seconds
                        async with asyncio.timeout(2):
                            await self.disconnect(user_id)
                    except asyncio.TimeoutError:
                        logger.warning(f"Timeout disconnecting run {user_id}")
                    except Exception as e:
                        logger.error(f"Error disconnecting run {user_id}: {e}")

        except asyncio.TimeoutError:
            logger.warning("WebSocketManager cleanup timed out")
        except Exception as e:
            logger.error(f"Error during WebSocketManager cleanup: {e}")
        finally:
            # Always clear internal state, even if cleanup had errors
            self._connections.clear()
            self._cancellation_tokens.clear()
            self._input_responses.clear()

    @property
    def active_connections(self) -> set[str]:
        """Get set of active run IDs"""
        return set(self._connections.keys())

    @property
    def active_runs(self) -> set[str]:
        """Get set of runs with active cancellation tokens"""
        return set(self._cancellation_tokens.keys())
