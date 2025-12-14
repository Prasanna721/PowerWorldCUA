import asyncio
import logging
import base64
import ssl
import certifi
import os
from typing import AsyncGenerator, Optional

# Fix SSL certificate verification for macOS
os.environ['SSL_CERT_FILE'] = certifi.where()
os.environ['REQUESTS_CA_BUNDLE'] = certifi.where()

from computer import Computer
from agent import ComputerAgent
from .message_types import (
    WebSocketMessage,
    MessageType,
    ScreenshotPayload,
    StatusPayload,
    AgentMessagePayload,
)
from ..config import get_settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CUAAgentService:
    def __init__(self):
        self.settings = get_settings()
        self.computer: Optional[Computer] = None
        self.agent: Optional[ComputerAgent] = None
        self.is_running = False
        self.step_count = 0

    async def initialize(self) -> None:
        """Initialize the Computer connection to the cloud sandbox."""
        logger.info(f"Initializing computer connection to sandbox: {self.settings.cua_sandbox_name}")
        self.computer = Computer(
            os_type="windows",
            provider_type="cloud",
            name=self.settings.cua_sandbox_name,
            api_key=self.settings.cua_api_key,
        )

    async def create_agent(self) -> None:
        """Create the ComputerAgent with Claude model."""
        if not self.computer:
            raise RuntimeError("Computer not initialized")

        logger.info("Creating ComputerAgent with Claude model")
        self.agent = ComputerAgent(
            model="cua/anthropic/claude-sonnet-4.5",
            tools=[self.computer],
            only_n_most_recent_images=3,
            max_trajectory_budget=10.0,
            instructions="""
You are automating a Windows desktop to download software.

IMPORTANT GUIDELINES:
- Always wait for windows and pages to fully load before interacting
- Look for loading indicators and wait for them to disappear
- Verify each action by checking on-screen confirmation
- If a button or link is not visible, try scrolling
- Take screenshots to verify your progress

YOUR TASK:
1. Open the web browser (Microsoft Edge or Chrome)
2. Navigate to the PowerWorld download page
3. Find and click the download link for the PowerWorld Simulator demo
4. Confirm the download has started
            """.strip(),
        )

    async def run_task(self) -> AsyncGenerator[WebSocketMessage, None]:
        """
        Run the agent task and yield messages for WebSocket streaming.

        The task: Navigate to PowerWorld download page and click download link.
        """
        self.is_running = True
        self.step_count = 0

        try:
            # Send status: connecting
            yield WebSocketMessage(
                type=MessageType.STATUS,
                payload=StatusPayload(
                    status="connecting",
                    message="Connecting to Windows sandbox...",
                ).model_dump(),
            )

            # Initialize computer and agent
            await self.initialize()
            await self.computer.run()
            await self.create_agent()

            # Send status: running
            yield WebSocketMessage(
                type=MessageType.STATUS,
                payload=StatusPayload(
                    status="running",
                    message="Agent started, navigating to PowerWorld...",
                ).model_dump(),
            )

            # Define the task
            task_instruction = f"""
Navigate to {self.settings.target_url} and click the download link
for the PowerWorld Simulator demo software.

Steps:
1. Open the web browser
2. Navigate to the URL: {self.settings.target_url}
3. Wait for the page to load completely
4. Find and click the download link on the page
5. Confirm the download has started
            """

            messages = [{"role": "user", "content": task_instruction}]

            # Run the agent and stream results
            async for result in self.agent.run(messages):
                if not self.is_running:
                    break

                for item in result.get("output", []):
                    self.step_count += 1

                    item_type = item.get("type", "")

                    # Handle text message from the agent
                    if item_type == "message":
                        content = item.get("content", [])
                        if content and len(content) > 0:
                            for block in content:
                                if block.get("type") == "text":
                                    text = block.get("text", "")
                                    if text:
                                        yield WebSocketMessage(
                                            type=MessageType.MESSAGE,
                                            payload=AgentMessagePayload(
                                                role="assistant",
                                                content=text,
                                            ).model_dump(),
                                        )
                                elif block.get("type") == "output_text":
                                    text = block.get("text", "")
                                    if text:
                                        yield WebSocketMessage(
                                            type=MessageType.MESSAGE,
                                            payload=AgentMessagePayload(
                                                role="assistant",
                                                content=text,
                                            ).model_dump(),
                                        )

                    # Handle computer call output (contains screenshots)
                    elif item_type == "computer_call_output":
                        output_content = item.get("content", [])
                        for output_item in output_content:
                            if output_item.get("type") == "computer_screenshot":
                                image_url = output_item.get("image_url", "")
                                if image_url:
                                    yield WebSocketMessage(
                                        type=MessageType.SCREENSHOT,
                                        payload=ScreenshotPayload(
                                            image_data=image_url,
                                            step=self.step_count,
                                        ).model_dump(),
                                    )
                            elif output_item.get("type") == "input_image":
                                image_url = output_item.get("image_url", "")
                                if image_url:
                                    yield WebSocketMessage(
                                        type=MessageType.SCREENSHOT,
                                        payload=ScreenshotPayload(
                                            image_data=image_url,
                                            step=self.step_count,
                                        ).model_dump(),
                                    )

                    # Handle computer call (agent is making an action)
                    elif item_type == "computer_call":
                        action = item.get("action", {})
                        action_type = action.get("type", "unknown")
                        yield WebSocketMessage(
                            type=MessageType.MESSAGE,
                            payload=AgentMessagePayload(
                                role="system",
                                content=f"Executing action: {action_type}",
                                action=action_type,
                            ).model_dump(),
                        )

                    # Handle reasoning
                    elif item_type == "reasoning":
                        summary = item.get("summary", [])
                        if summary:
                            for s in summary:
                                text = s.get("text", "")
                                if text:
                                    yield WebSocketMessage(
                                        type=MessageType.MESSAGE,
                                        payload=AgentMessagePayload(
                                            role="reasoning",
                                            content=text,
                                        ).model_dump(),
                                    )

            # Send completion status
            yield WebSocketMessage(
                type=MessageType.AGENT_COMPLETE,
                payload=StatusPayload(
                    status="completed",
                    message="Agent task completed successfully",
                ).model_dump(),
            )

        except Exception as e:
            logger.error(f"Error during agent execution: {e}")
            yield WebSocketMessage(
                type=MessageType.ERROR,
                payload=StatusPayload(
                    status="error",
                    message=str(e),
                ).model_dump(),
            )
        finally:
            self.is_running = False
            if self.computer:
                try:
                    await self.computer.disconnect()
                except Exception as e:
                    logger.error(f"Error disconnecting computer: {e}")

    async def stop(self) -> None:
        """Stop the running agent."""
        logger.info("Stopping agent...")
        self.is_running = False
