"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "@/lib/auth";
import { api, QuotaStatus } from "@/lib/api";
import { useEffect, useState } from "react";

export function Navbar() {
  const { user, loading, signOut, getToken } = useAuth();
  const pathname = usePathname();
  const [quota, setQuota] = useState<QuotaStatus | null>(null);
  const [profileOpen, setProfileOpen] = useState(false);
  const [confirmSignOut, setConfirmSignOut] = useState(false);

  const handleSignOutClick = () => {
    if (confirmSignOut) {
      signOut();
    } else {
      setConfirmSignOut(true);
      setTimeout(() => setConfirmSignOut(false), 3000);
    }
  };

  useEffect(() => {
    if (user && !loading) {
      getToken().then((token) => {
        if (token) {
          api.getQuota(token).then((res) => {
            if (res.data) setQuota(res.data);
            else if (res.quota) setQuota(res.quota);
          });
        }
      });
    }
  }, [user, loading, getToken]);

  if (pathname === "/login") {
    return (
      <header className="nav-header px-6 py-4 flex items-center justify-center">
        <span className="text-xl font-bold tracking-tight text-white">T1T2.ai</span>
      </header>
    );
  }

  // Active state styling for nav links (simplistic)
  const getLinkCls = (path: string) => {
    return pathname === path
      ? "text-white font-medium"
      : "text-neutral-400 hover:text-white transition-colors duration-200";
  };

  return (
    <header className="nav-header px-6 py-4 flex items-center justify-between">
      {/* Brand */}
      <Link href="/" className="text-xl font-bold tracking-tight text-white hover:opacity-90">
        T1T2.ai
      </Link>

      {/* Pages */}
      <div className="hidden md:flex items-center gap-6">
        <Link href="/" className={getLinkCls("/")}>
          Dashboard
        </Link>
        <Link href="/dashboard" className={getLinkCls("/dashboard")}>
          History
        </Link>
      </div>

      {/* Right side status */}
      <div className="flex items-center gap-4">
        {!loading && user ? (
          <>
            <div className="flex items-center gap-4">
              {quota ? (
                <span className={`text-[11px] font-semibold px-3 py-1.5 rounded-full ${
                  quota.remaining === 0 
                    ? "text-[#EF4444] bg-[#450A0A]" 
                    : quota.remaining <= 2 
                      ? "text-[#EAB308] bg-[#422006]" 
                      : "text-[#22C55E] bg-[#052E16]"
                }`}>
                  {quota.remaining} / {quota.limit} today
                </span>
              ) : (
                <span className="text-[11px] font-semibold px-3 py-1.5 rounded-full text-[#22C55E] bg-[#052E16]">
                  5 / 5 today
                </span>
              )}
              <div className="relative">
                <button 
                  onClick={() => setProfileOpen(!profileOpen)}
                  className="w-8 h-8 rounded-full bg-blue-600 text-white text-xs font-bold flex items-center justify-center transition-opacity hover:opacity-80 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 focus:ring-offset-neutral-950"
                  title="Profile menu"
                >
                  {user.email?.substring(0, 2).toUpperCase() || "ME"}
                </button>
                
                {profileOpen && (
                  <>
                    <div 
                      className="fixed inset-0 z-40 cursor-default" 
                      onClick={() => setProfileOpen(false)}
                      aria-hidden="true"
                    />
                    <div className="absolute right-0 top-10 w-48 bg-neutral-900 border border-neutral-800 rounded-lg shadow-xl z-50 py-1 flex flex-col overflow-hidden">
                      <div className="px-4 py-3 border-b border-neutral-800">
                        <p className="text-sm border-b-0 font-medium text-white truncate text-left">{user.email || "User"}</p>
                        <p className="text-xs text-neutral-500 mt-1 text-left">Free Plan</p>
                      </div>
                      <Link 
                        href="/dashboard" 
                        onClick={() => setProfileOpen(false)}
                        className="px-4 py-2.5 text-sm text-neutral-300 hover:bg-neutral-800 hover:text-white transition-colors text-left flex items-center gap-2.5"
                      >
                        <div className="w-1.5 h-1.5 rounded-full bg-green-500"></div>
                        History
                      </Link>
                      <Link 
                        href="/dashboard" 
                        onClick={() => setProfileOpen(false)}
                        className="px-4 py-2.5 text-sm text-neutral-300 hover:bg-neutral-800 hover:text-white transition-colors text-left flex items-center gap-2.5"
                      >
                        <div className="w-1.5 h-1.5 rounded-full bg-blue-500"></div>
                        Account
                      </Link>
                      <div className="h-px bg-neutral-800 border-none my-1"></div>
                      <button
                        onClick={handleSignOutClick}
                        className="px-4 py-2 text-sm text-red-500 hover:bg-neutral-800 transition-colors text-left flex items-center gap-2.5"
                      >
                        <div className="w-1.5 h-1.5 rounded-full bg-red-500"></div>
                        {confirmSignOut ? "Confirm sign out?" : "Sign out"}
                      </button>
                    </div>
                  </>
                )}
              </div>
            </div>
          </>
        ) : !loading && !user ? (
          <Link href="/login" className="text-sm font-medium text-neutral-400 hover:text-white transition-colors">
            Sign in
          </Link>
        ) : null}
      </div>
    </header>
  );
}
