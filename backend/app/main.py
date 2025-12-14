import os
import ssl
import certifi

# Fix SSL certificate verification for macOS - must be set before any other imports
os.environ['SSL_CERT_FILE'] = certifi.where()
os.environ['REQUESTS_CA_BUNDLE'] = certifi.where()

from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import logging
from .websocket.manager import ConnectionManager
from .websocket.handler import WebSocketHandler
from .api.routes import router as api_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="PowerWorld CUA Backend",
    description="Computer User Agent backend for PowerWorld APIs",
    version="2.0.0",
)

# CORS middleware for development and Postman
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(api_router)

# Initialize connection manager
connection_manager = ConnectionManager()


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "powerworld-cua-backend"}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Main WebSocket endpoint for CUA communication."""
    handler = WebSocketHandler(connection_manager)
    await handler.handle_connection(websocket)


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
