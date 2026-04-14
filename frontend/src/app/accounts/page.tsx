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
import { Pencil, Trash2, ChevronDown, ChevronUp, ExternalLink, Info } from "lucide-react";
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
  const [showCredentialHelp, setShowCredentialHelp] = useState(false);
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
            setShowCredentialHelp(false);
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
          {/* ── Credential Setup Guide ───────────────────────────────── */}
          <div className="rounded-md border border-[var(--card-border)] overflow-hidden">
            <button
              type="button"
              onClick={() => setShowCredentialHelp((v) => !v)}
              className="flex w-full items-center justify-between px-4 py-3 text-sm hover:bg-white/[0.03] transition-colors"
            >
              <span className="flex items-center gap-2 text-[var(--muted)]">
                <Info size={14} className="shrink-0" />
                How to get Kite API credentials
              </span>
              {showCredentialHelp
                ? <ChevronUp size={14} className="text-[var(--muted)] shrink-0" />
                : <ChevronDown size={14} className="text-[var(--muted)] shrink-0" />}
            </button>

            {showCredentialHelp && (
              <div className="border-t border-[var(--card-border)] bg-[var(--background)] px-4 py-5 space-y-6 text-sm">
                <p className="text-[var(--muted)] text-xs leading-relaxed">
                  Each Zerodha user requires their own Kite Connect app. Create one app per user — never reuse API keys across accounts.
                </p>

                <ol className="space-y-5">
                  {/* Step 1 */}
                  <li className="flex gap-3">
                    <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-brand-600/20 text-[10px] font-semibold text-brand-400 mt-0.5">
                      1
                    </span>
                    <div className="space-y-1 min-w-0">
                      <p className="text-white/90 font-medium text-sm">Log in to the Kite Connect developer portal</p>
                      <p className="text-xs text-[var(--muted)] leading-relaxed">
                        Go to the developer portal and sign in with the Zerodha credentials of the account owner.
                      </p>
                      <a
                        href="https://developers.kite.trade/"
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-1 text-xs text-brand-400 hover:text-brand-300 transition-colors"
                      >
                        developers.kite.trade <ExternalLink size={10} />
                      </a>
                      {/* Drop file at public/screenshots/kite-01-developer-portal.png to show here */}
                      <img
                        src="/screenshots/kite-01-developer-portal.png"
                        alt="Kite Connect developer portal dashboard showing the Create new app button"
                        className="mt-2 w-full rounded border border-[var(--card-border)]"
                        onError={(e) => { (e.target as HTMLImageElement).style.display = "none"; }}
                      />
                    </div>
                  </li>

                  {/* Step 2 */}
                  <li className="flex gap-3">
                    <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-brand-600/20 text-[10px] font-semibold text-brand-400 mt-0.5">
                      2
                    </span>
                    <div className="space-y-1 min-w-0">
                      <p className="text-white/90 font-medium text-sm">Create a new app for this user</p>
                      <p className="text-xs text-[var(--muted)] leading-relaxed">
                        Click <strong className="text-white/70">Create new app</strong> and fill in the details.
                        Use a descriptive name like <em className="text-white/60">"Trading Buddy — AB1234"</em> so you can identify it later.
                        Select <strong className="text-white/70">Connect</strong> as the app type.
                      </p>
                      <a
                        href="https://developers.kite.trade/apps/new"
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-1 text-xs text-brand-400 hover:text-brand-300 transition-colors"
                      >
                        Create new app <ExternalLink size={10} />
                      </a>
                      {/* Drop file at public/screenshots/kite-02-create-app.png to show here */}
                      <img
                        src="/screenshots/kite-02-create-app.png"
                        alt="Kite Connect create new app form showing Name, App type, and Redirect URL fields"
                        className="mt-2 w-full rounded border border-[var(--card-border)]"
                        onError={(e) => { (e.target as HTMLImageElement).style.display = "none"; }}
                      />
                    </div>
                  </li>

                  {/* Step 3 */}
                  <li className="flex gap-3">
                    <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-brand-600/20 text-[10px] font-semibold text-brand-400 mt-0.5">
                      3
                    </span>
                    <div className="space-y-1 min-w-0">
                      <p className="text-white/90 font-medium text-sm">Set the Redirect URL in the app</p>
                      <p className="text-xs text-[var(--muted)] leading-relaxed">
                        In the app form, set <strong className="text-white/70">Redirect URL</strong> to the trading-buddy backend callback.
                        This must match exactly (including http vs https).
                      </p>
                      <code className="block mt-1.5 rounded bg-[var(--card)] border border-[var(--card-border)] px-2.5 py-1.5 text-[11px] font-mono text-[var(--muted)] select-all break-all">
                        {process.env.NEXT_PUBLIC_API_URL
                          ? `${process.env.NEXT_PUBLIC_API_URL}/api/auth/callback`
                          : "http://localhost:8000/api/auth/callback"}
                      </code>
                      <p className="text-[10px] text-[var(--muted)]/60 leading-relaxed">
                        For production: set <code className="font-mono">NEXT_PUBLIC_API_URL</code> in your frontend environment to your deployed backend URL.
                      </p>
                      {/* Drop file at public/screenshots/kite-03-redirect-url.png to show here */}
                      <img
                        src="/screenshots/kite-03-redirect-url.png"
                        alt="Kite Connect app form with the Redirect URL field filled in"
                        className="mt-2 w-full rounded border border-[var(--card-border)]"
                        onError={(e) => { (e.target as HTMLImageElement).style.display = "none"; }}
                      />
                    </div>
                  </li>

                  {/* Step 4 */}
                  <li className="flex gap-3">
                    <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-brand-600/20 text-[10px] font-semibold text-brand-400 mt-0.5">
                      4
                    </span>
                    <div className="space-y-1 min-w-0">
                      <p className="text-white/90 font-medium text-sm">Copy the API Key and API Secret</p>
                      <p className="text-xs text-[var(--muted)] leading-relaxed">
                        After saving the app, open it from your dashboard. Copy the{" "}
                        <strong className="text-white/70">API Key</strong> and{" "}
                        <strong className="text-white/70">API Secret</strong> and paste them into the fields below.
                      </p>
                      <a
                        href="https://developers.kite.trade/apps"
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-1 text-xs text-brand-400 hover:text-brand-300 transition-colors"
                      >
                        My apps <ExternalLink size={10} />
                      </a>
                      {/* Drop file at public/screenshots/kite-04-api-credentials.png to show here */}
                      <img
                        src="/screenshots/kite-04-api-credentials.png"
                        alt="Kite Connect app detail page showing API Key and API Secret with copy buttons"
                        className="mt-2 w-full rounded border border-[var(--card-border)]"
                        onError={(e) => { (e.target as HTMLImageElement).style.display = "none"; }}
                      />
                    </div>
                  </li>

                  {/* Step 5 */}
                  <li className="flex gap-3">
                    <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-brand-600/20 text-[10px] font-semibold text-brand-400 mt-0.5">
                      5
                    </span>
                    <div className="space-y-1 min-w-0">
                      <p className="text-white/90 font-medium text-sm">Find the user&apos;s Kite User ID</p>
                      <p className="text-xs text-[var(--muted)] leading-relaxed">
                        The Kite User ID is the Zerodha client ID for the account owner — a 6-character code like{" "}
                        <code className="rounded bg-[var(--card)] border border-[var(--card-border)] px-1 py-0.5 text-[11px] font-mono">
                          AB1234
                        </code>.
                        The owner can find it on their Kite profile page or Zerodha account dashboard.
                      </p>
                      <a
                        href="https://kite.zerodha.com/dashboard"
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-1 text-xs text-brand-400 hover:text-brand-300 transition-colors"
                      >
                        Kite dashboard <ExternalLink size={10} />
                      </a>
                      {/* Drop file at public/screenshots/kite-05-user-id.png to show here */}
                      <img
                        src="/screenshots/kite-05-user-id.png"
                        alt="Kite profile page showing the Zerodha client ID"
                        className="mt-2 w-full rounded border border-[var(--card-border)]"
                        onError={(e) => { (e.target as HTMLImageElement).style.display = "none"; }}
                      />
                    </div>
                  </li>
                </ol>

                {/* Best practices callout */}
                <div className="rounded-md border border-yellow-500/20 bg-yellow-500/5 px-3 py-3 space-y-2">
                  <p className="text-[11px] font-semibold uppercase tracking-wide text-yellow-400/80">
                    Best practices
                  </p>
                  <ul className="space-y-1.5 text-[11px] text-[var(--muted)] leading-relaxed">
                    <li className="flex gap-2">
                      <span className="text-yellow-400/50 mt-px shrink-0">•</span>
                      <span>
                        <strong className="text-white/70">One app per user:</strong>{" "}
                        sharing API keys across accounts means a suspension or rate-limit on one will block all of them.
                      </span>
                    </li>
                    <li className="flex gap-2">
                      <span className="text-yellow-400/50 mt-px shrink-0">•</span>
                      <span>
                        <strong className="text-white/70">Keep the API Secret private:</strong>{" "}
                        treat it like a password — never commit it to version control or share it over chat.
                      </span>
                    </li>
                    <li className="flex gap-2">
                      <span className="text-yellow-400/50 mt-px shrink-0">•</span>
                      <span>
                        <strong className="text-white/70">Redirect URL must match exactly:</strong>{" "}
                        a mismatch causes Kite to reject the OAuth callback with an &quot;Invalid redirect URL&quot; error.
                      </span>
                    </li>
                    <li className="flex gap-2">
                      <span className="text-yellow-400/50 mt-px shrink-0">•</span>
                      <span>
                        <strong className="text-white/70">Tokens expire at 6:00 AM IST daily:</strong>{" "}
                        each user must log in again at the start of every trading day — this is enforced by Zerodha, not trading-buddy.
                      </span>
                    </li>
                  </ul>
                </div>

                <a
                  href="https://kite.trade/docs/connect/v3/"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 text-xs text-[var(--muted)] hover:text-white transition-colors"
                >
                  Full Kite Connect API documentation <ExternalLink size={10} />
                </a>
              </div>
            )}
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
        <>
        {/* Mobile card list */}
        <div className="space-y-3 lg:hidden">
          {accounts.map((account) => (
            <div
              key={account.id}
              className="rounded-lg border border-[var(--card-border)] bg-[var(--card)] p-4 space-y-3"
            >
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2 flex-wrap">
                    <h3 className="font-semibold truncate">{account.name}</h3>
                    <AccountStatusBadge isLoggedIn={account.token_status.is_logged_in} />
                  </div>
                  {account.owner_name && (
                    <p className="text-xs text-[var(--muted)] mt-0.5">{account.owner_name}</p>
                  )}
                </div>
                <div className="flex items-center gap-1 shrink-0">
                  <button
                    onClick={() => {
                      setEditing(account);
                      setUserIdUnlocked(false);
                      setShowCredentialHelp(false);
                      setShowForm(true);
                    }}
                    title="Edit"
                    aria-label="Edit account"
                    className="inline-flex h-10 w-10 items-center justify-center rounded-md text-[var(--muted)] hover:text-brand-500 hover:bg-white/5 transition-colors"
                  >
                    <Pencil size={16} />
                  </button>
                  <button
                    onClick={() => {
                      if (confirm(`Remove ${account.name}?`)) {
                        deleteMutation.mutate(account.id);
                      }
                    }}
                    title="Remove"
                    aria-label="Remove account"
                    className="inline-flex h-10 w-10 items-center justify-center rounded-md text-[var(--muted)] hover:text-red-400 hover:bg-white/5 transition-colors"
                  >
                    <Trash2 size={16} />
                  </button>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-x-3 gap-y-2 text-xs">
                <div>
                  <p className="text-[var(--muted)]">Kite User ID</p>
                  <p className="font-mono text-[var(--muted)]">{account.kite_user_id || "-"}</p>
                </div>
                <div>
                  <p className="text-[var(--muted)]">Max Lots</p>
                  <p>{account.max_lots}</p>
                </div>
                <div>
                  <p className="text-[var(--muted)]">Kite API</p>
                  <p className={account.has_kite_credentials ? "text-green-400" : "text-red-400"}>
                    {account.has_kite_credentials ? "Configured" : "Missing"}
                  </p>
                </div>
                {account.token_status.is_logged_in && (
                  <div>
                    <p className="text-[var(--muted)]">Session</p>
                    <p className="text-[10px] leading-tight">
                      In {formatTime(account.token_status.login_time)}
                      <br />
                      Exp {formatTime(account.token_status.expires_at)}
                    </p>
                  </div>
                )}
              </div>

              <div className="flex flex-wrap gap-2 pt-1">
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
                    className={`flex-1 min-w-[6rem] rounded-md px-3 py-2 text-xs font-medium transition-colors ${
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
                    className="flex-1 min-w-[6rem] rounded-md border border-[var(--card-border)] px-3 py-2 text-xs font-medium text-red-400 hover:text-red-300 hover:border-red-400/40 transition-colors"
                  >
                    Logout
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>

        {/* Desktop table */}
        <div className="hidden lg:block overflow-x-auto rounded-lg border border-[var(--card-border)]">
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
                          setShowCredentialHelp(false);
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
        </>
      )}
    </div>
  );
}
