"use client";

import { useAuthStatus } from "@/lib/hooks/useAccounts";
import { usePortfolioSummary, usePositions, useSnapshots } from "@/lib/hooks/usePortfolio";
import { formatINR } from "@/lib/utils/formatters";
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

export default function DashboardPage() {
  const { data: statuses, isLoading: authLoading } = useAuthStatus();
  const { data: summary, isLoading: summaryLoading } = usePortfolioSummary();
  const { data: positions } = usePositions();
  const { data: snapshots } = useSnapshots(undefined, 30);

  const loggedIn = statuses?.filter((s) => s.is_logged_in).length ?? 0;
  const total = statuses?.length ?? 0;
  const loading = authLoading || summaryLoading;

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold">Dashboard</h1>

      {/* Summary Cards */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-6">
        <SummaryCard label="Accounts" value={loading ? "-" : `${loggedIn}/${total}`} />
        <SummaryCard
          label="Total P&L"
          value={summary ? formatINR(summary.total_pnl) : "-"}
          color={summary && summary.total_pnl >= 0 ? "profit" : "loss"}
        />
        <SummaryCard
          label="Realized"
          value={summary ? formatINR(summary.total_realized_pnl) : "-"}
          color={summary && summary.total_realized_pnl >= 0 ? "profit" : "loss"}
        />
        <SummaryCard
          label="Unrealized"
          value={summary ? formatINR(summary.total_unrealized_pnl) : "-"}
          color={summary && summary.total_unrealized_pnl >= 0 ? "profit" : "loss"}
        />
        <SummaryCard
          label="Margin Used"
          value={summary ? formatINR(summary.total_margin_used) : "-"}
        />
        <SummaryCard
          label="Positions"
          value={summary ? String(summary.total_position_count) : "-"}
        />
      </div>

      {/* Per-account breakdown */}
      {summary?.accounts && summary.accounts.length > 0 && (
        <div className="overflow-x-auto rounded-lg border border-[var(--card-border)]">
          <table className="w-full text-sm">
            <thead className="bg-[var(--card)] text-left text-[var(--muted)]">
              <tr>
                <th className="px-4 py-3 font-medium">Account</th>
                <th className="px-4 py-3 font-medium">P&L</th>
                <th className="px-4 py-3 font-medium">Realized</th>
                <th className="px-4 py-3 font-medium">Unrealized</th>
                <th className="px-4 py-3 font-medium">Margin Used</th>
                <th className="px-4 py-3 font-medium">Positions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[var(--card-border)]">
              {summary.accounts.map((a: any) => (
                <tr key={a.account_id} className="bg-[var(--card)]">
                  <td className="px-4 py-3 font-medium">{a.account_name}</td>
                  <td className={`px-4 py-3 ${a.total_pnl >= 0 ? "text-profit" : "text-loss"}`}>
                    {formatINR(a.total_pnl)}
                  </td>
                  <td className="px-4 py-3">{formatINR(a.realized_pnl)}</td>
                  <td className="px-4 py-3">{formatINR(a.unrealized_pnl)}</td>
                  <td className="px-4 py-3">{formatINR(a.margin_used)}</td>
                  <td className="px-4 py-3">{a.position_count}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* P&L Chart */}
      {snapshots && snapshots.length > 0 && (
        <div className="rounded-lg border border-[var(--card-border)] bg-[var(--card)] p-4">
          <p className="text-sm font-medium mb-3">Daily P&L (30 days)</p>
          <ResponsiveContainer width="100%" height={250}>
            <LineChart data={snapshots}>
              <CartesianGrid strokeDasharray="3 3" stroke="#333" />
              <XAxis
                dataKey="snapshot_date"
                tick={{ fontSize: 11, fill: "#737373" }}
                tickFormatter={(v) => new Date(v).toLocaleDateString("en-IN", { day: "2-digit", month: "short" })}
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

      {/* Positions Table */}
      {positions && positions.length > 0 && (
        <div className="space-y-2">
          <p className="text-sm font-medium">Open Positions</p>
          <div className="overflow-x-auto rounded-lg border border-[var(--card-border)]">
            <table className="w-full text-sm">
              <thead className="bg-[var(--card)] text-left text-[var(--muted)]">
                <tr>
                  <th className="px-3 py-3 font-medium">Account</th>
                  <th className="px-3 py-3 font-medium">Symbol</th>
                  <th className="px-3 py-3 font-medium">Qty</th>
                  <th className="px-3 py-3 font-medium">Avg</th>
                  <th className="px-3 py-3 font-medium">LTP</th>
                  <th className="px-3 py-3 font-medium">P&L</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[var(--card-border)]">
                {positions.map((p: any) => (
                  <tr key={p.id} className="bg-[var(--card)]">
                    <td className="px-3 py-2.5 font-medium">{p.account_name}</td>
                    <td className="px-3 py-2.5">
                      <span className="font-medium">{p.tradingsymbol}</span>
                      <span className="ml-1 text-xs text-[var(--muted)]">{p.exchange}</span>
                    </td>
                    <td className={`px-3 py-2.5 ${p.quantity > 0 ? "text-green-400" : "text-red-400"}`}>
                      {p.quantity}
                    </td>
                    <td className="px-3 py-2.5">{p.average_price?.toFixed(2) ?? "-"}</td>
                    <td className="px-3 py-2.5">{p.last_price?.toFixed(2) ?? "-"}</td>
                    <td className={`px-3 py-2.5 ${(p.pnl ?? 0) >= 0 ? "text-profit" : "text-loss"}`}>
                      {p.pnl != null ? formatINR(p.pnl) : "-"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {!loading && !summary?.accounts?.length && (
        <div className="rounded-lg border border-[var(--card-border)] bg-[var(--card)] p-6 text-center">
          <p className="text-[var(--muted)]">
            No data yet. Log in to your accounts and positions will appear here.
          </p>
        </div>
      )}
    </div>
  );
}

function SummaryCard({
  label,
  value,
  color,
}: {
  label: string;
  value: string;
  color?: "profit" | "loss";
}) {
  return (
    <div className="rounded-lg border border-[var(--card-border)] bg-[var(--card)] p-4">
      <p className="text-sm text-[var(--muted)]">{label}</p>
      <p
        className={`mt-1 text-xl font-semibold ${
          color === "profit" ? "text-profit" : color === "loss" ? "text-loss" : ""
        }`}
      >
        {value}
      </p>
    </div>
  );
}
