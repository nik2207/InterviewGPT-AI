"use client";

import Image from "next/image";
import { useEffect, useRef, useState } from "react";

import type { UserProfile } from "@/types/user";

interface DashboardHeaderProps {
  user: UserProfile;
  onLogout: () => Promise<void>;
  onMenuToggle: () => void;
}

export function DashboardHeader({
  user,
  onLogout,
  onMenuToggle,
}: DashboardHeaderProps) {
  const [menuOpen, setMenuOpen] = useState(false);
  const [loggingOut, setLoggingOut] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setMenuOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const displayName = user.name || user.email.split("@")[0];

  const handleLogout = async () => {
    setLoggingOut(true);
    try {
      await onLogout();
    } finally {
      setLoggingOut(false);
      setMenuOpen(false);
    }
  };

  return (
    <header
      className="flex h-16 items-center justify-between border-b border-slate-200 bg-white px-4 lg:px-6"
      role="banner"
    >
      <div className="flex items-center gap-3">
        <button
          type="button"
          className="inline-flex rounded-lg border border-slate-200 p-2 text-slate-600 hover:bg-slate-50 lg:hidden"
          onClick={onMenuToggle}
          aria-label="Open navigation menu"
        >
          <MenuIcon />
        </button>
        <p className="hidden text-sm text-slate-500 sm:block">
          Interview preparation workspace
        </p>
      </div>

      <div className="relative" ref={menuRef}>
        <button
          type="button"
          className="flex items-center gap-3 rounded-lg border border-slate-200 px-3 py-2 hover:bg-slate-50"
          onClick={() => setMenuOpen((value) => !value)}
          aria-expanded={menuOpen}
          aria-haspopup="menu"
          aria-label="Account menu"
        >
          {user.picture ? (
            <Image
              src={user.picture}
              alt=""
              width={32}
              height={32}
              className="h-8 w-8 rounded-full"
              unoptimized
            />
          ) : (
            <span
              className="flex h-8 w-8 items-center justify-center rounded-full bg-brand-100 text-sm font-semibold text-brand-700"
              aria-hidden="true"
            >
              {displayName.charAt(0).toUpperCase()}
            </span>
          )}
          <span className="hidden max-w-[10rem] truncate text-sm font-medium text-slate-800 sm:inline">
            {displayName}
          </span>
        </button>

        {menuOpen ? (
          <div
            role="menu"
            className="absolute right-0 z-20 mt-2 w-56 rounded-xl border border-slate-200 bg-white p-2 shadow-lg"
          >
            <p className="px-3 py-2 text-xs text-slate-500">{user.email}</p>
            <button
              type="button"
              role="menuitem"
              className="w-full rounded-lg px-3 py-2 text-left text-sm text-slate-700 hover:bg-slate-50 disabled:opacity-60"
              onClick={handleLogout}
              disabled={loggingOut}
            >
              {loggingOut ? "Signing out…" : "Sign out"}
            </button>
          </div>
        ) : null}
      </div>
    </header>
  );
}

function MenuIcon() {
  return (
    <svg
      width="20"
      height="20"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      aria-hidden="true"
    >
      <path d="M4 6h16M4 12h16M4 18h16" />
    </svg>
  );
}
