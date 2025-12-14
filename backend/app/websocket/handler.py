from fastapi import WebSocket, WebSocketDisconnect
import json
import asyncio
import logging
from typing import Optional
from .manager import ConnectionManager
from ..cua.agent_service import CUAAgentService
from ..cua.message_types import (
    MessageType,
    WebSocketMessage,
    StatusPayload,
    APILogPayload,
    APIResponsePayload,
)
from ..api.bus_service import BusAPIService, LogEntry
from ..api.contingency_service import ContingencyAPIService

logger = logging.getLogger(__name__)


class WebSocketHandler:
    """Handles WebSocket messages and coordinates with CUA agent and APIs."""

    def __init__(self, manager: ConnectionManager):
        self.manager = manager
        self.agent_service: Optional[CUAAgentService] = None
        self.api_service: Optional[BusAPIService] = None
        self.agent_task: Optional[asyncio.Task] = None
        self.api_task: Optional[asyncio.Task] = None

    async def handle_connection(self, websocket: WebSocket) -> None:
        """Main handler for a WebSocket connection."""
        await self.manager.connect(websocket)

        # Send initial status
        await self.manager.send_json(
            websocket,
            WebSocketMessage(
                type=MessageType.STATUS,
                payload=StatusPayload(
                    status="idle",
                    message="Connected. Ready to start.",
                ).model_dump(),
            ).model_dump(),
        )

        try:
            while True:
                # Receive message from client
                data = await websocket.receive_text()
                message = json.loads(data)

                await self._handle_message(websocket, message)

        except WebSocketDisconnect:
            logger.info("Client disconnected normally")
            await self._cleanup(websocket)
        except Exception as e:
            logger.error(f"WebSocket error: {e}")
            await self._cleanup(websocket)

    async def _handle_message(self, websocket: WebSocket, message: dict) -> None:
        """Process incoming WebSocket messages."""
        msg_type = message.get("type")

        if msg_type == MessageType.START_AGENT.value:
            await self._start_agent(websocket)

        elif msg_type == MessageType.STOP_AGENT.value:
            await self._stop_agent(websocket)

        elif msg_type == MessageType.RUN_API.value:
            payload = message.get("payload", {})
            endpoint = payload.get("endpoint", "")
            await self._run_api(websocket, endpoint)

    async def _start_agent(self, websocket: WebSocket) -> None:
        """Start the CUA agent and stream results."""
        if self.agent_service and self.agent_service.is_running:
            await self.manager.send_json(
                websocket,
                WebSocketMessage(
                    type=MessageType.ERROR,
                    payload=StatusPayload(
                        status="error",
                        message="Agent is already running",
                    ).model_dump(),
                ).model_dump(),
            )
            return

        self.agent_service = CUAAgentService()

        async def run_agent():
            try:
                async for msg in self.agent_service.run_task():
                    await self.manager.send_json(websocket, msg.model_dump())
                    # Small delay to prevent overwhelming the WebSocket
                    await asyncio.sleep(0.05)
            except Exception as e:
                logger.error(f"Agent error: {e}")
                await self.manager.send_json(
                    websocket,
                    WebSocketMessage(
                        type=MessageType.ERROR,
                        payload=StatusPayload(
                            status="error",
                            message=str(e),
                        ).model_dump(),
                    ).model_dump(),
                )

        self.agent_task = asyncio.create_task(run_agent())

    async def _run_api(self, websocket: WebSocket, endpoint: str) -> None:
        """Run an API endpoint and stream logs."""
        if self.api_service and self.api_service.is_running:
            await self.manager.send_json(
                websocket,
                WebSocketMessage(
                    type=MessageType.ERROR,
                    payload=StatusPayload(
                        status="error",
                        message="An API is already running",
                    ).model_dump(),
                ).model_dump(),
            )
            return

        # Send status that we're starting
        await self.manager.send_json(
            websocket,
            WebSocketMessage(
                type=MessageType.STATUS,
                payload=StatusPayload(
                    status="running",
                    message=f"Starting API: {endpoint}",
                ).model_dump(),
            ).model_dump(),
        )

        async def stream_log(log_entry: LogEntry):
            """Callback to stream logs to WebSocket."""
            await self.manager.send_json(
                websocket,
                WebSocketMessage(
                    type=MessageType.API_LOG,
                    payload=APILogPayload(
                        message=log_entry.message,
                        timestamp=log_entry.timestamp,
                        level=log_entry.level,
                    ).model_dump(),
                ).model_dump(),
            )

        async def run_api():
            try:
                if endpoint == "buses":
                    self.api_service = BusAPIService(log_callback=stream_log)
                    result = await self.api_service.run()
                elif endpoint == "contingency":
                    self.api_service = ContingencyAPIService(log_callback=stream_log)
                    result = await self.api_service.run()
                else:
                    await self.manager.send_json(
                        websocket,
                        WebSocketMessage(
                            type=MessageType.ERROR,
                            payload=StatusPayload(
                                status="error",
                                message=f"Unknown API endpoint: {endpoint}",
                            ).model_dump(),
                        ).model_dump(),
                    )
                    return

                # Send the final response
                await self.manager.send_json(
                    websocket,
                    WebSocketMessage(
                        type=MessageType.API_RESPONSE,
                        payload=APIResponsePayload(
                            endpoint=endpoint,
                            status=result.status,
                            data=result.data,
                            error=result.error,
                        ).model_dump(),
                    ).model_dump(),
                )

                # Send completion status
                await self.manager.send_json(
                    websocket,
                    WebSocketMessage(
                        type=MessageType.STATUS,
                        payload=StatusPayload(
                            status="completed",
                            message=f"API {endpoint} completed",
                        ).model_dump(),
                    ).model_dump(),
                )

            except Exception as e:
                logger.error(f"API error: {e}")
                await self.manager.send_json(
                    websocket,
                    WebSocketMessage(
                        type=MessageType.ERROR,
                        payload=StatusPayload(
                            status="error",
                            message=str(e),
                        ).model_dump(),
                    ).model_dump(),
                )
            finally:
                self.api_service = None

        self.api_task = asyncio.create_task(run_api())

    async def _stop_agent(self, websocket: WebSocket) -> None:
        """Stop the running agent or API."""
        if self.agent_service:
            await self.agent_service.stop()

        if self.api_service:
            await self.api_service.stop()

        if self.agent_task:
            self.agent_task.cancel()
            try:
                await self.agent_task
            except asyncio.CancelledError:
                pass

        if self.api_task:
            self.api_task.cancel()
            try:
                await self.api_task
            except asyncio.CancelledError:
                pass

        await self.manager.send_json(
            websocket,
            WebSocketMessage(
                type=MessageType.STATUS,
                payload=StatusPayload(
                    status="stopped",
                    message="Stopped by user",
                ).model_dump(),
            ).model_dump(),
        )

    async def _cleanup(self, websocket: WebSocket) -> None:
        """Clean up on disconnect."""
        if self.agent_service:
            await self.agent_service.stop()
        if self.api_service:
            await self.api_service.stop()
        await self.manager.disconnect(websocket)
