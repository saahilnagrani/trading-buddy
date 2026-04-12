"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { getOrders, placeOrders, cancelOrder } from "@/lib/api";
import type { PlaceOrderRequest } from "@/lib/types";

export function useOrders(params?: {
  account_id?: string;
  status?: string;
  limit?: number;
  offset?: number;
}) {
  return useQuery({
    queryKey: ["orders", params],
    queryFn: () => getOrders(params),
    refetchInterval: 10_000,
  });
}

export function usePlaceOrders() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (req: PlaceOrderRequest) => placeOrders(req),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["orders"] }),
  });
}

export function useCancelOrder() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (orderId: string) => cancelOrder(orderId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["orders"] }),
  });
}
