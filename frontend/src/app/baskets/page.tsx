"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useAccounts } from "@/lib/hooks/useAccounts";
import { api } from "@/lib/api";

interface BasketItem {
  id: string;
  exchange: string;
  tradingsymbol: string;
  transaction_type: string;
  order_type: string;
  product: string;
  quantity: number;
  price_offset: number;
  sort_order: number;
}

interface Basket {
  id: string;
  name: string;
  description: string | null;
  is_active: boolean;
  items: BasketItem[];
  created_at: string;
}

export default function BasketsPage() {
  const qc = useQueryClient();
  const { data: accounts } = useAccounts();
  const { data: baskets, isLoading } = useQuery({
    queryKey: ["baskets"],
    queryFn: async () => (await api.get<Basket[]>("/baskets")).data,
  });

  const [showCreate, setShowCreate] = useState(false);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [executeId, setExecuteId] = useState<string | null>(null);
  const [selectedAccounts, setSelectedAccounts] = useState<string[]>([]);
  const [uniformLots, setUniformLots] = useState("1");

  // Create basket
  const [newName, setNewName] = useState("");
  const [newDesc, setNewDesc] = useState("");
  const [newItems, setNewItems] = useState<
    Array<{
      exchange: string;
      tradingsymbol: string;
      transaction_type: string;
      order_type: string;
      product: string;
      quantity: number;
      sort_order: number;
    }>
  >([]);

  const createMut = useMutation({
    mutationFn: async (data: any) => (await api.post("/baskets", data)).data,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["baskets"] });
      setShowCreate(false);
      setNewName("");
      setNewDesc("");
      setNewItems([]);
    },
  });

  const executeMut = useMutation({
    mutationFn: async ({ id, body }: { id: string; body: any }) =>
      (await api.post(`/baskets/${id}/execute`, body)).data,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["orders"] });
      setExecuteId(null);
    },
  });

  const deleteMut = useMutation({
    mutationFn: async (id: string) => await api.delete(`/baskets/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["baskets"] }),
  });

  function addItem() {
    setNewItems((prev) => [
      ...prev,
      {
        exchange: "NFO",
        tradingsymbol: "",
        transaction_type: "BUY",
        order_type: "LIMIT",
        product: "NRML",
        quantity: 25,
        sort_order: prev.length,
      },
    ]);
  }

  function handleCreate() {
    createMut.mutate({
      name: newName,
      description: newDesc || null,
      items: newItems.filter((i) => i.tradingsymbol),
    });
  }

  function handleExecute(basketId: string) {
    executeMut.mutate({
      id: basketId,
      body: {
        account_ids: selectedAccounts,
        mode: "uniform",
        uniform_lots: parseInt(uniformLots),
      },
    });
  }

  const loggedIn = accounts?.filter((a) => a.token_status.is_logged_in) ?? [];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Baskets</h1>
        <button
          onClick={() => setShowCreate(true)}
          className="rounded-md bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700"
        >
          Create Basket
        </button>
      </div>

      {/* Create Form */}
      {showCreate && (
        <div className="rounded-lg border border-[var(--card-border)] bg-[var(--card)] p-4 space-y-4">
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div>
              <label className="block text-sm text-[var(--muted)] mb-1">Name *</label>
              <input
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                className="w-full rounded-md border border-[var(--card-border)] bg-[var(--background)] px-3 py-2 text-sm"
                placeholder="e.g., NIFTY Iron Condor Weekly"
              />
            </div>
            <div>
              <label className="block text-sm text-[var(--muted)] mb-1">Description</label>
              <input
                value={newDesc}
                onChange={(e) => setNewDesc(e.target.value)}
                className="w-full rounded-md border border-[var(--card-border)] bg-[var(--background)] px-3 py-2 text-sm"
              />
            </div>
          </div>

          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <p className="text-sm font-medium">Items</p>
              <button onClick={addItem} className="text-sm text-brand-500 hover:text-brand-600">
                + Add Item
              </button>
            </div>
            {newItems.map((item, idx) => (
              <div key={idx} className="grid grid-cols-2 gap-2 sm:grid-cols-6 items-end">
                <input
                  value={item.tradingsymbol}
                  onChange={(e) => {
                    const updated = [...newItems];
                    updated[idx].tradingsymbol = e.target.value;
                    setNewItems(updated);
                  }}
                  placeholder="Symbol"
                  className="rounded-md border border-[var(--card-border)] bg-[var(--background)] px-2 py-1.5 text-sm"
                />
                <select
                  value={item.exchange}
                  onChange={(e) => {
                    const updated = [...newItems];
                    updated[idx].exchange = e.target.value;
                    setNewItems(updated);
                  }}
                  className="rounded-md border border-[var(--card-border)] bg-[var(--background)] px-2 py-1.5 text-sm"
                >
                  <option>NFO</option>
                  <option>NSE</option>
                </select>
                <select
                  value={item.transaction_type}
                  onChange={(e) => {
                    const updated = [...newItems];
                    updated[idx].transaction_type = e.target.value;
                    setNewItems(updated);
                  }}
                  className="rounded-md border border-[var(--card-border)] bg-[var(--background)] px-2 py-1.5 text-sm"
                >
                  <option value="BUY">BUY</option>
                  <option value="SELL">SELL</option>
                </select>
                <input
                  type="number"
                  value={item.quantity}
                  onChange={(e) => {
                    const updated = [...newItems];
                    updated[idx].quantity = parseInt(e.target.value) || 0;
                    setNewItems(updated);
                  }}
                  placeholder="Qty"
                  className="rounded-md border border-[var(--card-border)] bg-[var(--background)] px-2 py-1.5 text-sm"
                />
                <select
                  value={item.product}
                  onChange={(e) => {
                    const updated = [...newItems];
                    updated[idx].product = e.target.value;
                    setNewItems(updated);
                  }}
                  className="rounded-md border border-[var(--card-border)] bg-[var(--background)] px-2 py-1.5 text-sm"
                >
                  <option>NRML</option>
                  <option>MIS</option>
                </select>
                <button
                  onClick={() => setNewItems((prev) => prev.filter((_, i) => i !== idx))}
                  className="text-red-400 hover:text-red-500 text-sm"
                >
                  Remove
                </button>
              </div>
            ))}
          </div>

          <div className="flex gap-2">
            <button
              onClick={handleCreate}
              disabled={!newName || newItems.length === 0}
              className="rounded-md bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-50"
            >
              Create
            </button>
            <button
              onClick={() => setShowCreate(false)}
              className="rounded-md border border-[var(--card-border)] px-4 py-2 text-sm text-[var(--muted)]"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* Basket List */}
      {isLoading ? (
        <p className="text-[var(--muted)]">Loading...</p>
      ) : !baskets?.length ? (
        <p className="text-[var(--muted)]">No baskets yet.</p>
      ) : (
        <div className="space-y-3">
          {baskets.map((basket) => (
            <div
              key={basket.id}
              className="rounded-lg border border-[var(--card-border)] bg-[var(--card)]"
            >
              <div className="flex items-center justify-between p-4">
                <div>
                  <h3 className="font-medium">{basket.name}</h3>
                  {basket.description && (
                    <p className="text-sm text-[var(--muted)]">{basket.description}</p>
                  )}
                  <p className="text-xs text-[var(--muted)]">{basket.items.length} items</p>
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={() => setExpandedId(expandedId === basket.id ? null : basket.id)}
                    className="text-sm text-brand-500 hover:text-brand-600"
                  >
                    {expandedId === basket.id ? "Collapse" : "View"}
                  </button>
                  <button
                    onClick={() => setExecuteId(executeId === basket.id ? null : basket.id)}
                    className="rounded-md bg-brand-600 px-3 py-1.5 text-sm text-white hover:bg-brand-700"
                  >
                    Execute
                  </button>
                  <button
                    onClick={() => {
                      if (confirm(`Delete ${basket.name}?`)) deleteMut.mutate(basket.id);
                    }}
                    className="text-sm text-red-400 hover:text-red-500"
                  >
                    Delete
                  </button>
                </div>
              </div>

              {/* Items */}
              {expandedId === basket.id && (
                <div className="border-t border-[var(--card-border)] px-4 py-3">
                  <table className="w-full text-sm">
                    <thead className="text-[var(--muted)]">
                      <tr>
                        <th className="text-left py-1">#</th>
                        <th className="text-left py-1">Symbol</th>
                        <th className="text-left py-1">Side</th>
                        <th className="text-left py-1">Qty</th>
                        <th className="text-left py-1">Type</th>
                      </tr>
                    </thead>
                    <tbody>
                      {basket.items.map((item, idx) => (
                        <tr key={item.id}>
                          <td className="py-1">{idx + 1}</td>
                          <td className="py-1 font-medium">
                            {item.exchange}:{item.tradingsymbol}
                          </td>
                          <td className={`py-1 ${item.transaction_type === "BUY" ? "text-green-400" : "text-red-400"}`}>
                            {item.transaction_type}
                          </td>
                          <td className="py-1">{item.quantity}</td>
                          <td className="py-1 text-[var(--muted)]">{item.order_type}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}

              {/* Execute panel */}
              {executeId === basket.id && (
                <div className="border-t border-[var(--card-border)] p-4 space-y-3">
                  <div className="flex flex-wrap gap-2">
                    {loggedIn.map((a) => {
                      const sel = selectedAccounts.includes(a.id);
                      return (
                        <button
                          key={a.id}
                          onClick={() =>
                            setSelectedAccounts((prev) =>
                              sel ? prev.filter((x) => x !== a.id) : [...prev, a.id]
                            )
                          }
                          className={`rounded-md px-3 py-1.5 text-sm ${
                            sel
                              ? "bg-brand-600 text-white"
                              : "bg-[var(--background)] text-[var(--muted)]"
                          }`}
                        >
                          {a.name}
                        </button>
                      );
                    })}
                  </div>
                  <div className="flex items-center gap-3">
                    <label className="text-sm text-[var(--muted)]">Lots per account:</label>
                    <input
                      type="number"
                      min={1}
                      value={uniformLots}
                      onChange={(e) => setUniformLots(e.target.value)}
                      className="w-20 rounded-md border border-[var(--card-border)] bg-[var(--background)] px-2 py-1.5 text-sm"
                    />
                    <button
                      onClick={() => handleExecute(basket.id)}
                      disabled={selectedAccounts.length === 0 || executeMut.isPending}
                      className="rounded-md bg-brand-600 px-4 py-1.5 text-sm text-white hover:bg-brand-700 disabled:opacity-50"
                    >
                      {executeMut.isPending ? "Executing..." : "Go"}
                    </button>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
