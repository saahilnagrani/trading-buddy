"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { Menu, X } from "lucide-react";
import { cn } from "@/lib/utils/formatters";
import { NotificationBell } from "@/components/layout/NotificationBell";
import { useAuth } from "@/lib/contexts/AuthContext";
import { logoutUser } from "@/lib/api";

const NAV_ITEMS = [
  { href: "/", label: "Dashboard" },
  { href: "/accounts", label: "Accounts" },
  { href: "/trade", label: "Trade" },
  { href: "/orders", label: "Orders" },
  { href: "/baskets", label: "Baskets" },
  { href: "/strategies", label: "Strategies" },
  { href: "/portfolio", label: "Portfolio" },
  { href: "/settings", label: "Settings" },
];

export function Navbar() {
  const pathname = usePathname();
  const { user } = useAuth();
  const [mobileOpen, setMobileOpen] = useState(false);

  // Close the drawer whenever the route changes
  useEffect(() => {
    setMobileOpen(false);
  }, [pathname]);

  // Lock body scroll while the drawer is open
  useEffect(() => {
    if (mobileOpen) {
      document.body.style.overflow = "hidden";
    } else {
      document.body.style.overflow = "";
    }
    return () => {
      document.body.style.overflow = "";
    };
  }, [mobileOpen]);

  return (
    <nav className="border-b border-[var(--card-border)] bg-[var(--card)]">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="flex h-14 items-center gap-3 sm:gap-6">
          {/* Mobile hamburger */}
          <button
            type="button"
            onClick={() => setMobileOpen(true)}
            aria-label="Open menu"
            className="lg:hidden inline-flex h-10 w-10 items-center justify-center rounded-md text-[var(--muted)] hover:text-white hover:bg-white/5 transition-colors -ml-2"
          >
            <Menu size={20} />
          </button>

          <Link href="/" className="text-base sm:text-lg font-semibold tracking-tight whitespace-nowrap">
            Trading Buddy
          </Link>

          {/* Desktop nav */}
          <div className="hidden lg:flex flex-1 items-center gap-1">
            {NAV_ITEMS.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  "whitespace-nowrap rounded-md px-3 py-1.5 text-sm transition-colors",
                  pathname === item.href
                    ? "bg-white/10 text-white"
                    : "text-[var(--muted)] hover:text-white"
                )}
              >
                {item.label}
              </Link>
            ))}
          </div>

          {/* Spacer on mobile so right-side icons align to the far edge */}
          <div className="flex-1 lg:hidden" />

          <NotificationBell />
          {user && (
            <div className="hidden sm:flex items-center gap-3">
              <span className="text-xs text-[var(--muted)]">{user.username}</span>
              <button
                onClick={logoutUser}
                className="text-xs text-[var(--muted)] hover:text-white transition-colors"
              >
                Logout
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Mobile drawer */}
      {mobileOpen && (
        <div className="lg:hidden fixed inset-0 z-50 flex">
          {/* Backdrop */}
          <div
            onClick={() => setMobileOpen(false)}
            className="absolute inset-0 bg-black/60 backdrop-blur-sm"
            aria-hidden="true"
          />
          {/* Panel */}
          <div className="relative flex h-full w-72 max-w-[85vw] flex-col bg-[var(--card)] border-r border-[var(--card-border)] shadow-xl">
            <div className="flex h-14 items-center justify-between px-4 border-b border-[var(--card-border)]">
              <span className="text-base font-semibold">Trading Buddy</span>
              <button
                type="button"
                onClick={() => setMobileOpen(false)}
                aria-label="Close menu"
                className="inline-flex h-10 w-10 items-center justify-center rounded-md text-[var(--muted)] hover:text-white hover:bg-white/5 transition-colors -mr-2"
              >
                <X size={20} />
              </button>
            </div>
            <div className="flex-1 overflow-y-auto py-3">
              {NAV_ITEMS.map((item) => (
                <Link
                  key={item.href}
                  href={item.href}
                  className={cn(
                    "block px-4 py-3 text-sm transition-colors",
                    pathname === item.href
                      ? "bg-white/10 text-white font-medium"
                      : "text-[var(--muted)] hover:text-white hover:bg-white/5"
                  )}
                >
                  {item.label}
                </Link>
              ))}
            </div>
            {user && (
              <div className="border-t border-[var(--card-border)] p-4">
                <p className="text-xs text-[var(--muted)] mb-2">Signed in as</p>
                <p className="text-sm font-medium mb-3">{user.username}</p>
                <button
                  onClick={logoutUser}
                  className="w-full rounded-md border border-[var(--card-border)] px-3 py-2 text-sm text-[var(--muted)] hover:text-white hover:border-white/20 transition-colors"
                >
                  Logout
                </button>
              </div>
            )}
          </div>
        </div>
      )}
    </nav>
  );
}
