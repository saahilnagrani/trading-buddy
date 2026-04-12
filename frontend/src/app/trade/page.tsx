"use client";

import { useState, useCallback, useEffect, useRef } from "react";
import { useAccounts } from "@/lib/hooks/useAccounts";
import { usePlaceOrders } from "@/lib/hooks/useOrders";
import { searchInstruments } from "@/lib/api";
import { AccountStatusBadge } from "@/components/accounts/AccountStatusBadge";
import type {
  InstrumentResult,
  PlaceOrderRequest,
  PlaceOrderResponse,
  Account,
} from "@/lib/types";

type Step = "instrument" | "accounts" | "quantity" | "review";

function formatInstrumentDisplay(r: InstrumentResult) {
  // Parse tradingsymbol to extract underlying, expiry, strike, option type
  // e.g., "NIFTY2541725000CE" -> { name: "NIFTY", date: "17 APR", strike: "25000", optType: "CE" }
  const ts = r.tradingsymbol;
  const name = r.name || ts;

  if (!r.expiry) {
    // Equity instrument
    return { display: name || ts, sub: ts !== name ? ts : "", tag: null };
  }

  // Parse expiry date
  const expDate = new Date(r.expiry);
  const day = expDate.getUTCDate();
  const months = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"];
  const month = months[expDate.getUTCMonth()];

  // Determine if weekly or monthly
  // Monthly expiry is typically last Thursday of the month
  const lastDay = new Date(expDate.getUTCFullYear(), expDate.getUTCMonth() + 1, 0).getUTCDate();
  const isMonthly = day > lastDay - 7;
  const tag = isMonthly ? "MONTHLY" : "WEEKLY";

  // Extract option type from instrument_type
  const isOption = r.instrument_type?.includes("OPT");
  const isFuture = r.instrument_type?.includes("FUT");

  // Build display string
  let underlying = name;
  let suffix = "";
  if (isOption && r.strike) {
    suffix = `${r.strike} ${ts.endsWith("CE") ? "CE" : ts.endsWith("PE") ? "PE" : ""}`;
  } else if (isFuture) {
    suffix = "FUT";
  }

  // Add ordinal suffix to day
  const ordinal = (n: number) => {
    const s = ["th", "st", "nd", "rd"];
    const v = n % 100;
    return n + (s[(v - 20) % 10] || s[v] || s[0]);
  };

  const dateStr = `${ordinal(day)} ${month}`;
  const display = suffix ? `${underlying} ${suffix}` : underlying || ts;
  const sub = r.expiry ? `${day} ${month} ${tag}` : "";

  return { display, sub, tag, dateStr };
}

