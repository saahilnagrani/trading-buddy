"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils/formatters";
import { NotificationBell } from "@/components/layout/NotificationBell";

const NAV_ITEMS = [
  { href: "/", label: "Dashboard" },
  { href: "/login", label: "Login" },
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

  return (
    <nav className="border-b border-[var(--card-border)] bg-[var(--card)]">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="flex h-14 items-center gap-6">
          <Link href="/" className="text-lg font-semibold tracking-tight">
            Trading Buddy
          </Link>
          <div className="flex flex-1 items-center gap-1 overflow-x-auto">
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
          <NotificationBell />
        </div>
      </div>
    </nav>
  );
}
