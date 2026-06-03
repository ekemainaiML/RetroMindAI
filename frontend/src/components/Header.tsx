"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useUser } from "@/contexts/UserContext";
import { clearApiKey, clearJwt } from "@/utils/api";
import ThemeToggle from "./ThemeToggle";
import Logo from "./Logo";

export default function Header() {
  const pathname = usePathname();
  const router = useRouter();
  const { user, logout } = useUser();

  const navLinks = [
    { href: "/", label: "New Assessment" },
    { href: "/history", label: "History" },
    { href: "/analytics", label: "Analytics" },
    { href: "/knowledge-graph", label: "Knowledge Graph" },
    { href: "/settings", label: "Settings" },
    { href: "/admin", label: "Admin" },
  ];

  const handleLogout = () => {
    logout();
    clearJwt();
    clearApiKey();

    router.replace("/login");
  };

  return (
    <header className="sticky top-0 z-50 border-b border-border bg-surface/80 backdrop-blur-lg supports-[backdrop-filter]:bg-surface/70">
      <div className="mx-auto flex h-14 max-w-6xl items-center justify-between px-4">
        <Logo />

        <nav className="hidden md:flex items-center gap-0.5">
          {navLinks.map((link) => {
            const isActive = pathname === link.href;
            return (
              <Link
                key={link.href}
                href={link.href}
                className={`rounded-lg px-3 py-1.5 text-xs font-medium transition-all duration-150 ${
                  isActive
                    ? "bg-brand/10 text-brand shadow-sm"
                    : "text-text-secondary hover:bg-surface-hover hover:text-text-primary"
                }`}
              >
                {link.label}
              </Link>
            );
          })}
        </nav>

        <div className="flex items-center gap-1.5">
          <ThemeToggle />
          {user ? (
            <>
              <div className="hidden sm:flex items-center gap-2 ml-1.5 pl-3 border-l border-border">
                <div className="flex h-6 w-6 items-center justify-center rounded-full bg-brand/10 text-[10px] font-bold text-brand">
                  {user.name.charAt(0).toUpperCase()}
                </div>
                <span className="text-xs text-text-secondary truncate max-w-[80px]">
                  {user.name}
                </span>
                <button
                  onClick={handleLogout}
                  className="rounded-lg px-2 py-1 text-[11px] font-medium text-text-tertiary hover:text-danger hover:bg-danger/5 transition-colors"
                >
                  Sign Out
                </button>
              </div>
              <div className="sm:hidden flex items-center ml-1.5 pl-3 border-l border-border">
                <button
                  onClick={handleLogout}
                  className="rounded-lg px-2 py-1 text-[11px] font-medium text-text-tertiary hover:text-danger hover:bg-danger/5 transition-colors"
                >
                  Sign Out
                </button>
              </div>
            </>
          ) : (
            <div className="ml-1.5 pl-3 border-l border-border">
              <Link
                href="/login"
                className="rounded-lg px-3 py-1.5 text-xs font-medium text-brand hover:bg-brand/5 transition-colors"
              >
                Sign In
              </Link>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
