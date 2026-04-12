"use client";

import { cn } from "@/lib/utils/formatters";

interface Props {
  isLoggedIn: boolean;
}

export function AccountStatusBadge({ isLoggedIn }: Props) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium",
        isLoggedIn
          ? "bg-green-500/10 text-green-400"
          : "bg-red-500/10 text-red-400"
      )}
    >
      <span
        className={cn(
          "h-1.5 w-1.5 rounded-full",
          isLoggedIn ? "bg-green-400" : "bg-red-400"
        )}
      />
      {isLoggedIn ? "Connected" : "Disconnected"}
    </span>
  );
}
