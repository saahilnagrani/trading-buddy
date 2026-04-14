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
          <>
          {/* Mobile cards */}
          <div className="space-y-2 lg:hidden">
            {positions.map((p: any) => (
              <div key={p.id} className="rounded-lg border border-[var(--card-border)] bg-[var(--card)] p-3">
                <div className="flex items-center justify-between gap-3">
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <span className="font-medium truncate">{p.tradingsymbol}</span>
                      <span className="text-[10px] text-[var(--muted)]">{p.exchange}</span>
                      <span className="text-[10px] text-[var(--muted)] uppercase">{p.product}</span>
                    </div>
                  </div>
                  <span className={`text-sm font-semibold tabular-nums shrink-0 ${(p.pnl ?? 0) >= 0 ? "text-profit" : "text-loss"}`}>
                    {p.pnl != null ? formatINR(p.pnl) : "-"}
                  </span>
                </div>
                <div className="grid grid-cols-4 gap-2 mt-2 text-xs">
                  <div>
                    <p className="text-[var(--muted)] text-[10px]">Qty</p>
                    <p className={`tabular-nums ${p.quantity > 0 ? "text-green-400" : "text-red-400"}`}>{p.quantity}</p>
                  </div>
                  <div>
                    <p className="text-[var(--muted)] text-[10px]">Avg</p>
                    <p className="tabular-nums">{p.average_price?.toFixed(2) ?? "-"}</p>
                  </div>
                  <div>
                    <p className="text-[var(--muted)] text-[10px]">LTP</p>
                    <p className="tabular-nums">{p.last_price?.toFixed(2) ?? "-"}</p>
                  </div>
                  <div>
                    <p className="text-[var(--muted)] text-[10px]">Value</p>
                    <p className="tabular-nums">{p.value != null ? formatINR(p.value) : "-"}</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
          {/* Desktop table */}
          <div className="hidden lg:block overflow-x-auto rounded-lg border border-[var(--card-border)]">
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
          </>
        ) : (
          <p className="text-sm text-[var(--muted)]">No open positions.</p>
        )}
      </div>

      {/* Trade History */}
      <div className="space-y-2">
        <h2 className="text-lg font-medium">Trade History (60 days)</h2>
        {trades && trades.length > 0 ? (
          <>
          {/* Mobile cards */}
          <div className="space-y-2 lg:hidden">
            {trades.map((t: any) => (
              <div key={t.id} className="rounded-lg border border-[var(--card-border)] bg-[var(--card)] p-3">
                <div className="flex items-center justify-between gap-3">
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <span className="font-medium truncate">{t.tradingsymbol}</span>
                      <span className={`text-xs font-medium ${t.transaction_type === "BUY" ? "text-green-400" : "text-red-400"}`}>
                        {t.transaction_type}
                      </span>
                    </div>
                    <p className="text-[10px] text-[var(--muted)] mt-0.5">{formatDate(t.trade_date)}</p>
                  </div>
                  <div className="text-right shrink-0 text-xs">
                    <p className="text-[10px] text-[var(--muted)]">Qty × Price</p>
                    <p className="tabular-nums">
                      {t.quantity} × {t.price ? parseFloat(t.price).toFixed(2) : "-"}
                    </p>
                  </div>
                </div>
              </div>
            ))}
          </div>
          {/* Desktop table */}
          <div className="hidden lg:block overflow-x-auto rounded-lg border border-[var(--card-border)]">
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
          </>
        ) : (
          <p className="text-sm text-[var(--muted)]">No trades in the last 60 days.</p>
        )}
      </div>
    </div>
  );
}
