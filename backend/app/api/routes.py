from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import asyncio
import logging
from .bus_service import BusAPIService, LogEntry
from .contingency_service import ContingencyAPIService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["PowerWorld APIs"])


class LogEntryResponse(BaseModel):
    timestamp: float
    message: str
    level: str = "info"


class BusData(BaseModel):
    number: Optional[int] = None
    name: Optional[str] = None
    voltage_kv: Optional[float] = None
    area: Optional[str] = None
    zone: Optional[str] = None
    type: Optional[str] = None
    mw_load: Optional[float] = None
    mvar_load: Optional[float] = None


class BusesResponse(BaseModel):
    status: str
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    logs: List[LogEntryResponse] = []


class ContingencyData(BaseModel):
    number: Optional[int] = None
    name: Optional[str] = None
    circuit: Optional[str] = None
    status: Optional[str] = None
    violations: Optional[int] = None
    worst_violation: Optional[str] = None
    worst_percent: Optional[float] = None


class ContingencySummary(BaseModel):
    total_contingencies: Optional[int] = None
    passed: Optional[int] = None
    failed: Optional[int] = None


class ContingencyResponse(BaseModel):
    status: str
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    logs: List[LogEntryResponse] = []


# Store for active tasks and their results
active_tasks: Dict[str, asyncio.Task] = {}
task_results: Dict[str, BusesResponse] = {}


@router.post("/buses", response_model=BusesResponse)
async def get_buses():
    """
    Execute the CUA agent to extract bus data from PowerWorld.

    This endpoint:
    1. Connects to the Windows sandbox
    2. Opens PowerWorld and navigates to Network > Buses
    3. Captures a screenshot
    4. Sends to Anthropic to extract structured data
    5. Returns JSON with bus information

    Note: This is a long-running operation (30-120 seconds typically)
    """
    logger.info("Starting buses API request...")

    service = BusAPIService()

    try:
        result = await service.run()

        # Convert logs to response format
        logs = [
            LogEntryResponse(
                timestamp=log.timestamp,
                message=log.message,
                level=log.level
            )
            for log in result.logs
        ]

        if result.status == "success":
            return BusesResponse(
                status="success",
                data=result.data,
                logs=logs
            )
        else:
            return BusesResponse(
                status="error",
                error=result.error,
                logs=logs
            )

    except Exception as e:
        logger.error(f"Buses API error: {e}")
        return BusesResponse(
            status="error",
            error=str(e),
            logs=[]
        )


@router.post("/contingency", response_model=ContingencyResponse)
async def run_contingency_analysis():
    """
    Execute the CUA agent to run Contingency Analysis in PowerWorld.

    This endpoint:
    1. Connects to the Windows sandbox
    2. Opens PowerWorld and navigates to Tools > Contingency Analysis
    3. Runs the analysis and waits for completion
    4. Captures a screenshot of the Result tab
    5. Sends to Anthropic to extract structured data
    6. Returns JSON with contingency analysis results

    Note: This is a long-running operation (60-180 seconds typically)
    """
    logger.info("Starting contingency analysis API request...")

    service = ContingencyAPIService()

    try:
        result = await service.run()

        logs = [
            LogEntryResponse(
                timestamp=log.timestamp,
                message=log.message,
                level=log.level
            )
            for log in result.logs
        ]

        if result.status == "success":
            return ContingencyResponse(
                status="success",
                data=result.data,
                logs=logs
            )
        else:
            return ContingencyResponse(
                status="error",
                error=result.error,
                logs=logs
            )

    except Exception as e:
        logger.error(f"Contingency API error: {e}")
        return ContingencyResponse(
            status="error",
            error=str(e),
            logs=[]
        )


@router.get("/health")
async def api_health():
    """Health check for API endpoints."""
    return {"status": "healthy", "service": "powerworld-api"}
