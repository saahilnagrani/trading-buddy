"use client";

import { useState } from "react";
import Link from "next/link";
import { useAccounts } from "@/lib/hooks/useAccounts";
import { usePortfolioSummary, usePositions, useTradeHistory } from "@/lib/hooks/usePortfolio";
import { formatINR, formatTime, formatDate } from "@/lib/utils/formatters";

export default function PortfolioPage() {
  const { data: accounts } = useAccounts();
  const { data: summary } = usePortfolioSummary();
  const [selectedAccount, setSelectedAccount] = useState<string>("");
  const { data: positions } = usePositions(selectedAccount || undefined);
  const { data: trades } = useTradeHistory(selectedAccount || undefined, 30);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Portfolio</h1>
        <select
          value={selectedAccount}
          onChange={(e) => setSelectedAccount(e.target.value)}
          className="rounded-md border border-[var(--card-border)] bg-[var(--card)] px-3 py-2 text-sm"
        >
          <option value="">All Accounts</option>
          {accounts?.map((a) => (
            <option key={a.id} value={a.id}>
              {a.name}
            </option>
          ))}
        </select>
      </div>

      {/* Account Cards */}
      {!selectedAccount && summary?.accounts && (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {summary.accounts.map((a: any) => (
            <Link
              key={a.account_id}
              href={`/portfolio/${a.account_id}`}
              className="rounded-lg border border-[var(--card-border)] bg-[var(--card)] p-4 hover:border-brand-600/50 transition-colors"
            >
              <h3 className="font-medium">{a.account_name}</h3>
              <div className="mt-2 grid grid-cols-2 gap-2 text-sm">
                <div>
                  <p className="text-[var(--muted)]">P&L</p>
                  <p className={a.total_pnl >= 0 ? "text-profit" : "text-loss"}>
                    {formatINR(a.total_pnl)}
                  </p>
                </div>
                <div>
                  <p className="text-[var(--muted)]">Margin Used</p>
                  <p>{formatINR(a.margin_used)}</p>
                </div>
                <div>
                  <p className="text-[var(--muted)]">Positions</p>
                  <p>{a.position_count}</p>
                </div>
                <div>
                  <p className="text-[var(--muted)]">Available</p>
                  <p>{formatINR(a.margin_available)}</p>
                </div>
              </div>
            </Link>
          ))}
        </div>
      )}

      {/* Positions */}
      <div className="space-y-2">
        <h2 className="text-lg font-medium">
          Positions {selectedAccount && `(${accounts?.find((a) => a.id === selectedAccount)?.name})`}
        </h2>
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
                    {!selectedAccount && (
                      <p className="text-[10px] text-[var(--muted)] mt-0.5">{p.account_name}</p>
                    )}
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
                  {!selectedAccount && <th className="px-3 py-3 font-medium">Account</th>}
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
                    {!selectedAccount && <td className="px-3 py-2.5">{p.account_name}</td>}
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
        <h2 className="text-lg font-medium">Recent Trades (30 days)</h2>
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
                    <p className="text-[10px] text-[var(--muted)] mt-0.5">
                      {formatDate(t.trade_date)}
                      {!selectedAccount && t.account_name ? ` · ${t.account_name}` : ""}
                    </p>
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
                  {!selectedAccount && <th className="px-3 py-3 font-medium">Account</th>}
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
                    {!selectedAccount && <td className="px-3 py-2.5">{t.account_name}</td>}
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
          <p className="text-sm text-[var(--muted)]">No trades in the last 30 days.</p>
        )}
      </div>
    </div>
  );
}
