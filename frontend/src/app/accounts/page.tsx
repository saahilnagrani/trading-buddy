"use client";

import { useState } from "react";
import {
  useAccounts,
  useCreateAccount,
  useUpdateAccount,
  useDeleteAccount,
} from "@/lib/hooks/useAccounts";
import { AccountStatusBadge } from "@/components/accounts/AccountStatusBadge";
import type { Account, AccountCreate } from "@/lib/types";

export default function AccountsPage() {
  const { data: accounts, isLoading } = useAccounts();
  const createMutation = useCreateAccount();
  const updateMutation = useUpdateAccount();
  const deleteMutation = useDeleteAccount();
  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState<Account | null>(null);
  const [showSecret, setShowSecret] = useState(false);
  const [feedback, setFeedback] = useState<{ type: "success" | "error"; message: string } | null>(null);

  function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = new FormData(e.currentTarget);
    const payload: AccountCreate = {
      name: form.get("name") as string,
      owner_name: (form.get("owner_name") as string) || undefined,
      kite_api_key: (form.get("kite_api_key") as string) || undefined,
      kite_api_secret: (form.get("kite_api_secret") as string) || undefined,
      max_lots: parseInt(form.get("max_lots") as string) || 1,
    };

    setFeedback(null);
    if (editing) {
      updateMutation.mutate(
        { id: editing.id, data: payload },
        {
          onSuccess: () => {
            setEditing(null);
            setShowForm(false);
            setFeedback({ type: "success", message: "Account updated successfully" });
          },
          onError: (err: any) => {
            setFeedback({ type: "error", message: err?.response?.data?.detail || err?.message || "Failed to update account" });
          },
        }
      );
    } else {
      createMutation.mutate(payload, {
        onSuccess: () => {
          setShowForm(false);
          setFeedback({ type: "success", message: "Account created successfully" });
        },
        onError: (err: any) => {
          setFeedback({ type: "error", message: err?.response?.data?.detail || err?.message || "Failed to create account" });
        },
      });
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Accounts</h1>
        <button
          onClick={() => {
            setEditing(null);
            setShowSecret(false);
            setShowForm(true);
          }}
          className="rounded-md bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 transition-colors"
        >
          Add Account
        </button>
      </div>

      {feedback && (
        <div
          className={`rounded-lg border px-4 py-3 text-sm ${
            feedback.type === "success"
              ? "border-green-500/30 bg-green-500/10 text-green-400"
              : "border-red-500/30 bg-red-500/10 text-red-400"
          }`}
        >
          {feedback.message}
        </div>
      )}

      {/* Add/Edit Form */}
      {showForm && (
        <form
          onSubmit={handleSubmit}
          className="rounded-lg border border-[var(--card-border)] bg-[var(--card)] p-4 space-y-4"
        >
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <div>
              <label className="block text-sm text-[var(--muted)] mb-1">
                Account Name *
              </label>
              <input
                name="name"
                required
                defaultValue={editing?.name ?? ""}
                className="w-full rounded-md border border-[var(--card-border)] bg-[var(--background)] px-3 py-2 text-sm"
                placeholder="e.g., Dad's Account"
              />
            </div>
            <div>
              <label className="block text-sm text-[var(--muted)] mb-1">
                Owner Name
              </label>
              <input
                name="owner_name"
                defaultValue={editing?.owner_name ?? ""}
                className="w-full rounded-md border border-[var(--card-border)] bg-[var(--background)] px-3 py-2 text-sm"
                placeholder="e.g., Rajesh"
              />
            </div>
            <div>
              <label className="block text-sm text-[var(--muted)] mb-1">
                Max Lots
              </label>
              <input
                name="max_lots"
                type="number"
                min={1}
                defaultValue={editing?.max_lots ?? 1}
                className="w-full rounded-md border border-[var(--card-border)] bg-[var(--background)] px-3 py-2 text-sm"
              />
            </div>
          </div>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div>
              <label className="block text-sm text-[var(--muted)] mb-1">
                Kite API Key
              </label>
              <input
                name="kite_api_key"
                className="w-full rounded-md border border-[var(--card-border)] bg-[var(--background)] px-3 py-2 text-sm font-mono"
                placeholder={editing?.has_kite_credentials ? "••••••• (saved)" : "From kite.trade developer console"}
              />
            </div>
            <div>
              <label className="block text-sm text-[var(--muted)] mb-1">
                Kite API Secret
              </label>
              <div className="relative">
                <input
                  name="kite_api_secret"
                  type={showSecret ? "text" : "password"}
                  className="w-full rounded-md border border-[var(--card-border)] bg-[var(--background)] px-3 py-2 pr-16 text-sm font-mono"
                  placeholder={editing?.has_kite_credentials ? "••••••• (saved)" : "From kite.trade developer console"}
                />
                <button
                  type="button"
                  onClick={() => setShowSecret(!showSecret)}
                  className="absolute right-2 top-1/2 -translate-y-1/2 text-xs text-[var(--muted)] hover:text-white"
                >
                  {showSecret ? "Hide" : "Show"}
                </button>
              </div>
            </div>
          </div>
          <div className="flex gap-2">
            <button
              type="submit"
              disabled={createMutation.isPending || updateMutation.isPending}
              className="rounded-md bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {createMutation.isPending || updateMutation.isPending
                ? "Saving..."
                : editing
                  ? "Update"
                  : "Create"}
            </button>
            <button
              type="button"
              onClick={() => {
                setShowForm(false);
                setEditing(null);
              }}
              className="rounded-md border border-[var(--card-border)] px-4 py-2 text-sm text-[var(--muted)] hover:text-white"
            >
              Cancel
            </button>
          </div>
        </form>
      )}

      {/* Accounts Table */}
      {isLoading ? (
        <p className="text-[var(--muted)]">Loading...</p>
      ) : !accounts?.length ? (
        <p className="text-[var(--muted)]">
          No accounts yet. Add one to get started.
        </p>
      ) : (
        <div className="overflow-x-auto rounded-lg border border-[var(--card-border)]">
          <table className="w-full text-sm">
            <thead className="bg-[var(--card)] text-left text-[var(--muted)]">
              <tr>
                <th className="px-4 py-3 font-medium">Name</th>
                <th className="px-4 py-3 font-medium">Owner</th>
                <th className="px-4 py-3 font-medium">Max Lots</th>
                <th className="px-4 py-3 font-medium">Kite API</th>
                <th className="px-4 py-3 font-medium">Status</th>
                <th className="px-4 py-3 font-medium">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[var(--card-border)]">
              {accounts.map((account) => (
                <tr key={account.id} className="bg-[var(--card)]">
                  <td className="px-4 py-3 font-medium">{account.name}</td>
                  <td className="px-4 py-3 text-[var(--muted)]">
                    {account.owner_name || "-"}
                  </td>
                  <td className="px-4 py-3">{account.max_lots}</td>
                  <td className="px-4 py-3">
                    <span className={`text-xs ${account.has_kite_credentials ? "text-green-400" : "text-red-400"}`}>
                      {account.has_kite_credentials ? "Configured" : "Missing"}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <AccountStatusBadge
                      isLoggedIn={account.token_status.is_logged_in}
                    />
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex gap-2">
                      <button
                        onClick={() => {
                          setEditing(account);
                          setShowForm(true);
                        }}
                        className="text-brand-500 hover:text-brand-600 text-sm"
                      >
                        Edit
                      </button>
                      <button
                        onClick={() => {
                          if (confirm(`Remove ${account.name}?`)) {
                            deleteMutation.mutate(account.id);
                          }
                        }}
                        className="text-red-400 hover:text-red-500 text-sm"
                      >
                        Remove
                      </button>
                    </div>
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
