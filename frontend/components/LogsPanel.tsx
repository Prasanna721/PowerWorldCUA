"use client";

import { useRef, useEffect } from "react";
import { APILogPayload } from "@/types/messages";

interface LogsPanelProps {
  logs: APILogPayload[];
}

export default function LogsPanel({ logs }: LogsPanelProps) {
  const logsEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    logsEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [logs]);

  const formatTime = (timestamp: number) => {
    const date = new Date(timestamp * 1000);
    return date.toLocaleTimeString("en-US", {
      hour12: false,
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    });
  };

  const getLevelColor = (level: string) => {
    switch (level) {
      case "error":
        return "text-red-400";
      case "warning":
        return "text-yellow-400";
      default:
        return "text-[#999999]";
    }
  };

  return (
    <div className="h-full flex flex-col bg-[#0D0D0D]">
      <div className="p-3 border-b border-[#4A4A4A]">
        <h3 className="text-sm font-semibold text-[#999999] uppercase tracking-wide">
          Live Logs
        </h3>
      </div>

      <div className="flex-1 overflow-y-auto p-3 font-mono text-xs">
        {logs.length === 0 ? (
          <p className="text-[#666666]">No logs yet. Run an API to see logs.</p>
        ) : (
          <div className="space-y-1">
            {logs.map((log, index) => (
              <div key={index} className="flex gap-2">
                <span className="text-[#666666] flex-shrink-0">
                  [{formatTime(log.timestamp)}]
                </span>
                <span className={getLevelColor(log.level)}>{log.message}</span>
              </div>
            ))}
            <div ref={logsEndRef} />
          </div>
        )}
      </div>
    </div>
  );
}
