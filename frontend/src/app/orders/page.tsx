"use client";

import { useState } from "react";
import { useOrders, useCancelOrder } from "@/lib/hooks/useOrders";
import { useAccounts } from "@/lib/hooks/useAccounts";
import { useOrderWebSocket } from "@/lib/hooks/useWebSocket";
import { formatTime } from "@/lib/utils/formatters";
import { useQueryClient } from "@tanstack/react-query";

const STATUS_COLORS: Record<string, string> = {
  PLACED: "bg-blue-500/10 text-blue-400",
  OPEN: "bg-blue-500/10 text-blue-400",
  COMPLETE: "bg-green-500/10 text-green-400",
  CANCELLED: "bg-yellow-500/10 text-yellow-400",
  REJECTED: "bg-red-500/10 text-red-400",
  PENDING: "bg-gray-500/10 text-gray-400",
  ERROR: "bg-red-500/10 text-red-400",
};

export default function OrdersPage() {
  const [filterAccount, setFilterAccount] = useState<string>("");
  const [filterStatus, setFilterStatus] = useState<string>("");

  const { data: accounts } = useAccounts();
  const { data, isLoading } = useOrders({
    account_id: filterAccount || undefined,
    status: filterStatus || undefined,
    limit: 100,
  });
  const cancelMut = useCancelOrder();
  const qc = useQueryClient();

  // Live WebSocket updates
  useOrderWebSocket(() => {
    qc.invalidateQueries({ queryKey: ["orders"] });
  });

  const orders = data?.orders ?? [];

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold">Order Book</h1>

      {/* Filters */}
      <div className="flex flex-wrap gap-3">
        <select
          value={filterAccount}
          onChange={(e) => setFilterAccount(e.target.value)}
          className="rounded-md border border-[var(--card-border)] bg-[var(--card)] px-3 py-2 text-sm"
        >
          <option value="">All Accounts</option>
          {accounts?.map((a) => (
            <option key={a.id} value={a.id}>
              {a.name}
            </option>
          ))}
        </select>

        <select
          value={filterStatus}
          onChange={(e) => setFilterStatus(e.target.value)}
          className="rounded-md border border-[var(--card-border)] bg-[var(--card)] px-3 py-2 text-sm"
        >
          <option value="">All Statuses</option>
          <option value="PLACED">Placed</option>
          <option value="OPEN">Open</option>
          <option value="COMPLETE">Complete</option>
          <option value="CANCELLED">Cancelled</option>
          <option value="REJECTED">Rejected</option>
        </select>

        <span className="self-center text-sm text-[var(--muted)]">
          {data?.total ?? 0} orders
        </span>
      </div>

      {/* Orders Table */}
      {isLoading ? (
        <p className="text-[var(--muted)]">Loading...</p>
      ) : orders.length === 0 ? (
        <p className="text-[var(--muted)]">No orders found.</p>
      ) : (
        <div className="overflow-x-auto rounded-lg border border-[var(--card-border)]">
          <table className="w-full text-sm">
            <thead className="bg-[var(--card)] text-left text-[var(--muted)]">
              <tr>
                <th className="px-3 py-3 font-medium">Time</th>
                <th className="px-3 py-3 font-medium">Account</th>
                <th className="px-3 py-3 font-medium">Instrument</th>
                <th className="px-3 py-3 font-medium">Side</th>
                <th className="px-3 py-3 font-medium">Qty</th>
                <th className="px-3 py-3 font-medium">Price</th>
                <th className="px-3 py-3 font-medium">Filled</th>
                <th className="px-3 py-3 font-medium">Avg</th>
                <th className="px-3 py-3 font-medium">Status</th>
                <th className="px-3 py-3 font-medium">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[var(--card-border)]">
              {orders.map((o) => (
                <tr key={o.id} className="bg-[var(--card)]">
                  <td className="px-3 py-2.5 text-[var(--muted)]">
                    {formatTime(o.placed_at || o.created_at)}
                  </td>
                  <td className="px-3 py-2.5 font-medium">
                    {o.account_name || "-"}
                  </td>
                  <td className="px-3 py-2.5">
                    <span className="font-medium">{o.tradingsymbol}</span>
                    <span className="ml-1 text-xs text-[var(--muted)]">
                      {o.exchange}
                    </span>
                  </td>
                  <td className="px-3 py-2.5">
                    <span
                      className={
                        o.transaction_type === "BUY"
                          ? "text-green-400"
                          : "text-red-400"
                      }
                    >
                      {o.transaction_type}
                    </span>
                  </td>
                  <td className="px-3 py-2.5">{o.quantity}</td>
                  <td className="px-3 py-2.5">
                    {o.price ? parseFloat(String(o.price)).toFixed(2) : "MKT"}
                  </td>
                  <td className="px-3 py-2.5">{o.filled_quantity}</td>
                  <td className="px-3 py-2.5">
                    {o.average_price
                      ? parseFloat(String(o.average_price)).toFixed(2)
                      : "-"}
                  </td>
                  <td className="px-3 py-2.5">
                    <span
                      className={`rounded-full px-2 py-0.5 text-xs ${
                        STATUS_COLORS[o.status] || STATUS_COLORS.PENDING
                      }`}
                    >
                      {o.status}
                    </span>
                  </td>
                  <td className="px-3 py-2.5">
                    {["PLACED", "OPEN"].includes(o.status) && (
                      <button
                        onClick={() => {
                          if (confirm("Cancel this order?")) {
                            cancelMut.mutate(o.id);
                          }
                        }}
                        className="text-xs text-red-400 hover:text-red-500"
                      >
                        Cancel
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
