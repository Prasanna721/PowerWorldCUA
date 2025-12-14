"use client";

interface InstallButtonProps {
  isRunning: boolean;
  isConnected: boolean;
  onStart: () => void;
  onStop: () => void;
}

export default function InstallButton({
  isRunning,
  isConnected,
  onStart,
  onStop,
}: InstallButtonProps) {
  const handleClick = () => {
    if (isRunning) {
      onStop();
    } else {
      onStart();
    }
  };

  return (
    <button
      onClick={handleClick}
      disabled={!isConnected}
      className={`
        w-full py-3 px-6 font-semibold text-lg transition-all
        border border-[#4A4A4A]
        ${
          !isConnected
            ? "bg-[#222222] text-[#666666] cursor-not-allowed"
            : isRunning
            ? "bg-[#333333] text-white hover:bg-[#444444] cursor-pointer"
            : "bg-[#333333] text-[#FF6B00] hover:bg-[#444444] cursor-pointer"
        }
      `}
    >
      {!isConnected ? (
        "Disconnected"
      ) : isRunning ? (
        <span className="flex items-center justify-center gap-2">
          <span className="w-2 h-2 bg-[#FF6B00] animate-pulse"></span>
          Stop Agent
        </span>
      ) : (
        "Install PowerWorld"
      )}
    </button>
  );
}
