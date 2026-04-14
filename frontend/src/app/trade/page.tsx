"use client";

import { useState, useCallback, useEffect, useRef } from "react";
import { useAccounts } from "@/lib/hooks/useAccounts";
import { usePlaceOrders } from "@/lib/hooks/useOrders";
import { searchInstruments, fetchQuote } from "@/lib/api";
import { AccountStatusBadge } from "@/components/accounts/AccountStatusBadge";
import { Search, Users, Sliders, CheckCircle2, ChevronRight } from "lucide-react";
import type {
  InstrumentResult,
  PlaceOrderRequest,
  PlaceOrderResponse,
  Account,
  QuoteData,
} from "@/lib/types";

type Step = "instrument" | "accounts" | "quantity" | "review";

const STEPS: { key: Step; label: string; Icon: typeof Search }[] = [
  { key: "instrument", label: "Select instrument", Icon: Search },
  { key: "accounts", label: "Select accounts", Icon: Users },
  { key: "quantity", label: "Set quantity & type", Icon: Sliders },
  { key: "review", label: "Review", Icon: CheckCircle2 },
];

// Valid products per exchange per Kite API docs
// NSE/BSE equity: CNC (delivery), MIS (intraday)
// NFO/BFO derivatives, MCX commodity, CDS/BCD currency: NRML (carry-forward), MIS (intraday)
function getValidProducts(exchange: string): ("NRML" | "MIS" | "CNC")[] {
  if (exchange === "NSE" || exchange === "BSE") return ["CNC", "MIS"];
  if (exchange === "NFO" || exchange === "BFO" || exchange === "MCX" || exchange === "CDS" || exchange === "BCD")
    return ["NRML", "MIS"];
  return ["NRML", "MIS", "CNC"];
}

// Iceberg is only supported on NSE/BSE equity and NFO/BFO F&O in Kite
function isIcebergSupported(exchange: string): boolean {
  return ["NSE", "BSE", "NFO", "BFO"].includes(exchange);
}

