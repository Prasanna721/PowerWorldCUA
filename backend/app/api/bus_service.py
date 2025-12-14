import asyncio
import logging
import os
import ssl
import certifi
import glob
import base64
from typing import AsyncGenerator, Optional, List, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime
import time

# Fix SSL certificate verification for macOS
os.environ['SSL_CERT_FILE'] = certifi.where()
os.environ['REQUESTS_CA_BUNDLE'] = certifi.where()

from computer import Computer
from agent import ComputerAgent
from ..config import get_settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class LogEntry:
    timestamp: float
    message: str
    level: str = "info"


@dataclass
class APIResult:
    status: str  # "success", "error"
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    logs: List[LogEntry] = field(default_factory=list)
    final_screenshot: Optional[str] = None


class BusAPIService:
    """Service to extract bus data from PowerWorld via CUA agent."""

    def __init__(self, log_callback=None):
        self.settings = get_settings()
        self.computer: Optional[Computer] = None
        self.agent: Optional[ComputerAgent] = None
        self.is_running = False
        self.logs: List[LogEntry] = []
        self.final_screenshot: Optional[str] = None
        self.log_callback = log_callback  # Callback for streaming logs
        self.trajectory_path: Optional[str] = None  # Path to saved trajectories

    def _log(self, message: str, level: str = "info"):
        """Add a log entry and optionally stream it."""
        entry = LogEntry(timestamp=time.time(), message=message, level=level)
        self.logs.append(entry)
        logger.info(f"[BusAPI] {message}")
        if self.log_callback:
            asyncio.create_task(self.log_callback(entry))

    def _get_latest_screenshot(self) -> Optional[str]:
        """Read the latest screenshot from saved trajectory."""
        if not self.trajectory_path or not os.path.exists(self.trajectory_path):
            return None

        # Find all PNG files in trajectory directory
        pattern = os.path.join(self.trajectory_path, "**", "*.png")
        screenshots = glob.glob(pattern, recursive=True)

        if not screenshots:
            return None

        # Get the most recent screenshot by modification time
        latest = max(screenshots, key=os.path.getmtime)
        self._log(f"Found screenshot: {latest}")

        # Read and encode as base64 data URL
        with open(latest, "rb") as f:
            image_data = base64.b64encode(f.read()).decode("utf-8")

        return f"data:image/png;base64,{image_data}"

    async def initialize(self) -> None:
        """Initialize the Computer connection to the cloud sandbox."""
        self._log("Connecting to Windows sandbox...")
        self.computer = Computer(
            os_type="windows",
            provider_type="cloud",
            name=self.settings.cua_sandbox_name,
            api_key=self.settings.cua_api_key,
        )

    async def create_agent(self) -> None:
        """Create the ComputerAgent with bus-specific instructions."""
        if not self.computer:
            raise RuntimeError("Computer not initialized")

        self._log("Creating CUA agent...")

        # Create unique trajectory directory for this run
        trajectory_base = os.path.join(os.path.dirname(__file__), "..", "..", "trajectories")
        run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.trajectory_path = os.path.join(trajectory_base, f"bus_api_{run_id}")
        os.makedirs(self.trajectory_path, exist_ok=True)
        self._log(f"Trajectory will be saved to: {self.trajectory_path}")

        instructions = """
You are automating PowerWorld Simulator to extract bus data.

TASK: Open the buses dialog and capture the data.

STEPS:
1. Look at the current screen
2. If PowerWorld is not open or no grid is loaded:
   - Press Windows key and search for "B10Reserve.pwb"
   - Open the file in PowerWorld Simulator
3. Once the grid is visible in PowerWorld:
   - Click "Network" in the top menu bar
   - Click "Buses" in the dropdown menu
4. When the buses dialog opens:
   - Wait for it to fully load
   - Take a screenshot showing all bus information
   - The dialog should show bus names, voltages, and areas

IMPORTANT:
- Always wait for windows and dialogs to fully load before interacting
- If PowerWorld is already open with the grid, skip to step 3
- If the buses dialog is already open, just take a screenshot
- The grid areas are "Ativ Island" and "West Side County"
- Take a clear screenshot of the buses table/list
        """.strip()

        self.agent = ComputerAgent(
            model="cua/anthropic/claude-sonnet-4.5",
            tools=[self.computer],
            only_n_most_recent_images=5,
            max_trajectory_budget=15.0,
            instructions=instructions,
            trajectory_dir=self.trajectory_path,  # Save screenshots automatically
        )

    async def run(self) -> APIResult:
        """Execute the bus data extraction task."""
        self.is_running = True
        self.logs = []
        self.final_screenshot = None

        try:
            # Initialize
            await self.initialize()
            self._log("Starting sandbox connection...")
            await self.computer.run()
            self._log("Sandbox connected successfully")

            await self.create_agent()
            self._log("Agent initialized, starting task...")

            # Define the task
            task = """
Look at the current desktop. Open PowerWorld Simulator if not already open,
load the grid file B10Reserve.pwb if needed, then:
1. Click on "Network" in the top menu
2. Click on "Buses" in the dropdown
3. When the buses dialog opens, take a screenshot of the bus data table.

Take a final screenshot showing the buses information clearly.
            """

            messages = [{"role": "user", "content": task}]

            # Run the agent and capture results
            async for result in self.agent.run(messages):
                if not self.is_running:
                    break

                for item in result.get("output", []):
                    item_type = item.get("type", "")

                    # Log agent messages
                    if item_type == "message":
                        content = item.get("content", [])
                        for block in content:
                            text = block.get("text", "") or block.get("output_text", "")
                            if text:
                                self._log(f"Agent: {text[:200]}...")

                    # Capture screenshots - keep the last one
                    elif item_type == "computer_call_output":
                        output_content = item.get("content", [])
                        for output_item in output_content:
                            if output_item.get("type") in ["computer_screenshot", "input_image"]:
                                image_url = output_item.get("image_url", "")
                                if image_url:
                                    self.final_screenshot = image_url
                                    self._log("Screenshot captured")

                    # Log actions
                    elif item_type == "computer_call":
                        action = item.get("action", {})
                        action_type = action.get("type", "unknown")
                        self._log(f"Executing: {action_type}")

            self._log("Task completed, reading screenshot from trajectory...")

            # Get the latest screenshot from saved trajectory
            self.final_screenshot = self._get_latest_screenshot()

            # Process the final screenshot with Anthropic
            if self.final_screenshot:
                from .anthropic_processor import extract_bus_data
                self._log("Sending screenshot to Anthropic for analysis...")
                bus_data = await extract_bus_data(
                    self.final_screenshot,
                    self.settings.anthropic_api_key
                )
                self._log(f"Extracted {len(bus_data.get('buses', []))} buses")

                return APIResult(
                    status="success",
                    data=bus_data,
                    logs=self.logs,
                    final_screenshot=self.final_screenshot
                )
            else:
                self._log(f"No screenshot found in trajectory: {self.trajectory_path}", level="error")
                return APIResult(
                    status="error",
                    error=f"No screenshot found in trajectory: {self.trajectory_path}",
                    logs=self.logs
                )

        except Exception as e:
            error_msg = str(e)
            self._log(f"Error: {error_msg}", level="error")
            logger.error(f"Bus API error: {e}")
            return APIResult(
                status="error",
                error=error_msg,
                logs=self.logs
            )
        finally:
            self.is_running = False
            if self.computer:
                try:
                    await self.computer.disconnect()
                    self._log("Disconnected from sandbox")
                except Exception as e:
                    logger.error(f"Error disconnecting: {e}")

    async def stop(self) -> None:
        """Stop the running task."""
        self._log("Stopping task...")
        self.is_running = False
