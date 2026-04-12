"use client";

import { useEffect, useRef, useCallback, useState } from "react";
import type { OrderUpdate } from "@/lib/types";

export function useOrderWebSocket(onUpdate?: (update: OrderUpdate) => void) {
  const wsRef = useRef<WebSocket | null>(null);
  const [connected, setConnected] = useState(false);
  const [lastUpdate, setLastUpdate] = useState<OrderUpdate | null>(null);

  const connect = useCallback(() => {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || window.location.origin;
    const wsUrl = apiUrl.replace(/^http/, "ws");
    const ws = new WebSocket(`${wsUrl}/ws/orders`);

    ws.onopen = () => setConnected(true);
    ws.onclose = () => {
      setConnected(false);
      // Reconnect after 3 seconds
      setTimeout(connect, 3000);
    };
    ws.onerror = () => ws.close();

    ws.onmessage = (event) => {
      try {
        const update: OrderUpdate = JSON.parse(event.data);
        setLastUpdate(update);
        onUpdate?.(update);
      } catch {
        // Ignore parse errors
      }
    };

    wsRef.current = ws;
  }, [onUpdate]);

  useEffect(() => {
    connect();
    return () => {
      wsRef.current?.close();
    };
  }, [connect]);

  return { connected, lastUpdate };
}
