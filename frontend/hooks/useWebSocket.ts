"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import {
  MessageType,
  WebSocketMessage,
  ScreenshotPayload,
  StatusPayload,
  AgentMessagePayload,
  ConnectionState,
  APILogPayload,
  APIResponsePayload,
} from "@/types/messages";

interface UseWebSocketReturn {
  connectionState: ConnectionState;
  currentScreenshot: string | null;
  messages: AgentMessagePayload[];
  apiLogs: APILogPayload[];
  apiResponse: APIResponsePayload | null;
  runningEndpoint: string | null;
  startAgent: () => void;
  stopAgent: () => void;
  runAPI: (endpoint: string) => void;
  reconnect: () => void;
  clearAPIState: () => void;
}

export function useWebSocket(url: string): UseWebSocketReturn {
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  const [connectionState, setConnectionState] = useState<ConnectionState>({
    isConnected: false,
    status: "idle",
    statusMessage: "Disconnected",
  });

  const [currentScreenshot, setCurrentScreenshot] = useState<string | null>(
    null
  );
  const [messages, setMessages] = useState<AgentMessagePayload[]>([]);
  const [apiLogs, setApiLogs] = useState<APILogPayload[]>([]);
  const [apiResponse, setApiResponse] = useState<APIResponsePayload | null>(
    null
  );
  const [runningEndpoint, setRunningEndpoint] = useState<string | null>(null);

  const handleMessage = useCallback((message: WebSocketMessage) => {
    switch (message.type) {
      case MessageType.SCREENSHOT:
        const screenshotPayload = message.payload as ScreenshotPayload;
        setCurrentScreenshot(screenshotPayload.image_data);
        break;

      case MessageType.STATUS:
      case MessageType.AGENT_COMPLETE:
        const statusPayload = message.payload as StatusPayload;
        setConnectionState((prev) => ({
          ...prev,
          status: statusPayload.status,
          statusMessage: statusPayload.message || "",
        }));
        // Clear running endpoint when completed/stopped/error
        if (["completed", "stopped", "error", "idle"].includes(statusPayload.status)) {
          setRunningEndpoint(null);
        }
        break;

      case MessageType.MESSAGE:
        const msgPayload = message.payload as AgentMessagePayload;
        setMessages((prev) => [...prev, msgPayload]);
        break;

      case MessageType.ERROR:
        const errorPayload = message.payload as StatusPayload;
        setConnectionState((prev) => ({
          ...prev,
          status: "error",
          statusMessage: errorPayload.message || "Unknown error",
        }));
        setRunningEndpoint(null);
        break;

      case MessageType.API_LOG:
        const logPayload = message.payload as APILogPayload;
        setApiLogs((prev) => [...prev, logPayload]);
        break;

      case MessageType.API_RESPONSE:
        const responsePayload = message.payload as APIResponsePayload;
        setApiResponse(responsePayload);
        break;
    }
  }, []);

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      return;
    }

    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => {
      console.log("WebSocket connected");
      setConnectionState({
        isConnected: true,
        status: "idle",
        statusMessage: "Connected. Ready to start.",
      });
    };

    ws.onclose = () => {
      console.log("WebSocket disconnected");
      setConnectionState((prev) => ({
        ...prev,
        isConnected: false,
        statusMessage: "Disconnected",
      }));

      // Auto-reconnect after 3 seconds
      reconnectTimeoutRef.current = setTimeout(() => {
        connect();
      }, 3000);
    };

    ws.onerror = (error) => {
      console.error("WebSocket error:", error);
      setConnectionState((prev) => ({
        ...prev,
        status: "error",
        statusMessage: "Connection error",
      }));
    };

    ws.onmessage = (event) => {
      try {
        const message: WebSocketMessage = JSON.parse(event.data);
        handleMessage(message);
      } catch (e) {
        console.error("Failed to parse message:", e);
      }
    };
  }, [url, handleMessage]);

  const sendMessage = useCallback((type: MessageType, payload?: unknown) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      const message: WebSocketMessage = { type, payload };
      wsRef.current.send(JSON.stringify(message));
    }
  }, []);

  const startAgent = useCallback(() => {
    setMessages([]);
    setCurrentScreenshot(null);
    sendMessage(MessageType.START_AGENT);
  }, [sendMessage]);

  const stopAgent = useCallback(() => {
    sendMessage(MessageType.STOP_AGENT);
  }, [sendMessage]);

  const runAPI = useCallback(
    (endpoint: string) => {
      // Clear previous API state
      setApiLogs([]);
      setApiResponse(null);
      setRunningEndpoint(endpoint);
      sendMessage(MessageType.RUN_API, { endpoint });
    },
    [sendMessage]
  );

  const clearAPIState = useCallback(() => {
    setApiLogs([]);
    setApiResponse(null);
  }, []);

  const reconnect = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.close();
    }
    connect();
  }, [connect]);

  useEffect(() => {
    connect();

    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [connect]);

  return {
    connectionState,
    currentScreenshot,
    messages,
    apiLogs,
    apiResponse,
    runningEndpoint,
    startAgent,
    stopAgent,
    runAPI,
    reconnect,
    clearAPIState,
  };
}
