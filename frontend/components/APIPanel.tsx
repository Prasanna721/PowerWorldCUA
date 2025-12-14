"use client";

import { ConnectionState, APILogPayload, APIResponsePayload } from "@/types/messages";
import APIButtonPanel from "./APIButtonPanel";
import LogsPanel from "./LogsPanel";
import ResponsePanel from "./ResponsePanel";

interface APIPanelProps {
  connectionState: ConnectionState;
  apiLogs: APILogPayload[];
  apiResponse: APIResponsePayload | null;
  runningEndpoint: string | null;
  onRunAPI: (endpoint: string) => void;
  onStop: () => void;
}

export default function APIPanel({
  connectionState,
  apiLogs,
  apiResponse,
  runningEndpoint,
  onRunAPI,
  onStop,
}: APIPanelProps) {
  const isRunning = connectionState.status === "running";

  return (
    <div className="h-full w-full bg-black flex flex-col">
      {/* API Buttons at top */}
      <APIButtonPanel
        isRunning={isRunning}
        isConnected={connectionState.isConnected}
        runningEndpoint={runningEndpoint}
        onRunAPI={onRunAPI}
        onStop={onStop}
      />

      {/* Split panel for logs and response */}
      <div className="flex-1 flex overflow-hidden">
        {/* Logs panel - left side */}
        <div className="w-1/2 border-r border-[#4A4A4A]">
          <LogsPanel logs={apiLogs} />
        </div>

        {/* Response panel - right side */}
        <div className="w-1/2">
          <ResponsePanel response={apiResponse} isRunning={isRunning} />
        </div>
      </div>
    </div>
  );
}
