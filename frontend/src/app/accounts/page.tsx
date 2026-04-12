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

  function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = new FormData(e.currentTarget);
    const payload: AccountCreate = {
      name: form.get("name") as string,
      owner_name: (form.get("owner_name") as string) || undefined,
      max_lots: parseInt(form.get("max_lots") as string) || 1,
    };

    if (editing) {
      updateMutation.mutate(
        { id: editing.id, data: payload },
        {
          onSuccess: () => {
            setEditing(null);
            setShowForm(false);
          },
        }
      );
    } else {
      createMutation.mutate(payload, {
        onSuccess: () => setShowForm(false),
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
            setShowForm(true);
          }}
          className="rounded-md bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 transition-colors"
        >
          Add Account
        </button>
      </div>

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
          <div className="flex gap-2">
            <button
              type="submit"
              className="rounded-md bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700"
            >
              {editing ? "Update" : "Create"}
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
