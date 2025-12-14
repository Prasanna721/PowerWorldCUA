export enum MessageType {
  // Outgoing to backend
  START_AGENT = "start_agent",
  STOP_AGENT = "stop_agent",
  RUN_API = "run_api",

  // Incoming from backend
  SCREENSHOT = "screenshot",
  STATUS = "status",
  MESSAGE = "message",
  ERROR = "error",
  AGENT_COMPLETE = "agent_complete",
  API_LOG = "api_log",
  API_RESPONSE = "api_response",
}

export interface WebSocketMessage {
  type: MessageType;
  payload?: unknown;
  timestamp?: number;
}

export interface ScreenshotPayload {
  image_data: string;
  step: number;
}

export interface StatusPayload {
  status: "connecting" | "running" | "idle" | "error" | "completed" | "stopped";
  message?: string;
}

export interface AgentMessagePayload {
  role: "assistant" | "system" | "reasoning";
  content: string;
  action?: string;
}

export interface ConnectionState {
  isConnected: boolean;
  status: StatusPayload["status"];
  statusMessage: string;
}

// New API types
export interface APILogPayload {
  message: string;
  timestamp: number;
  level: string;
}

export interface BusData {
  number?: number;
  name?: string;
  voltage_kv?: number;
  area?: string;
  zone?: string;
  type?: string;
  mw_load?: number;
  mvar_load?: number;
}

export interface ContingencyData {
  number?: number;
  name?: string;
  circuit?: string;
  status?: string;
  violations?: number;
  worst_violation?: string;
  worst_percent?: number;
}

export interface ContingencySummary {
  total_contingencies?: number;
  passed?: number;
  failed?: number;
}

export interface APIResponsePayload {
  endpoint: string;
  status: "success" | "error";
  data?: {
    buses?: BusData[];
    [key: string]: unknown;
  };
  error?: string;
}

export interface RunAPIPayload {
  endpoint: string;
}

// API endpoint definitions
export interface APIEndpoint {
  id: string;
  name: string;
  description: string;
}

export const API_ENDPOINTS: APIEndpoint[] = [
  {
    id: "buses",
    name: "Get Buses",
    description: "Extract bus data from PowerWorld grid",
  },
  {
    id: "contingency",
    name: "Contingency Analysis",
    description: "Run contingency analysis and extract results",
  },
];
