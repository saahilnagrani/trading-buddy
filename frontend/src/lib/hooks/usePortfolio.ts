"use client";

import { useQuery } from "@tanstack/react-query";
import axios from "axios";

const api = axios.create({ baseURL: "/api" });

export function usePortfolioSummary() {
  return useQuery({
    queryKey: ["portfolio-summary"],
    queryFn: async () => (await api.get("/portfolio/summary")).data,
    refetchInterval: 30_000,
  });
}

export function usePositions(accountId?: string) {
  return useQuery({
    queryKey: ["positions", accountId],
    queryFn: async () =>
      (await api.get("/portfolio/positions", { params: { account_id: accountId } })).data,
    refetchInterval: 30_000,
  });
}

export function useSnapshots(accountId?: string, days: number = 30) {
  return useQuery({
    queryKey: ["snapshots", accountId, days],
    queryFn: async () =>
      (await api.get("/portfolio/snapshots", { params: { account_id: accountId, days } })).data,
  });
}

export function useTradeHistory(accountId?: string, days: number = 30) {
  return useQuery({
    queryKey: ["trade-history", accountId, days],
    queryFn: async () =>
      (await api.get("/portfolio/trades", { params: { account_id: accountId, days } })).data,
  });
}