function formatInstrumentDisplay(r: InstrumentResult) {
  const ts = r.tradingsymbol;
  const name = r.name || "";

  if (!r.expiry) {
    return { display: name || ts, sub: name && name !== ts ? ts : "", tag: null };
  }

  const expDate = new Date(r.expiry);
  const day = expDate.getUTCDate();
  const months = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"];
  const month = months[expDate.getUTCMonth()];

  const lastDay = new Date(expDate.getUTCFullYear(), expDate.getUTCMonth() + 1, 0).getUTCDate();
  const isMonthly = day > lastDay - 7;
  const tag = isMonthly ? "MONTHLY" : "WEEKLY";
  const tagShort = isMonthly ? "" : " w";

  const it = r.instrument_type?.toUpperCase() || "";
  const isOption = it.includes("OPT") || it === "CE" || it === "PE";
  const isFuture = it.includes("FUT");

  const ordinal = (n: number) => {
    const s = ["th", "st", "nd", "rd"];
    const v = n % 100;
    return n + (s[(v - 20) % 10] || s[v] || s[0]);
  };

  const underlying = name || ts.replace(/\d.*/,"");

  if (isOption && r.strike) {
    const optType = it === "CE" || ts.endsWith("CE") ? "CE" : it === "PE" || ts.endsWith("PE") ? "PE" : "";
    const display = `${underlying} ${ordinal(day)}${tagShort} ${month} ${r.strike} ${optType}`;
    const sub = `${day} ${month} ${tag}`;
    return { display, sub, tag };
  }

  if (isFuture) {
    const display = `${underlying} ${ordinal(day)}${tagShort} ${month} FUT`;
    const sub = `${day} ${month} ${tag}`;
    return { display, sub, tag };
  }

  const display = underlying || ts;
  const sub = `${day} ${month} ${tag}`;
  return { display, sub, tag };
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
  const [orderType, setOrderType] = useState<"MARKET" | "LIMIT" | "SL" | "SL-M">("LIMIT");
  const [product, setProduct] = useState<"NRML" | "MIS" | "CNC">("NRML");
  const [variety, setVariety] = useState<"regular" | "amo" | "iceberg">("regular");
  const [icebergLegs, setIcebergLegs] = useState("");
  const [icebergQty, setIcebergQty] = useState("");
  const [price, setPrice] = useState("");
  const [triggerPrice, setTriggerPrice] = useState("");
  const [mode, setMode] = useState<"uniform" | "custom">("uniform");
  const [uniformQty, setUniformQty] = useState("");
  const [customAllocs, setCustomAllocs] = useState<Record<string, string>>({});
  const [orderResult, setOrderResult] = useState<PlaceOrderResponse | null>(null);
  const [quote, setQuote] = useState<QuoteData | null>(null);
  const [quoteError, setQuoteError] = useState<string | null>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout>>();
  const abortRef = useRef<AbortController>();

  // Debounced instrument search with abort for stale requests
  useEffect(() => {
    if (searchQuery.length < 2) {
      setSearchResults([]);
      return;
    }
    clearTimeout(debounceRef.current);
    abortRef.current?.abort();

    debounceRef.current = setTimeout(async () => {
      const controller = new AbortController();
      abortRef.current = controller;
      setSearching(true);
      try {
        const results = await searchInstruments(searchQuery);
        if (!controller.signal.aborted) {
          setSearchResults(results);
        }
      } catch {
        if (!controller.signal.aborted) {
          setSearchResults([]);
        }
      }
      if (!controller.signal.aborted) {
        setSearching(false);
      }
    }, 500);
  }, [searchQuery]);

  // Auto-correct product + variety when the instrument's exchange changes
  useEffect(() => {
    if (!instrument) return;
    const valid = getValidProducts(instrument.exchange);
    if (!valid.includes(product)) {
      setProduct(valid[0]);
    }
    if (variety === "iceberg" && !isIcebergSupported(instrument.exchange)) {
      setVariety("regular");
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [instrument]);

  // Poll quote data every 3s when an instrument is selected
  useEffect(() => {
    if (!instrument) {
      setQuote(null);
      setQuoteError(null);
      return;
    }
    let cancelled = false;
    const symbol = `${instrument.exchange}:${instrument.tradingsymbol}`;

    async function poll() {
      try {
        const data = await fetchQuote(symbol);
        if (!cancelled) {
          setQuote(data);
          setQuoteError(null);
        }
      } catch (e: any) {
        if (!cancelled) {
          const detail =
            e?.response?.data?.detail ||
            e?.message ||
            "Unable to fetch quote";
          setQuoteError(
            typeof detail === "string" ? detail : "Unable to fetch quote"
          );
        }
      }
    }

    poll();
    const id = setInterval(poll, 3000);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, [instrument]);

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

  // Compute effective per-account quantity for the uniform mode, capped at each account's max_lots.
  // Returns null if no capping is happening (i.e., every selected account can take the full uniform qty).
  function getUniformCapPreview(): {
    capped: { accountId: string; name: string; requested: number; allowed: number }[];
    effectiveAllocations: Record<string, number>;
  } | null {
    if (!instrument || mode !== "uniform") return null;
    const lotSize = instrument.lot_size || 1;
    const reqQty = parseInt(uniformQty);
    if (!reqQty || reqQty <= 0) return null;
    const effective: Record<string, number> = {};
    const capped: { accountId: string; name: string; requested: number; allowed: number }[] = [];
    for (const aid of selectedAccounts) {
      const acc = accounts?.find((a) => a.id === aid);
      if (!acc) continue;
      const maxQty = acc.max_lots * lotSize;
      const alloc = Math.min(reqQty, maxQty);
      effective[aid] = alloc;
      if (alloc < reqQty) {
        capped.push({
          accountId: aid,
          name: acc.name,
          requested: reqQty,
          allowed: alloc,
        });
      }
    }
    return { capped, effectiveAllocations: effective };
  }

  // Can the user advance from the current step?
  function canGoNext(): boolean {
    if (step === "instrument") return !!instrument;
    if (step === "accounts") return selectedAccounts.length > 0;
    if (step === "quantity") {
      if (mode === "uniform") return !!uniformQty && parseInt(uniformQty) > 0;
      return Object.values(customAllocs).some((v) => v && parseInt(v) > 0);
    }
    return false;
  }

  function handleBack() {
    const idx = STEPS.findIndex((s) => s.key === step);
    if (idx > 0) setStep(STEPS[idx - 1].key);
  }

  async function handleNext() {
    if (!canGoNext()) return;
    if (step === "instrument") setStep("accounts");
    else if (step === "accounts") setStep("quantity");
    else if (step === "quantity") await handlePlaceOrder();
  }

  async function handlePlaceOrder() {
    if (!instrument) return;

    // In uniform mode, if any selected account's max_lots would be exceeded,
    // automatically switch to custom_allocations with per-account caps so the
    // bigger accounts get the full qty and the smaller ones get their max.
    const cap = getUniformCapPreview();
    const mustCap = cap && cap.capped.length > 0;

    const req: PlaceOrderRequest = {
      account_ids: selectedAccounts,
      mode: mustCap ? "custom" : mode,
      order: {
        exchange: instrument.exchange,
        tradingsymbol: instrument.tradingsymbol,
        transaction_type: txnType,
        order_type: orderType,
        product,
        variety,
        price:
          orderType === "LIMIT" || orderType === "SL"
            ? parseFloat(price)
            : undefined,
        trigger_price:
          orderType === "SL" || orderType === "SL-M"
            ? parseFloat(triggerPrice)
            : undefined,
        iceberg_legs:
          variety === "iceberg" && icebergLegs
            ? parseInt(icebergLegs)
            : undefined,
        iceberg_quantity:
          variety === "iceberg" && icebergQty
            ? parseInt(icebergQty)
            : undefined,
      },
      uniform_quantity:
        mode === "uniform" && !mustCap ? parseInt(uniformQty) : undefined,
      custom_allocations: mustCap
        ? cap!.effectiveAllocations
        : mode === "custom"
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

      {/* Step breadcrumb + BACK/NEXT */}
      <div className="flex flex-col gap-3 rounded-lg border border-[var(--card-border)] bg-[var(--card)] px-4 py-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-1 overflow-x-auto text-sm -mx-1 px-1">
          {STEPS.map((s, i) => {
            const active = step === s.key;
            const clickable = s.key !== "review" || !!orderResult;
            const Icon = s.Icon;
            return (
              <div key={s.key} className="flex items-center gap-1 whitespace-nowrap">
                <button
                  onClick={() => clickable && setStep(s.key)}
                  disabled={!clickable}
                  className={`flex items-center gap-1.5 rounded-md px-2 py-1 transition-colors ${
                    active
                      ? "text-brand-500 font-medium"
                      : clickable
                      ? "text-[var(--muted)] hover:text-white"
                      : "text-[var(--muted)]/50 cursor-not-allowed"
                  }`}
                >
                  <Icon size={16} />
                  <span className={active ? "" : "hidden sm:inline"}>{s.label}</span>
                </button>
                {i < STEPS.length - 1 && (
                  <ChevronRight size={14} className="text-[var(--muted)]/50 shrink-0" />
                )}
              </div>
            );
          })}
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <button
            onClick={handleBack}
            disabled={step === "instrument" || step === "review"}
            className="rounded-md border border-[var(--card-border)] px-4 py-1.5 text-sm font-medium text-[var(--muted)] hover:text-white hover:border-white/20 transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
          >
            BACK
          </button>
          {step !== "review" && (
            <button
              onClick={handleNext}
              disabled={!canGoNext() || placeOrdersMut.isPending}
              className="rounded-md bg-brand-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-brand-700 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
            >
              {step === "quantity"
                ? placeOrdersMut.isPending
                  ? "PLACING..."
                  : "PLACE ORDER"
                : "NEXT"}
            </button>
          )}
        </div>
      </div>

      {/* Quote Panel (persistent across steps 2-4) */}
      {instrument && step !== "instrument" && (
        <div className="rounded-lg border border-[var(--card-border)] bg-[var(--card)] p-4">
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-2 flex-wrap">
                <span className="text-base sm:text-lg font-semibold truncate">
                  {formatInstrumentDisplay(instrument).display}
                </span>
                <span className="rounded bg-white/10 px-1.5 py-0.5 text-[11px] font-medium text-[var(--muted)]">
                  {instrument.exchange}
                </span>
                {instrument.lot_size > 1 && (
                  <span className="text-xs text-[var(--muted)]">
                    Lot: {instrument.lot_size}
                  </span>
                )}
              </div>
              {quote ? (
                <div className="mt-2 space-y-2">
                  {/* LTP + Change */}
                  <div className="flex items-baseline gap-3">
                    <span className="text-2xl font-bold tabular-nums">
                      {quote.last_price.toLocaleString("en-IN", {
                        minimumFractionDigits: 2,
                        maximumFractionDigits: 2,
                      })}
                    </span>
                    <span
                      className={`text-sm font-medium ${
                        quote.change >= 0 ? "text-green-400" : "text-red-400"
                      }`}
                    >
                      {quote.change >= 0 ? "+" : ""}
                      {quote.change.toFixed(2)} ({quote.change_percent.toFixed(2)}
                      %)
                    </span>
                  </div>

                  {/* OHLC + Bid/Ask + Vol/OI */}
                  <div className="flex flex-wrap gap-x-6 gap-y-1 text-xs">
                    <div>
                      <span className="text-[var(--muted)]">O </span>
                      <span className="tabular-nums">{quote.open.toLocaleString("en-IN")}</span>
                    </div>
                    <div>
                      <span className="text-[var(--muted)]">H </span>
                      <span className="tabular-nums text-green-400">{quote.high.toLocaleString("en-IN")}</span>
                    </div>
                    <div>
                      <span className="text-[var(--muted)]">L </span>
                      <span className="tabular-nums text-red-400">{quote.low.toLocaleString("en-IN")}</span>
                    </div>
                    <div>
                      <span className="text-[var(--muted)]">C </span>
                      <span className="tabular-nums">{quote.close.toLocaleString("en-IN")}</span>
                    </div>
                    <div className="border-l border-[var(--card-border)] pl-4">
                      <span className="text-[var(--muted)]">Bid </span>
                      <span className="tabular-nums">{quote.bid.toLocaleString("en-IN")}</span>
                      <span className="text-[var(--muted)]"> x{quote.bid_qty}</span>
                    </div>
                    <div>
                      <span className="text-[var(--muted)]">Ask </span>
                      <span className="tabular-nums">{quote.ask.toLocaleString("en-IN")}</span>
                      <span className="text-[var(--muted)]"> x{quote.ask_qty}</span>
                    </div>
                    <div className="border-l border-[var(--card-border)] pl-4">
                      <span className="text-[var(--muted)]">Vol </span>
                      <span className="tabular-nums">
                        {quote.volume >= 100000
                          ? (quote.volume / 100000).toFixed(2) + "L"
                          : quote.volume.toLocaleString("en-IN")}
                      </span>
                    </div>
                    {quote.oi > 0 && (
                      <div>
                        <span className="text-[var(--muted)]">OI </span>
                        <span className="tabular-nums">
                          {quote.oi >= 100000
                            ? (quote.oi / 100000).toFixed(2) + "L"
                            : quote.oi.toLocaleString("en-IN")}
                        </span>
                      </div>
                    )}
                  </div>
                </div>
              ) : quoteError ? (
                <p className="mt-2 text-xs text-yellow-400">
                  Quote unavailable: {quoteError}
                </p>
              ) : (
                <p className="mt-2 text-sm text-[var(--muted)]">
                  Loading quote...
                </p>
              )}
            </div>
            <button
              onClick={() => {
                setStep("instrument");
                setInstrument(null);
                setSearchQuery("");
                setQuote(null);
                setQuoteError(null);
              }}
              className="shrink-0 text-xs text-[var(--muted)] hover:text-white"
            >
              Change
            </button>
          </div>
        </div>
      )}

      {/* Step 1: Instrument Search */}
      {step === "instrument" && (
        <div className="space-y-4 max-w-xl">
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
            <p className="text-xs text-[var(--muted)]">
              {selectedAccounts.length} account{selectedAccounts.length === 1 ? "" : "s"} selected
            </p>
          )}
        </div>
      )}

      {/* Step 3: Order Details + Quantity */}
      {step === "quantity" && instrument && (
        <div className="space-y-4">
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
                {getValidProducts(instrument.exchange).map((p) => (
                  <option key={p} value={p}>
                    {p}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm text-[var(--muted)] mb-1">
                Variety
              </label>
              <select
                value={variety}
                onChange={(e) => setVariety(e.target.value as any)}
                className="w-full rounded-md border border-[var(--card-border)] bg-[var(--background)] px-3 py-2 text-sm"
              >
                <option value="regular">Regular</option>
                <option value="amo">AMO (After Market)</option>
                {isIcebergSupported(instrument.exchange) && (
                  <option value="iceberg">Iceberg</option>
                )}
              </select>
            </div>
          </div>

          {/* Price inputs — separate row since they're conditional */}
          {(orderType === "LIMIT" || orderType === "SL" || orderType === "SL-M") && (
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 max-w-md">
              {(orderType === "LIMIT" || orderType === "SL") && (
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
              {(orderType === "SL" || orderType === "SL-M") && (
                <div>
                  <label className="block text-sm text-[var(--muted)] mb-1">
                    Trigger Price
                  </label>
                  <input
                    type="number"
                    step={instrument.tick_size}
                    value={triggerPrice}
                    onChange={(e) => setTriggerPrice(e.target.value)}
                    className="w-full rounded-md border border-[var(--card-border)] bg-[var(--background)] px-3 py-2 text-sm"
                  />
                </div>
              )}
            </div>
          )}

          {/* Iceberg params */}
          {variety === "iceberg" && (
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 max-w-md">
              <div>
                <label className="block text-sm text-[var(--muted)] mb-1">
                  Iceberg Legs (2–10)
                </label>
                <input
                  type="number"
                  min={2}
                  max={10}
                  step={1}
                  value={icebergLegs}
                  onChange={(e) => setIcebergLegs(e.target.value)}
                  placeholder="e.g., 5"
                  className="w-full rounded-md border border-[var(--card-border)] bg-[var(--background)] px-3 py-2 text-sm"
                />
              </div>
              <div>
                <label className="block text-sm text-[var(--muted)] mb-1">
                  Disclosed Qty per Leg
                </label>
                <input
                  type="number"
                  min={1}
                  step={instrument.lot_size || 1}
                  value={icebergQty}
                  onChange={(e) => setIcebergQty(e.target.value)}
                  placeholder={`Multiple of ${instrument.lot_size}`}
                  className="w-full rounded-md border border-[var(--card-border)] bg-[var(--background)] px-3 py-2 text-sm"
                />
              </div>
            </div>
          )}

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
          {(() => {
            const lotSize = instrument.lot_size || 1;
            const quickLots = [1, 2, 3, 5, 10];
            return mode === "uniform" ? (
              <div>
                <div className="flex items-baseline justify-between max-w-xs mb-1">
                  <label className="text-sm text-[var(--muted)]">
                    Quantity (per account)
                  </label>
                  <span className="text-xs text-[var(--muted)]">
                    Lot size: {lotSize}
                    {uniformQty && parseInt(uniformQty) > 0 && lotSize > 0 && (
                      <>
                        {" · "}
                        {(parseInt(uniformQty) / lotSize).toFixed(
                          parseInt(uniformQty) % lotSize === 0 ? 0 : 2
                        )}{" "}
                        lot{parseInt(uniformQty) === lotSize ? "" : "s"}
                      </>
                    )}
                  </span>
                </div>
                <input
                  type="number"
                  min={1}
                  step={lotSize}
                  value={uniformQty}
                  onChange={(e) => setUniformQty(e.target.value)}
                  placeholder={`e.g., ${lotSize}`}
                  className="w-full max-w-xs rounded-md border border-[var(--card-border)] bg-[var(--background)] px-3 py-2 text-sm"
                />
                <div className="mt-2 flex items-center gap-2 flex-wrap">
                  <span className="text-xs text-[var(--muted)]">Quick:</span>
                  {quickLots.map((n) => {
                    const qty = lotSize * n;
                    const active = parseInt(uniformQty) === qty;
                    return (
                      <button
                        key={n}
                        onClick={() => setUniformQty(String(qty))}
                        className={`rounded-md px-2.5 py-1 text-xs font-medium transition-colors ${
                          active
                            ? "bg-brand-600 text-white"
                            : "border border-[var(--card-border)] text-[var(--muted)] hover:text-white hover:border-white/20"
                        }`}
                      >
                        {n}L
                      </button>
                    );
                  })}
                </div>
                {(() => {
                  const cap = getUniformCapPreview();
                  if (!cap || cap.capped.length === 0) return null;
                  return (
                    <div className="mt-3 rounded-lg border border-yellow-500/30 bg-yellow-500/5 p-3 text-xs">
                      <p className="font-medium text-yellow-400 mb-1">
                        Some accounts will receive a smaller quantity (max lots limit):
                      </p>
                      <ul className="space-y-0.5 text-[var(--muted)]">
                        {cap.capped.map((c) => (
                          <li key={c.accountId}>
                            <span className="font-medium text-white">{c.name}</span>
                            : requested {c.requested} → sending {c.allowed}
                            {" "}({(c.allowed / lotSize).toFixed(
                              c.allowed % lotSize === 0 ? 0 : 2
                            )} lot
                            {c.allowed === lotSize ? "" : "s"})
                          </li>
                        ))}
                      </ul>
                    </div>
                  );
                })()}
              </div>
            ) : (
              <div className="space-y-2">
                <p className="text-sm text-[var(--muted)]">
                  Set quantity per account (lot size: {lotSize}):
                </p>
                {selectedAccounts.map((aid) => {
                  const account = accounts?.find((a) => a.id === aid);
                  const current = customAllocs[aid] || "";
                  const currentQty = parseInt(current) || 0;
                  const maxLots = account?.max_lots || 999;
                  return (
                    <div
                      key={aid}
                      className="rounded-lg border border-[var(--card-border)] bg-[var(--card)] p-3"
                    >
                      <div className="flex items-center gap-3">
                        <span className="flex-1 text-sm font-medium">
                          {account?.name}
                        </span>
                        <span className="text-xs text-[var(--muted)]">
                          Max: {maxLots} lots
                        </span>
                        <input
                          type="number"
                          min={1}
                          step={lotSize}
                          value={current}
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
                      <div className="mt-2 flex items-center gap-2 flex-wrap">
                        <span className="text-[11px] text-[var(--muted)]">
                          {currentQty > 0 && lotSize > 0
                            ? `${(currentQty / lotSize).toFixed(
                                currentQty % lotSize === 0 ? 0 : 2
                              )} lot${currentQty === lotSize ? "" : "s"}`
                            : "Quick:"}
                        </span>
                        {quickLots
                          .filter((n) => n <= maxLots)
                          .map((n) => {
                            const qty = lotSize * n;
                            const active = currentQty === qty;
                            return (
                              <button
                                key={n}
                                onClick={() =>
                                  setCustomAllocs((prev) => ({
                                    ...prev,
                                    [aid]: String(qty),
                                  }))
                                }
                                className={`rounded-md px-2 py-0.5 text-[11px] font-medium transition-colors ${
                                  active
                                    ? "bg-brand-600 text-white"
                                    : "border border-[var(--card-border)] text-[var(--muted)] hover:text-white hover:border-white/20"
                                }`}
                              >
                                {n}L
                              </button>
                            );
                          })}
                        {maxLots < 999 && maxLots > 0 && !quickLots.includes(maxLots) && (
                          <button
                            onClick={() =>
                              setCustomAllocs((prev) => ({
                                ...prev,
                                [aid]: String(lotSize * maxLots),
                              }))
                            }
                            className={`rounded-md px-2 py-0.5 text-[11px] font-medium transition-colors ${
                              currentQty === lotSize * maxLots
                                ? "bg-brand-600 text-white"
                                : "border border-[var(--card-border)] text-[var(--muted)] hover:text-white hover:border-white/20"
                            }`}
                          >
                            Max ({maxLots}L)
                          </button>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            );
          })()}

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

          {/* Mobile cards */}
          <div className="space-y-2 lg:hidden">
            {orderResult.results.map((r, i) => (
              <div key={i} className="rounded-lg border border-[var(--card-border)] bg-[var(--card)] p-3">
                <div className="flex items-center justify-between gap-3">
                  <span className="font-medium truncate">{r.account_name}</span>
                  <span
                    className={`shrink-0 rounded-full px-2 py-0.5 text-xs ${
                      r.status === "PLACED"
                        ? "bg-green-500/10 text-green-400"
                        : "bg-red-500/10 text-red-400"
                    }`}
                  >
                    {r.status}
                  </span>
                </div>
                <div className="mt-1 text-xs text-[var(--muted)] space-y-0.5">
                  <p>Order ID: <span className="font-mono">{r.kite_order_id || "-"}</span></p>
                  {r.message && <p className="break-words">{r.message}</p>}
                </div>
              </div>
            ))}
          </div>
          {/* Desktop table */}
          <div className="hidden lg:block overflow-x-auto rounded-lg border border-[var(--card-border)]">
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
              setQuote(null);
              setQuoteError(null);
              setSelectedAccounts([]);
              setUniformQty("");
              setCustomAllocs({});
              setPrice("");
              setTriggerPrice("");
              setVariety("regular");
              setIcebergLegs("");
              setIcebergQty("");
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
