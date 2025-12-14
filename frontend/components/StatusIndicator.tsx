"use client";

interface StatusIndicatorProps {
  isConnected: boolean;
  status: string;
  message: string;
}

export default function StatusIndicator({
  isConnected,
  status,
  message,
}: StatusIndicatorProps) {
  const getStatusColor = () => {
    if (!isConnected) return "bg-red-500";
    switch (status) {
      case "running":
      case "connecting":
        return "bg-[#FF6B00]";
      case "completed":
        return "bg-green-500";
      case "error":
        return "bg-red-500";
      default:
        return "bg-[#666666]";
    }
  };

  return (
    <div className="flex items-start gap-3">
      <div className={`w-3 h-3 mt-1 ${getStatusColor()} flex-shrink-0`}></div>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-white capitalize">
          {isConnected ? status : "Disconnected"}
        </p>
        <p className="text-xs text-[#999999] mt-0.5 break-words">{message}</p>
      </div>
    </div>
  );
}
