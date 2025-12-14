"use client";

import { API_ENDPOINTS } from "@/types/messages";

interface APIButtonPanelProps {
  isRunning: boolean;
  isConnected: boolean;
  runningEndpoint: string | null;
  onRunAPI: (endpoint: string) => void;
  onStop: () => void;
}

export default function APIButtonPanel({
  isRunning,
  isConnected,
  runningEndpoint,
  onRunAPI,
  onStop,
}: APIButtonPanelProps) {
  return (
    <div className="p-4 border-b border-[#4A4A4A]">
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-sm font-semibold text-[#999999] uppercase tracking-wide">
          PowerWorld APIs
        </h2>
        {isRunning && (
          <button
            onClick={onStop}
            className="px-3 py-1 text-xs bg-[#333333] border border-[#4A4A4A] text-red-400 hover:bg-[#444444] transition-colors cursor-pointer"
          >
            Stop
          </button>
        )}
      </div>

      <div className="flex flex-wrap gap-2">
        {API_ENDPOINTS.map((endpoint) => {
          const isThisRunning = runningEndpoint === endpoint.id;
          return (
            <button
              key={endpoint.id}
              onClick={() => onRunAPI(endpoint.id)}
              disabled={!isConnected || isRunning}
              className={`
                px-4 py-2 font-medium transition-all
                border border-[#4A4A4A]
                ${
                  !isConnected || isRunning
                    ? "bg-[#222222] text-[#666666] cursor-not-allowed"
                    : "bg-[#333333] text-[#FF6B00] hover:bg-[#444444] cursor-pointer"
                }
              `}
              title={endpoint.description}
            >
              {isThisRunning ? (
                <span className="flex items-center gap-2">
                  <span className="w-2 h-2 bg-[#FF6B00] animate-pulse"></span>
                  Running...
                </span>
              ) : (
                endpoint.name
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
}
