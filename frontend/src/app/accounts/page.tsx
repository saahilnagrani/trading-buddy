"use client";

import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import {
  useAccounts,
  useCreateAccount,
  useUpdateAccount,
  useDeleteAccount,
} from "@/lib/hooks/useAccounts";
import { getLoginUrl, logoutAccount } from "@/lib/api";
import { AccountStatusBadge } from "@/components/accounts/AccountStatusBadge";
import { formatTime } from "@/lib/utils/formatters";
import { Pencil, Trash2 } from "lucide-react";
import { useQueryClient } from "@tanstack/react-query";
import type { Account, AccountCreate } from "@/lib/types";

export default function AccountsPage() {
  return (
    <Suspense fallback={<p className="text-[var(--muted)]">Loading...</p>}>
      <AccountsContent />
    </Suspense>
  );
}

function AccountsContent() {
  const { data: accounts, isLoading } = useAccounts();
  const searchParams = useSearchParams();
  const qc = useQueryClient();
  const createMutation = useCreateAccount();
  const updateMutation = useUpdateAccount();
  const deleteMutation = useDeleteAccount();
  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState<Account | null>(null);
  const [showSecret, setShowSecret] = useState(false);
  const [userIdUnlocked, setUserIdUnlocked] = useState(false);
  const [feedback, setFeedback] = useState<{ type: "success" | "error"; message: string } | null>(null);

  // Handle OAuth callback results from ?success=... or ?error=... URL params
  useEffect(() => {
    const success = searchParams.get("success");
    const error = searchParams.get("error");
    if (success) {
      setFeedback({ type: "success", message: "Login successful! Token stored." });
      qc.invalidateQueries({ queryKey: ["accounts"] });
    } else if (error === "user_id_mismatch") {
      const expected = searchParams.get("expected") || "?";
      const actual = searchParams.get("actual") || "?";
      setFeedback({
        type: "error",
        message: `Login rejected: this account is locked to Kite user ${expected}, but you logged in as ${actual}. Log in with the correct Zerodha account, or edit the account and unlock the Kite User ID to fix a typo.`,
      });
    } else if (error) {
      setFeedback({ type: "error", message: `Login failed: ${error.replace(/_/g, " ")}` });
    }
  }, [searchParams, qc]);

  function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = new FormData(e.currentTarget);
    // Include kite_user_id when: creating, or editing an account that has no
    // existing user ID yet, or editing and the user clicked Unlock. For
    // already-bound accounts the field is read-only until unlocked, so we
    // don't risk overwriting a correct binding with a stale form value.
    const includeUserId = !editing || !editing.kite_user_id || userIdUnlocked;
    const payload: AccountCreate = {
      name: form.get("name") as string,
      owner_name: (form.get("owner_name") as string) || undefined,
      kite_api_key: (form.get("kite_api_key") as string) || undefined,
      kite_api_secret: (form.get("kite_api_secret") as string) || undefined,
      kite_user_id: includeUserId
        ? ((form.get("kite_user_id") as string) || undefined)
        : undefined,
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
            setUserIdUnlocked(false);
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
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div>
              <div className="flex items-center justify-between mb-1">
                <label className="block text-sm text-[var(--muted)]">
                  Kite User ID *
                  {editing && editing.kite_user_id && !userIdUnlocked && (
                    <span className="ml-2 text-[10px] uppercase tracking-wide text-[var(--muted)]/70">
                      locked
                    </span>
                  )}
                </label>
                {editing && editing.kite_user_id && !userIdUnlocked && (
                  <button
                    type="button"
                    onClick={() => {
                      if (
                        confirm(
                          "Unlocking allows you to change the Kite User ID for this account. Only do this if you entered the wrong ID by mistake. Proceed?"
                        )
                      ) {
                        setUserIdUnlocked(true);
                      }
                    }}
                    className="text-[11px] text-yellow-400 hover:text-yellow-300"
                  >
                    Unlock
                  </button>
                )}
              </div>
              <input
                name="kite_user_id"
                required={!editing}
                readOnly={!!(editing && editing.kite_user_id && !userIdUnlocked)}
                defaultValue={editing?.kite_user_id ?? ""}
                className={`w-full rounded-md border border-[var(--card-border)] bg-[var(--background)] px-3 py-2 text-sm font-mono [&:not(:placeholder-shown)]:uppercase ${
                  editing && editing.kite_user_id && !userIdUnlocked
                    ? "opacity-60 cursor-not-allowed"
                    : ""
                }`}
                placeholder="e.g., AB1234"
              />
              <p className="mt-1 text-[10px] text-[var(--muted)]">
                Binds this account to a specific Zerodha user. Login is
                rejected if the Kite account that authenticates does not
                match.
              </p>
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
                <th className="px-4 py-3 font-medium">Kite User ID</th>
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
                  <td className="px-4 py-3 font-mono text-xs text-[var(--muted)]">
                    {account.kite_user_id || "-"}
                  </td>
                  <td className="px-4 py-3">{account.max_lots}</td>
                  <td className="px-4 py-3">
                    <span className={`text-xs ${account.has_kite_credentials ? "text-green-400" : "text-red-400"}`}>
                      {account.has_kite_credentials ? "Configured" : "Missing"}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <div className="space-y-1">
                      <AccountStatusBadge
                        isLoggedIn={account.token_status.is_logged_in}
                      />
                      {account.token_status.is_logged_in && (
                        <div className="text-[10px] text-[var(--muted)] leading-tight">
                          <div>In: {formatTime(account.token_status.login_time)}</div>
                          <div>Exp: {formatTime(account.token_status.expires_at)}</div>
                        </div>
                      )}
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      {account.has_kite_credentials && (
                        <button
                          onClick={async () => {
                            try {
                              const { login_url } = await getLoginUrl(account.id);
                              window.open(login_url, "_blank");
                            } catch {
                              alert("Failed to generate login URL");
                            }
                          }}
                          className={`rounded-md px-3 py-1.5 text-xs font-medium transition-colors ${
                            account.token_status.is_logged_in
                              ? "border border-[var(--card-border)] text-[var(--muted)] hover:text-white hover:border-white/20"
                              : "bg-green-600 text-white hover:bg-green-700"
                          }`}
                        >
                          {account.token_status.is_logged_in ? "Re-login" : "Login"}
                        </button>
                      )}
                      {account.token_status.is_logged_in && (
                        <button
                          onClick={async () => {
                            if (
                              !confirm(
                                `End the current Kite session for ${account.name}? You'll need to log in again to place orders.`
                              )
                            )
                              return;
                            try {
                              await logoutAccount(account.id);
                              qc.invalidateQueries({ queryKey: ["accounts"] });
                              setFeedback({
                                type: "success",
                                message: `Session ended for ${account.name}`,
                              });
                            } catch (err: any) {
                              setFeedback({
                                type: "error",
                                message:
                                  err?.response?.data?.detail ||
                                  err?.message ||
                                  "Failed to end session",
                              });
                            }
                          }}
                          className="rounded-md border border-[var(--card-border)] px-3 py-1.5 text-xs font-medium text-red-400 hover:text-red-300 hover:border-red-400/40 transition-colors"
                        >
                          Logout
                        </button>
                      )}
                      <button
                        onClick={() => {
                          setEditing(account);
                          setUserIdUnlocked(false);
                          setShowForm(true);
                        }}
                        title="Edit"
                        className="rounded-md p-1.5 text-[var(--muted)] hover:text-brand-500 hover:bg-white/5 transition-colors"
                      >
                        <Pencil size={15} />
                      </button>
                      <button
                        onClick={() => {
                          if (confirm(`Remove ${account.name}?`)) {
                            deleteMutation.mutate(account.id);
                          }
                        }}
                        title="Remove"
                        className="rounded-md p-1.5 text-[var(--muted)] hover:text-red-400 hover:bg-white/5 transition-colors"
                      >
                        <Trash2 size={15} />
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
