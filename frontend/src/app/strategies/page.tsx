"use client";

import { useState, useMemo } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useAccounts } from "@/lib/hooks/useAccounts";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
  ResponsiveContainer,
} from "recharts";
import { calculatePayoff, type PayoffLeg } from "@/lib/utils/payoff";
import { formatINR } from "@/lib/utils/formatters";
import axios from "axios";

const api = axios.create({ baseURL: (process.env.NEXT_PUBLIC_API_URL || "") + "/api" });

interface LegForm {
  leg_number: number;
  instrument_type: "CE" | "PE" | "FUT";
  strike: string;
  transaction_type: "BUY" | "SELL";
  quantity: string;
  price: string;
  tradingsymbol: string;
}

const EMPTY_LEG: () => LegForm = () => ({
  leg_number: 1,
  instrument_type: "CE",
  strike: "",
  transaction_type: "BUY",
  quantity: "25",
  price: "",
  tradingsymbol: "",
});

export default function StrategiesPage() {
  const qc = useQueryClient();
  const { data: accounts } = useAccounts();

  // Templates
  const { data: templates } = useQuery({
    queryKey: ["strategy-templates"],
    queryFn: async () => (await api.get("/strategies/templates")).data as Record<string, any>,
  });

  // Existing strategies
  const { data: strategies } = useQuery({
    queryKey: ["strategies"],
    queryFn: async () => (await api.get("/strategies")).data as any[],
  });

  // Builder state
  const [name, setName] = useState("");
  const [underlying, setUnderlying] = useState("NIFTY");
  const [strategyType, setStrategyType] = useState("CUSTOM");
  const [expiry, setExpiry] = useState("");
  const [legs, setLegs] = useState<LegForm[]>([EMPTY_LEG()]);
  const [selectedAccounts, setSelectedAccounts] = useState<string[]>([]);
  const [uniformLots, setUniformLots] = useState("1");
  const [showBuilder, setShowBuilder] = useState(false);

  // Payoff calculation (client-side, real-time)
  const payoff = useMemo(() => {
    const payoffLegs: PayoffLeg[] = legs
      .filter((l) => l.strike && l.quantity)
      .map((l) => ({
        strike: parseFloat(l.strike),
        instrumentType: l.instrument_type,
        transactionType: l.transaction_type,
        quantity: parseInt(l.quantity),
        premium: parseFloat(l.price) || 0,
      }));
    return calculatePayoff(payoffLegs);
  }, [legs]);

  const createMut = useMutation({
    mutationFn: async (data: any) => (await api.post("/strategies", data)).data,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["strategies"] });
    },
  });

  const executeMut = useMutation({
    mutationFn: async ({ id, body }: { id: string; body: any }) =>
      (await api.post(`/strategies/${id}/execute`, body)).data,
  });

  function applyTemplate(key: string) {
    const tpl = templates?.[key];
    if (!tpl) return;
    setName(tpl.name);
    setStrategyType(tpl.type);
    const spotEstimate = underlying === "NIFTY" ? 24000 : underlying === "BANKNIFTY" ? 52000 : 20000;
    setLegs(
      tpl.legs.map((l: any, i: number) => ({
        leg_number: i + 1,
        instrument_type: l.instrument_type,
        strike: String(spotEstimate + (l.strike_offset || 0)),
        transaction_type: l.transaction_type,
        quantity: "25",
        price: "",
        tradingsymbol: "",
      }))
    );
  }

  function addLeg() {
    setLegs((prev) => [
      ...prev,
      { ...EMPTY_LEG(), leg_number: prev.length + 1 },
    ]);
  }

  function removeLeg(idx: number) {
    setLegs((prev) => prev.filter((_, i) => i !== idx).map((l, i) => ({ ...l, leg_number: i + 1 })));
  }

  function updateLeg(idx: number, field: keyof LegForm, value: string) {
    setLegs((prev) => {
      const updated = [...prev];
      (updated[idx] as any)[field] = value;
      return updated;
    });
  }

  async function handleCreate() {
    const result = await createMut.mutateAsync({
      name,
      strategy_type: strategyType,
      underlying,
      expiry_date: expiry || null,
      legs: legs.map((l) => ({
        leg_number: l.leg_number,
        exchange: "NFO",
        tradingsymbol: l.tradingsymbol || null,
        instrument_type: l.instrument_type,
        strike: parseFloat(l.strike) || null,
        transaction_type: l.transaction_type,
        quantity: parseInt(l.quantity) || 25,
        order_type: "LIMIT",
        price: parseFloat(l.price) || null,
      })),
    });
    alert(`Strategy "${result.name}" created. Set tradingsymbols and execute.`);
  }

  const loggedIn = accounts?.filter((a) => a.token_status.is_logged_in) ?? [];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Strategies</h1>
        <button
          onClick={() => setShowBuilder(!showBuilder)}
          className="rounded-md bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700"
        >
          {showBuilder ? "Close Builder" : "New Strategy"}
        </button>
      </div>

      {showBuilder && (
        <div className="space-y-4">
          {/* Template selector */}
          <div>
            <label className="block text-sm text-[var(--muted)] mb-1">Start from template</label>
            <div className="flex flex-wrap gap-2">
              {templates &&
                Object.entries(templates).map(([key, tpl]: [string, any]) => (
                  <button
                    key={key}
                    onClick={() => applyTemplate(key)}
                    className="rounded-md border border-[var(--card-border)] bg-[var(--card)] px-3 py-1.5 text-sm hover:border-brand-600 transition-colors"
                  >
                    {tpl.name}
                  </button>
                ))}
            </div>
          </div>

          {/* Strategy details */}
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-4">
            <div>
              <label className="block text-sm text-[var(--muted)] mb-1">Name</label>
              <input
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="w-full rounded-md border border-[var(--card-border)] bg-[var(--background)] px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label className="block text-sm text-[var(--muted)] mb-1">Underlying</label>
              <select
                value={underlying}
                onChange={(e) => setUnderlying(e.target.value)}
                className="w-full rounded-md border border-[var(--card-border)] bg-[var(--background)] px-3 py-2 text-sm"
              >
                <option>NIFTY</option>
                <option>BANKNIFTY</option>
                <option>FINNIFTY</option>
                <option>SENSEX</option>
              </select>
            </div>
            <div>
              <label className="block text-sm text-[var(--muted)] mb-1">Expiry</label>
              <input
                type="date"
                value={expiry}
                onChange={(e) => setExpiry(e.target.value)}
                className="w-full rounded-md border border-[var(--card-border)] bg-[var(--background)] px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label className="block text-sm text-[var(--muted)] mb-1">Type</label>
              <input
                value={strategyType}
                onChange={(e) => setStrategyType(e.target.value)}
                className="w-full rounded-md border border-[var(--card-border)] bg-[var(--background)] px-3 py-2 text-sm"
                readOnly
              />
            </div>
          </div>

          {/* Legs */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <p className="text-sm font-medium">Legs</p>
              <button onClick={addLeg} className="text-sm text-brand-500 hover:text-brand-600">
                + Add Leg
              </button>
            </div>
            {legs.map((leg, idx) => (
              <div key={idx} className="grid grid-cols-3 gap-2 sm:grid-cols-7 items-end rounded-lg border border-[var(--card-border)] bg-[var(--card)] p-3">
                <div>
                  <label className="block text-xs text-[var(--muted)]">Type</label>
                  <select
                    value={leg.instrument_type}
                    onChange={(e) => updateLeg(idx, "instrument_type", e.target.value)}
                    className="w-full rounded border border-[var(--card-border)] bg-[var(--background)] px-2 py-1.5 text-sm"
                  >
                    <option value="CE">CE</option>
                    <option value="PE">PE</option>
                    <option value="FUT">FUT</option>
                  </select>
                </div>
                <div>
                  <label className="block text-xs text-[var(--muted)]">Strike</label>
                  <input
                    value={leg.strike}
                    onChange={(e) => updateLeg(idx, "strike", e.target.value)}
                    className="w-full rounded border border-[var(--card-border)] bg-[var(--background)] px-2 py-1.5 text-sm"
                    placeholder="24000"
                  />
                </div>
                <div>
                  <label className="block text-xs text-[var(--muted)]">Side</label>
                  <select
                    value={leg.transaction_type}
                    onChange={(e) => updateLeg(idx, "transaction_type", e.target.value)}
                    className={`w-full rounded border border-[var(--card-border)] px-2 py-1.5 text-sm ${
                      leg.transaction_type === "BUY" ? "bg-green-900/20" : "bg-red-900/20"
                    }`}
                  >
                    <option value="BUY">BUY</option>
                    <option value="SELL">SELL</option>
                  </select>
                </div>
                <div>
                  <label className="block text-xs text-[var(--muted)]">Qty</label>
                  <input
                    value={leg.quantity}
                    onChange={(e) => updateLeg(idx, "quantity", e.target.value)}
                    className="w-full rounded border border-[var(--card-border)] bg-[var(--background)] px-2 py-1.5 text-sm"
                  />
                </div>
                <div>
                  <label className="block text-xs text-[var(--muted)]">Premium</label>
                  <input
                    value={leg.price}
                    onChange={(e) => updateLeg(idx, "price", e.target.value)}
                    className="w-full rounded border border-[var(--card-border)] bg-[var(--background)] px-2 py-1.5 text-sm"
                    placeholder="0"
                  />
                </div>
                <div>
                  <label className="block text-xs text-[var(--muted)]">Symbol</label>
                  <input
                    value={leg.tradingsymbol}
                    onChange={(e) => updateLeg(idx, "tradingsymbol", e.target.value)}
                    className="w-full rounded border border-[var(--card-border)] bg-[var(--background)] px-2 py-1.5 text-sm"
                    placeholder="NIFTY2504..."
                  />
                </div>
                <button
                  onClick={() => removeLeg(idx)}
                  className="text-red-400 hover:text-red-500 text-sm self-end pb-1"
                >
                  Remove
                </button>
              </div>
            ))}
          </div>

          {/* Payoff Chart */}
          {payoff.points.length > 0 && (
            <div className="rounded-lg border border-[var(--card-border)] bg-[var(--card)] p-4">
              <div className="flex items-center justify-between mb-3">
                <p className="text-sm font-medium">Payoff at Expiry</p>
                <div className="flex gap-4 text-xs">
                  <span className="text-green-400">
                    Max Profit: {payoff.maxProfit !== null ? formatINR(payoff.maxProfit) : "Unlimited"}
                  </span>
                  <span className="text-red-400">
                    Max Loss: {payoff.maxLoss !== null ? formatINR(payoff.maxLoss) : "Unlimited"}
                  </span>
                  {payoff.breakevens.length > 0 && (
                    <span className="text-[var(--muted)]">
                      Breakeven: {payoff.breakevens.map((b) => b.toFixed(0)).join(", ")}
                    </span>
                  )}
                </div>
              </div>
              <ResponsiveContainer width="100%" height={300}>
                <LineChart data={payoff.points}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#333" />
                  <XAxis
                    dataKey="underlying_price"
                    tick={{ fontSize: 11, fill: "#737373" }}
                    tickFormatter={(v) => v.toFixed(0)}
                  />
                  <YAxis tick={{ fontSize: 11, fill: "#737373" }} tickFormatter={(v) => `${(v / 1000).toFixed(1)}k`} />
                  <Tooltip
                    contentStyle={{ backgroundColor: "#141414", border: "1px solid #262626" }}
                    formatter={(value: number) => [formatINR(value), "P&L"]}
                    labelFormatter={(label) => `Spot: ${parseFloat(label).toFixed(0)}`}
                  />
                  <ReferenceLine y={0} stroke="#555" />
                  <Line type="monotone" dataKey="pnl" stroke="#3b82f6" dot={false} strokeWidth={2} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          )}

          <button
            onClick={handleCreate}
            disabled={!name || legs.length === 0 || createMut.isPending}
            className="rounded-md bg-brand-600 px-6 py-2.5 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-50"
          >
            {createMut.isPending ? "Creating..." : "Save Strategy"}
          </button>
        </div>
      )}

      {/* Existing strategies */}
      {strategies && strategies.length > 0 && (
        <div className="space-y-3">
          <h2 className="text-lg font-medium">Saved Strategies</h2>
          {strategies.map((s: any) => (
            <div
              key={s.id}
              className="rounded-lg border border-[var(--card-border)] bg-[var(--card)] p-4"
            >
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="font-medium">{s.name}</h3>
                  <p className="text-sm text-[var(--muted)]">
                    {s.underlying} | {s.strategy_type} | {s.legs.length} legs |{" "}
                    <span
                      className={
                        s.status === "FILLED"
                          ? "text-green-400"
                          : s.status === "DRAFT"
                          ? "text-gray-400"
                          : "text-yellow-400"
                      }
                    >
                      {s.status}
                    </span>
                  </p>
                </div>
                {s.status === "DRAFT" && (
                  <div className="flex gap-2 items-center">
                    <select
                      onChange={(e) => {
                        const aid = e.target.value;
                        if (aid && !selectedAccounts.includes(aid)) {
                          setSelectedAccounts((prev) => [...prev, aid]);
                        }
                      }}
                      className="rounded-md border border-[var(--card-border)] bg-[var(--background)] px-2 py-1.5 text-sm"
                    >
                      <option value="">Add account...</option>
                      {loggedIn.map((a) => (
                        <option key={a.id} value={a.id}>{a.name}</option>
                      ))}
                    </select>
                    <input
                      type="number"
                      min={1}
                      value={uniformLots}
                      onChange={(e) => setUniformLots(e.target.value)}
                      className="w-16 rounded-md border border-[var(--card-border)] bg-[var(--background)] px-2 py-1.5 text-sm"
                      placeholder="Lots"
                    />
                    <button
                      onClick={() =>
                        executeMut.mutate({
                          id: s.id,
                          body: {
                            account_ids: selectedAccounts.length ? selectedAccounts : ["all"],
                            mode: "uniform",
                            uniform_lots: parseInt(uniformLots),
                          },
                        })
                      }
                      disabled={executeMut.isPending}
                      className="rounded-md bg-brand-600 px-3 py-1.5 text-sm text-white hover:bg-brand-700 disabled:opacity-50"
                    >
                      Execute
                    </button>
                  </div>
                )}
              </div>
              <div className="mt-2 flex flex-wrap gap-2">
                {s.legs.map((leg: any) => (
                  <span
                    key={leg.id}
                    className={`rounded px-2 py-1 text-xs ${
                      leg.transaction_type === "BUY"
                        ? "bg-green-500/10 text-green-400"
                        : "bg-red-500/10 text-red-400"
                    }`}
                  >
                    {leg.transaction_type} {leg.instrument_type} {leg.strike ? parseFloat(leg.strike).toFixed(0) : ""} x{leg.quantity}
                  </span>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
