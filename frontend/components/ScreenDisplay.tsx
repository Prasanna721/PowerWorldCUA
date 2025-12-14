"use client";

interface ScreenDisplayProps {
  screenshot: string | null;
  status: string;
  statusMessage: string;
}

export default function ScreenDisplay({
  screenshot,
  status,
  statusMessage,
}: ScreenDisplayProps) {
  return (
    <div className="h-full w-full bg-black flex flex-col">
      {/* Header */}
      <div className="p-4 border-b border-[#4A4A4A] flex items-center justify-between">
        <h2 className="text-sm font-semibold text-[#999999] uppercase tracking-wide">
          Sandbox Screen
        </h2>
        <span className="text-xs text-[#666666]">Windows Cloud Sandbox</span>
      </div>

      {/* Screen Area */}
      <div className="flex-1 flex items-center justify-center p-4 overflow-hidden">
        {screenshot ? (
          <div className="relative w-full h-full flex items-center justify-center">
            <img
              src={screenshot}
              alt="Sandbox Screen"
              className="max-w-full max-h-full object-contain border border-[#4A4A4A]"
              style={{ imageRendering: "auto" }}
            />
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center text-center">
            <div className="w-24 h-24 border-2 border-[#4A4A4A] flex items-center justify-center mb-4">
              <svg
                className="w-12 h-12 text-[#4A4A4A]"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="square"
                  strokeLinejoin="miter"
                  strokeWidth={1}
                  d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"
                />
              </svg>
            </div>
            <p className="text-[#666666] text-lg">
              {status === "connecting"
                ? "Connecting to sandbox..."
                : status === "running"
                ? "Waiting for screenshot..."
                : "No screen capture"}
            </p>
            <p className="text-[#4A4A4A] text-sm mt-2 max-w-md">
              {statusMessage || "Click 'Install PowerWorld' to start the agent"}
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
