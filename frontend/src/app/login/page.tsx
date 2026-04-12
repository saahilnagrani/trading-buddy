"use client";

import { useEffect } from "react";
import { useSearchParams } from "next/navigation";
import { useAuthStatus } from "@/lib/hooks/useAccounts";
import { getLoginUrl } from "@/lib/api";
import { AccountStatusBadge } from "@/components/accounts/AccountStatusBadge";
import { formatTime } from "@/lib/utils/formatters";

export default function LoginPage() {
  const { data: statuses, isLoading, refetch } = useAuthStatus();
  const searchParams = useSearchParams();

  const successId = searchParams.get("success");
  const error = searchParams.get("error");

  // Refetch on successful callback redirect
  useEffect(() => {
    if (successId) refetch();
  }, [successId, refetch]);

  async function handleLogin(accountId: string) {
    try {
      const { login_url } = await getLoginUrl(accountId);
      window.open(login_url, "_blank");
    } catch {
      alert("Failed to generate login URL. Check that the backend is running.");
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Daily Login</h1>
        <p className="mt-1 text-sm text-[var(--muted)]">
          Log in to each Zerodha account. Tokens expire at 6:00 AM IST daily.
        </p>
      </div>

      {error && (
        <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400">
          Login failed: {error.replace(/_/g, " ")}
        </div>
      )}

      {successId && (
        <div className="rounded-lg border border-green-500/30 bg-green-500/10 px-4 py-3 text-sm text-green-400">
          Login successful! Token stored.
        </div>
      )}

      {isLoading ? (
        <p className="text-[var(--muted)]">Loading accounts...</p>
      ) : !statuses?.length ? (
        <p className="text-[var(--muted)]">
          No accounts configured. Go to Accounts to add one.
        </p>
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {statuses.map((status) => (
            <div
              key={status.account_id}
              className="rounded-lg border border-[var(--card-border)] bg-[var(--card)] p-4 space-y-3"
            >
              <div className="flex items-center justify-between">
                <h3 className="font-medium">{status.name}</h3>
                <AccountStatusBadge isLoggedIn={status.is_logged_in} />
              </div>

              {status.is_logged_in ? (
                <div className="text-sm text-[var(--muted)] space-y-1">
                  <p>Logged in at {formatTime(status.login_time)}</p>
                  <p>Expires at {formatTime(status.expires_at)}</p>
                </div>
              ) : (
                <p className="text-sm text-[var(--muted)]">
                  Not logged in today
                </p>
              )}

              <button
                onClick={() => handleLogin(status.account_id)}
                className={
                  status.is_logged_in
                    ? "w-full rounded-md border border-[var(--card-border)] px-4 py-2 text-sm text-[var(--muted)] hover:text-white transition-colors"
                    : "w-full rounded-md bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 transition-colors"
                }
              >
                {status.is_logged_in ? "Re-login" : "Login to Zerodha"}
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
