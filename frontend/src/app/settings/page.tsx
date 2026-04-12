"use client";

import { useState, useEffect } from "react";
import { useAccounts, useUpdateAccount } from "@/lib/hooks/useAccounts";
import type { Account } from "@/lib/types";
import axios from "axios";

const api = axios.create({ baseURL: "/api" });

export default function SettingsPage() {
  const { data: accounts } = useAccounts();
  const updateMut = useUpdateAccount();
  const [pushEnabled, setPushEnabled] = useState(false);
  const [pushSupported, setPushSupported] = useState(false);

  // Check push notification support
  useEffect(() => {
    setPushSupported("serviceWorker" in navigator && "PushManager" in window);

    if ("serviceWorker" in navigator) {
      navigator.serviceWorker.register("/sw.js").catch(() => {});
      navigator.serviceWorker.ready.then((reg) => {
        reg.pushManager.getSubscription().then((sub) => {
          setPushEnabled(!!sub);
        });
      });
    }
  }, []);

  async function togglePush() {
    if (!pushSupported) return;

    const reg = await navigator.serviceWorker.ready;

    if (pushEnabled) {
      const sub = await reg.pushManager.getSubscription();
      if (sub) {
        await sub.unsubscribe();
        await api.delete("/notifications/subscribe", {
          params: { endpoint: sub.endpoint },
        });
      }
      setPushEnabled(false);
    } else {
      const permission = await Notification.requestPermission();
      if (permission !== "granted") return;

      // Note: VAPID public key needs to be configured
      // For now, subscription will work once VAPID keys are set
      try {
        const sub = await reg.pushManager.subscribe({
          userVisibleOnly: true,
          applicationServerKey: process.env.NEXT_PUBLIC_VAPID_PUBLIC_KEY,
        });
        const json = sub.toJSON();
        await api.post("/notifications/subscribe", {
          endpoint: sub.endpoint,
          p256dh_key: json.keys?.p256dh ?? "",
          auth_key: json.keys?.auth ?? "",
          user_agent: navigator.userAgent,
        });
        setPushEnabled(true);
      } catch (e) {
        console.error("Push subscription failed:", e);
      }
    }
  }

  return (
    <div className="space-y-8">
      <h1 className="text-2xl font-semibold">Settings</h1>

      {/* Push Notifications */}
      <section className="space-y-3">
        <h2 className="text-lg font-medium">Notifications</h2>
        <div className="rounded-lg border border-[var(--card-border)] bg-[var(--card)] p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="font-medium text-sm">Push Notifications</p>
              <p className="text-xs text-[var(--muted)]">
                Get notified about order fills, margin alerts, and token expiry
              </p>
            </div>
            {pushSupported ? (
              <button
                onClick={togglePush}
                className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                  pushEnabled ? "bg-brand-600" : "bg-gray-600"
                }`}
              >
                <span
                  className={`inline-block h-4 w-4 rounded-full bg-white transition-transform ${
                    pushEnabled ? "translate-x-6" : "translate-x-1"
                  }`}
                />
              </button>
            ) : (
              <span className="text-xs text-[var(--muted)]">Not supported</span>
            )}
          </div>
        </div>
      </section>

      {/* Risk Controls per Account */}
      <section className="space-y-3">
        <h2 className="text-lg font-medium">Risk Controls</h2>
        <p className="text-sm text-[var(--muted)]">
          Set per-account limits. Orders exceeding these limits will be rejected.
        </p>

        {accounts?.map((account) => (
          <RiskControlCard
            key={account.id}
            account={account}
            onSave={(data) =>
              updateMut.mutate({ id: account.id, data })
            }
          />
        ))}
      </section>
    </div>
  );
}

function RiskControlCard({
  account,
  onSave,
}: {
  account: Account;
  onSave: (data: any) => void;
}) {
  const [maxLots, setMaxLots] = useState(String(account.max_lots));
  const [maxOrderValue, setMaxOrderValue] = useState(
    (account as any).max_order_value ? String((account as any).max_order_value) : ""
  );
  const [maxDailyOrders, setMaxDailyOrders] = useState(
    String((account as any).max_daily_orders ?? 50)
  );
  const [maxOpenPositions, setMaxOpenPositions] = useState(
    String((account as any).max_open_positions ?? 20)
  );
  const [dirty, setDirty] = useState(false);

  function handleSave() {
    onSave({
      max_lots: parseInt(maxLots) || 1,
      max_order_value: maxOrderValue ? parseFloat(maxOrderValue) : null,
      max_daily_orders: parseInt(maxDailyOrders) || 50,
      max_open_positions: parseInt(maxOpenPositions) || 20,
    });
    setDirty(false);
  }

  return (
    <div className="rounded-lg border border-[var(--card-border)] bg-[var(--card)] p-4 space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="font-medium">{account.name}</h3>
        {dirty && (
          <button
            onClick={handleSave}
            className="rounded-md bg-brand-600 px-3 py-1 text-xs text-white hover:bg-brand-700"
          >
            Save
          </button>
        )}
      </div>

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <div>
          <label className="block text-xs text-[var(--muted)] mb-1">Max Lots</label>
          <input
            type="number"
            min={1}
            value={maxLots}
            onChange={(e) => { setMaxLots(e.target.value); setDirty(true); }}
            className="w-full rounded-md border border-[var(--card-border)] bg-[var(--background)] px-2 py-1.5 text-sm"
          />
        </div>
        <div>
          <label className="block text-xs text-[var(--muted)] mb-1">Max Order Value</label>
          <input
            type="number"
            value={maxOrderValue}
            onChange={(e) => { setMaxOrderValue(e.target.value); setDirty(true); }}
            placeholder="No limit"
            className="w-full rounded-md border border-[var(--card-border)] bg-[var(--background)] px-2 py-1.5 text-sm"
          />
        </div>
        <div>
          <label className="block text-xs text-[var(--muted)] mb-1">Max Daily Orders</label>
          <input
            type="number"
            min={1}
            value={maxDailyOrders}
            onChange={(e) => { setMaxDailyOrders(e.target.value); setDirty(true); }}
            className="w-full rounded-md border border-[var(--card-border)] bg-[var(--background)] px-2 py-1.5 text-sm"
          />
        </div>
        <div>
          <label className="block text-xs text-[var(--muted)] mb-1">Max Open Positions</label>
          <input
            type="number"
            min={1}
            value={maxOpenPositions}
            onChange={(e) => { setMaxOpenPositions(e.target.value); setDirty(true); }}
            className="w-full rounded-md border border-[var(--card-border)] bg-[var(--background)] px-2 py-1.5 text-sm"
          />
        </div>
      </div>
    </div>
  );
}
