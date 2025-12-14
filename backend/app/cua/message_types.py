from enum import Enum
from typing import Optional, Any
from pydantic import BaseModel
import time


class MessageType(str, Enum):
    # Incoming from frontend
    START_AGENT = "start_agent"
    STOP_AGENT = "stop_agent"
    RUN_API = "run_api"  # New: trigger API endpoint

    # Outgoing to frontend
    SCREENSHOT = "screenshot"
    STATUS = "status"
    MESSAGE = "message"
    ERROR = "error"
    AGENT_COMPLETE = "agent_complete"
    API_LOG = "api_log"  # New: streaming log from API
    API_RESPONSE = "api_response"  # New: final API response


class WebSocketMessage(BaseModel):
    type: MessageType
    payload: Optional[Any] = None
    timestamp: Optional[float] = None

    def __init__(self, **data):
        if "timestamp" not in data or data["timestamp"] is None:
            data["timestamp"] = time.time()
        super().__init__(**data)


class ScreenshotPayload(BaseModel):
    image_data: str  # base64 PNG data URL
    step: int


class StatusPayload(BaseModel):
    status: str  # "connecting", "running", "idle", "error", "completed", "stopped"
    message: Optional[str] = None


class AgentMessagePayload(BaseModel):
    role: str  # "assistant", "system", "reasoning"
    content: str
    action: Optional[str] = None


class APILogPayload(BaseModel):
    """Payload for streaming API logs."""
    message: str
    timestamp: float
    level: str = "info"


class APIResponsePayload(BaseModel):
    """Payload for final API response."""
    endpoint: str
    status: str  # "success", "error"
    data: Optional[Any] = None
    error: Optional[str] = None


class RunAPIPayload(BaseModel):
    """Payload for triggering an API endpoint."""
    endpoint: str  # "buses", etc.
