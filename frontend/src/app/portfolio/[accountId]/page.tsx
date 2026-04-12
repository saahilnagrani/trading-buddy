"use client";

import { useParams } from "next/navigation";
import { useAccounts } from "@/lib/hooks/useAccounts";
import { usePositions, useSnapshots, useTradeHistory } from "@/lib/hooks/usePortfolio";
import { formatINR, formatDate } from "@/lib/utils/formatters";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from "recharts";

export default function AccountPortfolioPage() {
  const { accountId } = useParams<{ accountId: string }>();
  const { data: accounts } = useAccounts();
  const { data: positions } = usePositions(accountId);
  const { data: snapshots } = useSnapshots(accountId, 60);
  const { data: trades } = useTradeHistory(accountId, 60);

  const account = accounts?.find((a) => a.id === accountId);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">{account?.name ?? "Account"}</h1>
        {account?.owner_name && (
          <p className="text-sm text-[var(--muted)]">Owner: {account.owner_name}</p>
        )}
      </div>

      {/* P&L Chart */}
      {snapshots && snapshots.length > 0 && (
        <div className="rounded-lg border border-[var(--card-border)] bg-[var(--card)] p-4">
          <p className="text-sm font-medium mb-3">P&L History (60 days)</p>
          <ResponsiveContainer width="100%" height={250}>
            <LineChart data={snapshots}>
              <CartesianGrid strokeDasharray="3 3" stroke="#333" />
              <XAxis
                dataKey="snapshot_date"
                tick={{ fontSize: 11, fill: "#737373" }}
                tickFormatter={(v) =>
                  new Date(v).toLocaleDateString("en-IN", { day: "2-digit", month: "short" })
                }
              />
              <YAxis
                tick={{ fontSize: 11, fill: "#737373" }}
                tickFormatter={(v) => `${(v / 1000).toFixed(0)}k`}
              />
              <Tooltip
                contentStyle={{ backgroundColor: "#141414", border: "1px solid #262626" }}
                formatter={(value: number) => [formatINR(value), "P&L"]}
              />
              <ReferenceLine y={0} stroke="#555" />
              <Line type="monotone" dataKey="total_pnl" stroke="#3b82f6" dot={false} strokeWidth={2} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Positions */}
      <div className="space-y-2">
        <h2 className="text-lg font-medium">Open Positions</h2>
        {positions && positions.length > 0 ? (
          <div className="overflow-x-auto rounded-lg border border-[var(--card-border)]">
            <table className="w-full text-sm">
              <thead className="bg-[var(--card)] text-left text-[var(--muted)]">
                <tr>
                  <th className="px-3 py-3 font-medium">Symbol</th>
                  <th className="px-3 py-3 font-medium">Product</th>
                  <th className="px-3 py-3 font-medium">Qty</th>
                  <th className="px-3 py-3 font-medium">Avg Price</th>
                  <th className="px-3 py-3 font-medium">LTP</th>
                  <th className="px-3 py-3 font-medium">P&L</th>
                  <th className="px-3 py-3 font-medium">Value</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[var(--card-border)]">
                {positions.map((p: any) => (
                  <tr key={p.id} className="bg-[var(--card)]">
                    <td className="px-3 py-2.5 font-medium">
                      {p.tradingsymbol}
                      <span className="ml-1 text-xs text-[var(--muted)]">{p.exchange}</span>
                    </td>
                    <td className="px-3 py-2.5 text-[var(--muted)]">{p.product}</td>
                    <td className={`px-3 py-2.5 ${p.quantity > 0 ? "text-green-400" : "text-red-400"}`}>
                      {p.quantity}
                    </td>
                    <td className="px-3 py-2.5">{p.average_price?.toFixed(2) ?? "-"}</td>
                    <td className="px-3 py-2.5">{p.last_price?.toFixed(2) ?? "-"}</td>
                    <td className={`px-3 py-2.5 ${(p.pnl ?? 0) >= 0 ? "text-profit" : "text-loss"}`}>
                      {p.pnl != null ? formatINR(p.pnl) : "-"}
                    </td>
                    <td className="px-3 py-2.5">{p.value != null ? formatINR(p.value) : "-"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="text-sm text-[var(--muted)]">No open positions.</p>
        )}
      </div>

      {/* Trade History */}
      <div className="space-y-2">
        <h2 className="text-lg font-medium">Trade History (60 days)</h2>
        {trades && trades.length > 0 ? (
          <div className="overflow-x-auto rounded-lg border border-[var(--card-border)]">
            <table className="w-full text-sm">
              <thead className="bg-[var(--card)] text-left text-[var(--muted)]">
                <tr>
                  <th className="px-3 py-3 font-medium">Date</th>
                  <th className="px-3 py-3 font-medium">Symbol</th>
                  <th className="px-3 py-3 font-medium">Side</th>
                  <th className="px-3 py-3 font-medium">Qty</th>
                  <th className="px-3 py-3 font-medium">Price</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[var(--card-border)]">
                {trades.map((t: any) => (
                  <tr key={t.id} className="bg-[var(--card)]">
                    <td className="px-3 py-2.5 text-[var(--muted)]">{formatDate(t.trade_date)}</td>
                    <td className="px-3 py-2.5 font-medium">{t.tradingsymbol}</td>
                    <td className={`px-3 py-2.5 ${t.transaction_type === "BUY" ? "text-green-400" : "text-red-400"}`}>
                      {t.transaction_type}
                    </td>
                    <td className="px-3 py-2.5">{t.quantity}</td>
                    <td className="px-3 py-2.5">{t.price ? parseFloat(t.price).toFixed(2) : "-"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="text-sm text-[var(--muted)]">No trades in the last 60 days.</p>
        )}
      </div>
    </div>
  );
}
