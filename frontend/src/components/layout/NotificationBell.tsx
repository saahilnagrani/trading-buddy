"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import axios from "axios";
import { formatTime } from "@/lib/utils/formatters";

const api = axios.create({ baseURL: "/api" });

interface NotifItem {
  id: string;
  type: string;
  title: string;
  body: string | null;
  is_read: boolean;
  created_at: string;
}

export function NotificationBell() {
  const qc = useQueryClient();
  const [open, setOpen] = useState(false);

  const { data: count } = useQuery({
    queryKey: ["notif-count"],
    queryFn: async () => (await api.get<{ count: number }>("/notifications/unread-count")).data.count,
    refetchInterval: 15_000,
  });

  const { data: notifs } = useQuery({
    queryKey: ["notifs"],
    queryFn: async () => (await api.get<NotifItem[]>("/notifications", { params: { limit: 20 } })).data,
    enabled: open,
  });

  const markAllRead = useMutation({
    mutationFn: async () => await api.put("/notifications/read-all"),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["notif-count"] });
      qc.invalidateQueries({ queryKey: ["notifs"] });
    },
  });

  return (
    <div className="relative">
      <button
        onClick={() => setOpen(!open)}
        className="relative rounded-md p-1.5 text-[var(--muted)] hover:text-white transition-colors"
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          width="18"
          height="18"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9" />
          <path d="M10.3 21a1.94 1.94 0 0 0 3.4 0" />
        </svg>
        {(count ?? 0) > 0 && (
          <span className="absolute -right-1 -top-1 flex h-4 w-4 items-center justify-center rounded-full bg-red-500 text-[10px] font-bold text-white">
            {count! > 9 ? "9+" : count}
          </span>
        )}
      </button>

      {open && (
        <div className="absolute right-0 top-10 z-50 w-80 rounded-lg border border-[var(--card-border)] bg-[var(--card)] shadow-xl">
          <div className="flex items-center justify-between border-b border-[var(--card-border)] px-3 py-2">
            <span className="text-sm font-medium">Notifications</span>
            {(count ?? 0) > 0 && (
              <button
                onClick={() => markAllRead.mutate()}
                className="text-xs text-brand-500 hover:text-brand-600"
              >
                Mark all read
              </button>
            )}
          </div>
          <div className="max-h-80 overflow-y-auto">
            {notifs && notifs.length > 0 ? (
              notifs.map((n) => (
                <div
                  key={n.id}
                  className={`border-b border-[var(--card-border)] px-3 py-2.5 text-sm ${
                    !n.is_read ? "bg-brand-600/5" : ""
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-medium text-xs">
                      {!n.is_read && (
                        <span className="mr-1 inline-block h-1.5 w-1.5 rounded-full bg-brand-500" />
                      )}
                      {n.title}
                    </span>
                    <span className="text-xs text-[var(--muted)]">
                      {formatTime(n.created_at)}
                    </span>
                  </div>
                  {n.body && (
                    <p className="mt-0.5 text-xs text-[var(--muted)]">{n.body}</p>
                  )}
                </div>
              ))
            ) : (
              <p className="px-3 py-4 text-center text-sm text-[var(--muted)]">
                No notifications
              </p>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
