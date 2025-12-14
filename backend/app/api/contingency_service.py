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


class ContingencyAPIService:
    """Service to run Contingency Analysis in PowerWorld via CUA agent."""

    def __init__(self, log_callback=None):
        self.settings = get_settings()
        self.computer: Optional[Computer] = None
        self.agent: Optional[ComputerAgent] = None
        self.is_running = False
        self.logs: List[LogEntry] = []
        self.final_screenshot: Optional[str] = None
        self.log_callback = log_callback
        self.trajectory_path: Optional[str] = None

    def _log(self, message: str, level: str = "info"):
        """Add a log entry and optionally stream it."""
        entry = LogEntry(timestamp=time.time(), message=message, level=level)
        self.logs.append(entry)
        logger.info(f"[ContingencyAPI] {message}")
        if self.log_callback:
            asyncio.create_task(self.log_callback(entry))

    def _get_all_screenshots(self) -> List[str]:
        """Read all screenshots from saved trajectory."""
        if not self.trajectory_path or not os.path.exists(self.trajectory_path):
            return []

        # Find all PNG files in trajectory directory
        pattern = os.path.join(self.trajectory_path, "**", "*.png")
        screenshots = glob.glob(pattern, recursive=True)

        if not screenshots:
            return []

        # Sort by modification time
        screenshots.sort(key=os.path.getmtime)

        result = []
        for screenshot_path in screenshots:
            with open(screenshot_path, "rb") as f:
                image_data = base64.b64encode(f.read()).decode("utf-8")
            result.append(f"data:image/png;base64,{image_data}")

        self._log(f"Found {len(result)} screenshots in trajectory")
        return result

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
        """Create the ComputerAgent with contingency analysis instructions."""
        if not self.computer:
            raise RuntimeError("Computer not initialized")

        self._log("Creating CUA agent...")

        # Create unique trajectory directory for this run
        trajectory_base = os.path.join(os.path.dirname(__file__), "..", "..", "trajectories")
        run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.trajectory_path = os.path.join(trajectory_base, f"contingency_api_{run_id}")
        os.makedirs(self.trajectory_path, exist_ok=True)
        self._log(f"Trajectory will be saved to: {self.trajectory_path}")

        instructions = """
You are automating PowerWorld Simulator to run Contingency Analysis.

TASK: Run contingency analysis and capture results for each contingency.

STEPS:
1. If PowerWorld is not open, press Windows key and search for "B10Reserve.pwb", open it
2. Once grid is visible, click "Tools" > "Contingency Analysis"
3. Click "Start Run" and wait for analysis to complete
4. After completion, there are 3 tabs: Contingency, Options, Results
5. Select the Contingency tab (if not already selected)
6. For EACH contingency row:
   - Click on the row to select it
   - Click the "Results" tab
   - Take a screenshot of the results
   - Go back to "Contingency" tab
   - Repeat for the next row
7. Do this for all contingency rows (Row 1, Row 2, Row 3, etc.)

IMPORTANT:
- Take a screenshot after viewing Results for EACH contingency
- Each screenshot shows one contingency's detailed results
- Continue until all contingencies have been captured
        """.strip()

        self.agent = ComputerAgent(
            model="cua/anthropic/claude-sonnet-4.5",
            tools=[self.computer],
            only_n_most_recent_images=5,
            max_trajectory_budget=20.0,  # Higher budget for more complex task
            instructions=instructions,
            trajectory_dir=self.trajectory_path,
        )

    async def run(self) -> APIResult:
        """Execute the contingency analysis task."""
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
Open PowerWorld with B10Reserve.pwb if not already open, then:
1. Click "Tools" > "Contingency Analysis"
2. Click "Start Run" and wait for completion
3. Go to Contingency tab
4. For each contingency row: click the row, click Results tab, take screenshot, go back to Contingency tab
5. Repeat for all contingency rows
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

                    # Log actions
                    elif item_type == "computer_call":
                        action = item.get("action", {})
                        action_type = action.get("type", "unknown")
                        self._log(f"Executing: {action_type}")

            self._log("Task completed, reading screenshots from trajectory...")

            # Get ALL screenshots from saved trajectory
            screenshots = self._get_all_screenshots()

            # Process all screenshots with Anthropic
            if screenshots:
                from .anthropic_processor import extract_contingency_data_multi
                self._log(f"Sending {len(screenshots)} screenshots to Anthropic for analysis...")
                contingency_data = await extract_contingency_data_multi(
                    screenshots,
                    self.settings.anthropic_api_key
                )
                num_contingencies = len(contingency_data.get('contingencies', []))
                self._log(f"Extracted {num_contingencies} contingencies")

                return APIResult(
                    status="success",
                    data=contingency_data,
                    logs=self.logs,
                    final_screenshot=screenshots[-1] if screenshots else None
                )
            else:
                self._log(f"No screenshots found in trajectory: {self.trajectory_path}", level="error")
                return APIResult(
                    status="error",
                    error=f"No screenshots found in trajectory: {self.trajectory_path}",
                    logs=self.logs
                )

        except Exception as e:
            error_msg = str(e)
            self._log(f"Error: {error_msg}", level="error")
            logger.error(f"Contingency API error: {e}")
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
