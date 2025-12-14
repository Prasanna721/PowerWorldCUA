"use client";

import { useWebSocket } from "@/hooks/useWebSocket";
import ControlPanel from "@/components/ControlPanel";
import APIPanel from "@/components/APIPanel";

const WS_URL = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000/ws";

export default function Home() {
  const {
    connectionState,
    apiLogs,
    apiResponse,
    runningEndpoint,
    runAPI,
    startAgent,
    stopAgent,
    reconnect,
  } = useWebSocket(WS_URL);

  return (
    <main className="h-screen w-screen bg-black flex overflow-hidden">
      {/* Left Panel - Control Panel */}
      <div className="w-80 h-full border-r border-[#4A4A4A] flex-shrink-0">
        <ControlPanel
          connectionState={connectionState}
          onReconnect={reconnect}
          onStart={startAgent}
          onStop={stopAgent}
        />
      </div>

      {/* Right Panel - API Panel */}
      <div className="flex-1 h-full">
        <APIPanel
          connectionState={connectionState}
          apiLogs={apiLogs}
          apiResponse={apiResponse}
          runningEndpoint={runningEndpoint}
          onRunAPI={runAPI}
          onStop={stopAgent}
        />
      </div>
    </main>
  );
}
