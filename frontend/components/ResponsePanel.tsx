"use client";

import { APIResponsePayload } from "@/types/messages";

interface ResponsePanelProps {
  response: APIResponsePayload | null;
  isRunning: boolean;
}

export default function ResponsePanel({
  response,
  isRunning,
}: ResponsePanelProps) {
  const formatJSON = (data: unknown) => {
    try {
      return JSON.stringify(data, null, 2);
    } catch {
      return String(data);
    }
  };

  return (
    <div className="h-full flex flex-col bg-[#0D0D0D]">
      <div className="p-3 border-b border-[#4A4A4A]">
        <h3 className="text-sm font-semibold text-[#999999] uppercase tracking-wide">
          API Response
        </h3>
      </div>

      <div className="flex-1 overflow-y-auto p-3">
        {isRunning ? (
          <div className="flex items-center justify-center h-full">
            <div className="text-center">
              <div className="w-8 h-8 border-2 border-[#FF6B00] border-t-transparent animate-spin mx-auto mb-3"></div>
              <p className="text-[#666666]">Processing...</p>
            </div>
          </div>
        ) : response ? (
          <div className="space-y-3">
            {/* Status badge */}
            <div className="flex items-center gap-2">
              <span
                className={`px-2 py-1 text-xs font-medium ${
                  response.status === "success"
                    ? "bg-green-900 text-green-300"
                    : "bg-red-900 text-red-300"
                }`}
              >
                {response.status.toUpperCase()}
              </span>
              <span className="text-[#666666] text-sm">
                Endpoint: {response.endpoint}
              </span>
            </div>

            {/* Error message */}
            {response.error && (
              <div className="p-3 bg-red-900/20 border border-red-800 text-red-300 text-sm">
                {response.error}
              </div>
            )}

            {/* Data */}
            {response.data && (
              <div className="font-mono text-xs">
                <pre className="p-3 bg-[#1A1A1A] border border-[#4A4A4A] overflow-x-auto text-[#E5E5E5] whitespace-pre-wrap">
                  {formatJSON(response.data)}
                </pre>
              </div>
            )}
          </div>
        ) : (
          <div className="flex items-center justify-center h-full">
            <p className="text-[#666666] text-center">
              No response yet.
              <br />
              Run an API to see results.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