export default function TradePage() {
  const { data: accounts } = useAccounts();
  const placeOrdersMut = usePlaceOrders();

  // Form state
  const [step, setStep] = useState<Step>("instrument");
  const [instrument, setInstrument] = useState<InstrumentResult | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<InstrumentResult[]>([]);
  const [searching, setSearching] = useState(false);
  const [selectedAccounts, setSelectedAccounts] = useState<string[]>([]);
  const [txnType, setTxnType] = useState<"BUY" | "SELL">("BUY");
  const [orderType, setOrderType] = useState<"MARKET" | "LIMIT">("LIMIT");
  const [product, setProduct] = useState<"NRML" | "MIS" | "CNC">("NRML");
  const [price, setPrice] = useState("");
  const [mode, setMode] = useState<"uniform" | "custom">("uniform");
  const [uniformQty, setUniformQty] = useState("");
  const [customAllocs, setCustomAllocs] = useState<Record<string, string>>({});
  const [orderResult, setOrderResult] = useState<PlaceOrderResponse | null>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout>>();

  // Debounced instrument search
  useEffect(() => {
    if (searchQuery.length < 2) {
      setSearchResults([]);
      return;
    }
    clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(async () => {
      setSearching(true);
      try {
        const results = await searchInstruments(searchQuery);
        setSearchResults(results);
      } catch {
        setSearchResults([]);
      }
      setSearching(false);
    }, 300);
  }, [searchQuery]);

  const loggedInAccounts = accounts?.filter(
    (a) => a.token_status.is_logged_in
  ) ?? [];

  function toggleAccount(id: string) {
    setSelectedAccounts((prev) =>
      prev.includes(id) ? prev.filter((a) => a !== id) : [...prev, id]
    );
  }

  function toggleAll() {
    if (selectedAccounts.length === loggedInAccounts.length) {
      setSelectedAccounts([]);
    } else {
      setSelectedAccounts(loggedInAccounts.map((a) => a.id));
    }
  }

  async function handlePlaceOrder() {
    if (!instrument) return;

    const req: PlaceOrderRequest = {
      account_ids: selectedAccounts,
      mode,
      order: {
        exchange: instrument.exchange,
        tradingsymbol: instrument.tradingsymbol,
        transaction_type: txnType,
        order_type: orderType,
        product,
        price: orderType === "LIMIT" ? parseFloat(price) : undefined,
      },
      uniform_quantity: mode === "uniform" ? parseInt(uniformQty) : undefined,
      custom_allocations:
        mode === "custom"
          ? Object.fromEntries(
              Object.entries(customAllocs).map(([k, v]) => [k, parseInt(v)])
            )
          : undefined,
    };

    try {
      const result = await placeOrdersMut.mutateAsync(req);
      setOrderResult(result);
      setStep("review");
    } catch (e: any) {
      alert(e.response?.data?.detail || "Order placement failed");
    }
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold">Place Trade</h1>

      {/* Step indicators */}
      <div className="flex gap-2 text-sm">
        {(["instrument", "accounts", "quantity", "review"] as Step[]).map(
          (s, i) => (
            <button
              key={s}
              onClick={() => {
                if (s === "review" && !orderResult) return;
                setStep(s);
              }}
              className={`rounded-full px-3 py-1 transition-colors ${
                step === s
                  ? "bg-brand-600 text-white"
                  : "bg-[var(--card)] text-[var(--muted)] hover:text-white"
              }`}
            >
              {i + 1}. {s.charAt(0).toUpperCase() + s.slice(1)}
            </button>
          )
        )}
      </div>

      {/* Step 1: Instrument Search */}
      {step === "instrument" && (
        <div className="space-y-4">
          <div>
            <label className="block text-sm text-[var(--muted)] mb-1">
              Search Instrument
            </label>
            <input
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full rounded-md border border-[var(--card-border)] bg-[var(--background)] px-3 py-2 text-sm"
              placeholder="e.g., NIFTY, RELIANCE, BANKNIFTY..."
            />
          </div>

          {searching && (
            <p className="text-sm text-[var(--muted)]">Searching...</p>
          )}

          {searchResults.length > 0 && (
            <div className="max-h-96 overflow-y-auto rounded-lg border border-[var(--card-border)] bg-[var(--card)]">
              {searchResults.map((r) => {
                const fmt = formatInstrumentDisplay(r);
                return (
                  <button
                    key={`${r.exchange}:${r.tradingsymbol}`}
                    onClick={() => {
                      setInstrument(r);
                      setSearchResults([]);
                      setSearchQuery(r.tradingsymbol);
                      setStep("accounts");
                    }}
                    className="w-full text-left px-4 py-3 hover:bg-white/5 border-b border-[var(--card-border)] last:border-0 flex items-center justify-between gap-3"
                  >
                    <span className="text-sm font-medium truncate">
                      {fmt.display}
                    </span>
                    <div className="flex items-center gap-2 shrink-0">
                      {fmt.sub && (
                        <span className="text-xs text-[var(--muted)]">
                          {fmt.sub}
                        </span>
                      )}
                      <span className="rounded bg-white/10 px-1.5 py-0.5 text-[11px] font-medium text-[var(--muted)]">
                        {r.exchange}
                      </span>
                    </div>
                  </button>
                );
              })}
            </div>
          )}

          {instrument && (
            <div className="rounded-lg border border-brand-600/30 bg-brand-600/5 p-3 text-sm">
              Selected:{" "}
              <span className="font-medium">
                {instrument.exchange}:{instrument.tradingsymbol}
              </span>
              {instrument.lot_size > 1 && (
                <span className="ml-2 text-[var(--muted)]">
                  Lot size: {instrument.lot_size}
                </span>
              )}
              <button
                onClick={() => setStep("accounts")}
                className="ml-4 rounded bg-brand-600 px-3 py-1 text-xs text-white hover:bg-brand-700"
              >
                Next
              </button>
            </div>
          )}
        </div>
      )}

      {/* Step 2: Account Selection */}
      {step === "accounts" && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <p className="text-sm text-[var(--muted)]">
              Select accounts to trade on
            </p>
            <button
              onClick={toggleAll}
              className="text-sm text-brand-500 hover:text-brand-600"
            >
              {selectedAccounts.length === loggedInAccounts.length
                ? "Deselect All"
                : "Select All"}
            </button>
          </div>

          <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-3">
            {(accounts ?? []).map((account) => {
              const loggedIn = account.token_status.is_logged_in;
              const selected = selectedAccounts.includes(account.id);
              return (
                <button
                  key={account.id}
                  disabled={!loggedIn}
                  onClick={() => toggleAccount(account.id)}
                  className={`flex items-center justify-between rounded-lg border p-3 text-left text-sm transition-colors ${
                    selected
                      ? "border-brand-600 bg-brand-600/10"
                      : loggedIn
                      ? "border-[var(--card-border)] bg-[var(--card)] hover:border-white/20"
                      : "border-[var(--card-border)] bg-[var(--card)] opacity-50 cursor-not-allowed"
                  }`}
                >
                  <div>
                    <p className="font-medium">{account.name}</p>
                    <p className="text-xs text-[var(--muted)]">
                      Max lots: {account.max_lots}
                    </p>
                  </div>
                  <AccountStatusBadge isLoggedIn={loggedIn} />
                </button>
              );
            })}
          </div>

          {selectedAccounts.length > 0 && (
            <button
              onClick={() => setStep("quantity")}
              className="rounded-md bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700"
            >
              Next ({selectedAccounts.length} selected)
            </button>
          )}
        </div>
      )}

      {/* Step 3: Order Details + Quantity */}
      {step === "quantity" && instrument && (
        <div className="space-y-4">
          <div className="rounded-lg border border-[var(--card-border)] bg-[var(--card)] p-4 text-sm">
            <span className="font-medium">
              {instrument.exchange}:{instrument.tradingsymbol}
            </span>
            <span className="ml-2 text-[var(--muted)]">
              {selectedAccounts.length} accounts
            </span>
          </div>

          {/* Order params */}
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
            <div>
              <label className="block text-sm text-[var(--muted)] mb-1">
                Side
              </label>
              <div className="flex gap-1">
                {(["BUY", "SELL"] as const).map((t) => (
                  <button
                    key={t}
                    onClick={() => setTxnType(t)}
                    className={`flex-1 rounded-md px-3 py-2 text-sm font-medium transition-colors ${
                      txnType === t
                        ? t === "BUY"
                          ? "bg-green-600 text-white"
                          : "bg-red-600 text-white"
                        : "bg-[var(--card)] text-[var(--muted)]"
                    }`}
                  >
                    {t}
                  </button>
                ))}
              </div>
            </div>
            <div>
              <label className="block text-sm text-[var(--muted)] mb-1">
                Type
              </label>
              <select
                value={orderType}
                onChange={(e) => setOrderType(e.target.value as any)}
                className="w-full rounded-md border border-[var(--card-border)] bg-[var(--background)] px-3 py-2 text-sm"
              >
                <option value="LIMIT">Limit</option>
                <option value="MARKET">Market</option>
                <option value="SL">SL</option>
                <option value="SL-M">SL-M</option>
              </select>
            </div>
            <div>
              <label className="block text-sm text-[var(--muted)] mb-1">
                Product
              </label>
              <select
                value={product}
                onChange={(e) => setProduct(e.target.value as any)}
                className="w-full rounded-md border border-[var(--card-border)] bg-[var(--background)] px-3 py-2 text-sm"
              >
                <option value="NRML">NRML</option>
                <option value="MIS">MIS</option>
                <option value="CNC">CNC</option>
              </select>
            </div>
            {orderType === "LIMIT" && (
              <div>
                <label className="block text-sm text-[var(--muted)] mb-1">
                  Price
                </label>
                <input
                  type="number"
                  step={instrument.tick_size}
                  value={price}
                  onChange={(e) => setPrice(e.target.value)}
                  className="w-full rounded-md border border-[var(--card-border)] bg-[var(--background)] px-3 py-2 text-sm"
                />
              </div>
            )}
          </div>

          {/* Mode toggle */}
          <div>
            <label className="block text-sm text-[var(--muted)] mb-1">
              Allocation Mode
            </label>
            <div className="flex gap-1">
              {(["uniform", "custom"] as const).map((m) => (
                <button
                  key={m}
                  onClick={() => setMode(m)}
                  className={`rounded-md px-4 py-2 text-sm transition-colors ${
                    mode === m
                      ? "bg-brand-600 text-white"
                      : "bg-[var(--card)] text-[var(--muted)]"
                  }`}
                >
                  {m === "uniform" ? "Same on All" : "Custom per Account"}
                </button>
              ))}
            </div>
          </div>

          {/* Quantity input */}
          {mode === "uniform" ? (
            <div>
              <label className="block text-sm text-[var(--muted)] mb-1">
                Quantity (per account)
              </label>
              <input
                type="number"
                min={1}
                step={instrument.lot_size || 1}
                value={uniformQty}
                onChange={(e) => setUniformQty(e.target.value)}
                placeholder={`Lot size: ${instrument.lot_size}`}
                className="w-full max-w-xs rounded-md border border-[var(--card-border)] bg-[var(--background)] px-3 py-2 text-sm"
              />
            </div>
          ) : (
            <div className="space-y-2">
              <p className="text-sm text-[var(--muted)]">
                Set quantity per account:
              </p>
              {selectedAccounts.map((aid) => {
                const account = accounts?.find((a) => a.id === aid);
                return (
                  <div
                    key={aid}
                    className="flex items-center gap-3 rounded-lg border border-[var(--card-border)] bg-[var(--card)] p-3"
                  >
                    <span className="flex-1 text-sm font-medium">
                      {account?.name}
                    </span>
                    <span className="text-xs text-[var(--muted)]">
                      Max: {account?.max_lots} lots
                    </span>
                    <input
                      type="number"
                      min={1}
                      step={instrument.lot_size || 1}
                      value={customAllocs[aid] || ""}
                      onChange={(e) =>
                        setCustomAllocs((prev) => ({
                          ...prev,
                          [aid]: e.target.value,
                        }))
                      }
                      placeholder="Qty"
                      className="w-24 rounded-md border border-[var(--card-border)] bg-[var(--background)] px-3 py-1.5 text-sm"
                    />
                  </div>
                );
              })}
            </div>
          )}

          <button
            onClick={handlePlaceOrder}
            disabled={placeOrdersMut.isPending}
            className="rounded-md bg-brand-600 px-6 py-2.5 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-50"
          >
            {placeOrdersMut.isPending ? "Placing..." : "Place Order"}
          </button>
        </div>
      )}

      {/* Step 4: Results */}
      {step === "review" && orderResult && (
        <div className="space-y-4">
          <div className="flex gap-4 text-sm">
            <span className="text-green-400">
              Placed: {orderResult.placed}
            </span>
            <span className="text-red-400">Failed: {orderResult.failed}</span>
          </div>

          <div className="overflow-x-auto rounded-lg border border-[var(--card-border)]">
            <table className="w-full text-sm">
              <thead className="bg-[var(--card)] text-left text-[var(--muted)]">
                <tr>
                  <th className="px-4 py-3 font-medium">Account</th>
                  <th className="px-4 py-3 font-medium">Status</th>
                  <th className="px-4 py-3 font-medium">Order ID</th>
                  <th className="px-4 py-3 font-medium">Message</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[var(--card-border)]">
                {orderResult.results.map((r, i) => (
                  <tr key={i} className="bg-[var(--card)]">
                    <td className="px-4 py-3 font-medium">
                      {r.account_name}
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className={`rounded-full px-2 py-0.5 text-xs ${
                          r.status === "PLACED"
                            ? "bg-green-500/10 text-green-400"
                            : "bg-red-500/10 text-red-400"
                        }`}
                      >
                        {r.status}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-[var(--muted)]">
                      {r.kite_order_id || "-"}
                    </td>
                    <td className="px-4 py-3 text-[var(--muted)]">
                      {r.message || "-"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <button
            onClick={() => {
              setOrderResult(null);
              setStep("instrument");
              setInstrument(null);
              setSearchQuery("");
              setSelectedAccounts([]);
              setUniformQty("");
              setCustomAllocs({});
              setPrice("");
            }}
            className="rounded-md border border-[var(--card-border)] px-4 py-2 text-sm text-[var(--muted)] hover:text-white"
          >
            Place Another Trade
          </button>
        </div>
      )}
    </div>
  );
}
