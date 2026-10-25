"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { searchKnowledgeBase } from "@/lib/api";
import type { Guideline, Role } from "@/lib/types";
import { Modal, Spinner } from "./ui";

const ROLES: Role[] = ["Creator", "Manager", "Admin", "Legal"];

export default function AppHeader({
  role,
  onRoleChange,
  active,
}: {
  role: Role;
  onRoleChange?: (role: Role) => void;
  active: "workspace" | "analytics";
}) {
  const [searchOpen, setSearchOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<Guideline[]>([]);
  const [searching, setSearching] = useState(false);
  const [searched, setSearched] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    function onKey(event: KeyboardEvent) {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        setSearchOpen((open) => !open);
      }
      if (event.key === "Escape") setSearchOpen(false);
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  useEffect(() => {
    if (searchOpen) {
      const timer = setTimeout(() => inputRef.current?.focus(), 30);
      return () => clearTimeout(timer);
    }
    setQuery("");
    setResults([]);
    setSearched(false);
  }, [searchOpen]);

  async function runSearch(event: React.FormEvent) {
    event.preventDefault();
    if (!query.trim()) return;
    setSearching(true);
    setSearched(true);
    try {
      const data = await searchKnowledgeBase(query);
      setResults(data.items);
    } catch {
      setResults([]);
    } finally {
      setSearching(false);
    }
  }

  return (
    <>
      <header className="sticky top-0 z-40 border-b border-edge/80 bg-ink/85 backdrop-blur-xl">
        <div className="mx-auto flex h-16 max-w-[1800px] items-center gap-3 px-4 lg:px-6">
          <Link href="/" className="flex shrink-0 items-center gap-2.5">
            <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-signal/15 text-signal ring-1 ring-signal/30">
              <ShieldIcon />
            </span>
            <span className="hidden flex-col leading-tight sm:flex">
              <span className="text-sm font-bold tracking-tight text-white">BrandGuard AI</span>
              <span className="text-[10px] uppercase tracking-[0.22em] text-slate-500">Governance</span>
            </span>
          </Link>

          <div className="hidden items-center gap-1.5 rounded-xl border border-edge bg-white/[0.02] px-3 py-1.5 text-xs text-slate-300 xl:flex">
            <span className="text-slate-500">Org</span>
            <span className="font-semibold text-slate-200">Acme Corp</span>
            <span className="rounded bg-white/5 px-1.5 py-0.5 text-[9px] uppercase tracking-wider text-slate-400">
              Enterprise
            </span>
            <span className="px-1 text-slate-600">/</span>
            <span className="max-w-[220px] truncate text-slate-400">Q4 Global Launch</span>
          </div>

          <button
            onClick={() => setSearchOpen(true)}
            className="group ml-auto flex h-9 w-full max-w-md items-center gap-2 rounded-xl border border-edge bg-white/[0.03] px-3 text-left text-sm text-slate-500 transition hover:border-signal/40 hover:bg-white/[0.05]"
          >
            <SearchIcon />
            <span className="truncate">Search guidelines, claims, or scans…</span>
            <kbd className="ml-auto rounded border border-edge bg-ink px-1.5 py-0.5 text-[10px] font-semibold text-slate-500">
              Ctrl K
            </kbd>
          </button>

          <div className="flex shrink-0 items-center gap-1.5">
            <div className="hidden items-center gap-1 rounded-xl border border-edge bg-white/[0.02] p-1 md:flex">
              <Link
                href="/"
                className={`rounded-lg px-3 py-1.5 text-xs font-semibold transition ${
                  active === "workspace"
                    ? "bg-signal/15 text-white ring-1 ring-signal/30"
                    : "text-slate-400 hover:text-slate-100"
                }`}
              >
                Workspace
              </Link>
              <Link
                href="/analytics"
                className={`rounded-lg px-3 py-1.5 text-xs font-semibold transition ${
                  active === "analytics"
                    ? "bg-signal/15 text-white ring-1 ring-signal/30"
                    : "text-slate-400 hover:text-slate-100"
                }`}
              >
                Insights
              </Link>
            </div>

            <label className="hidden items-center gap-1.5 rounded-xl border border-edge bg-white/[0.02] px-2.5 py-1.5 sm:flex">
              <span className="text-[10px] uppercase tracking-widest text-slate-500">Role</span>
              <select
                value={role}
                onChange={(event) => onRoleChange?.(event.target.value as Role)}
                className="bg-transparent text-xs font-semibold text-slate-200 outline-none"
                aria-label="Active role"
              >
                {ROLES.map((item) => (
                  <option key={item} value={item} className="bg-panel">
                    {item}
                  </option>
                ))}
              </select>
            </label>

            <button
              className="relative flex h-9 w-9 items-center justify-center rounded-xl border border-edge bg-white/[0.02] text-slate-400 transition hover:text-white"
              aria-label="Notifications"
              title="3 approval requests waiting"
            >
              <BellIcon />
              <span className="absolute -right-1 -top-1 flex h-4 min-w-4 items-center justify-center rounded-full bg-critical px-1 text-[9px] font-bold text-white">
                3
              </span>
            </button>

            <div className="flex h-9 items-center gap-2 rounded-xl border border-edge bg-white/[0.02] pl-1 pr-2.5">
              <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-gradient-to-br from-signal to-purple-500 text-[11px] font-bold text-white">
                DS
              </span>
              <span className="hidden text-xs font-semibold text-slate-300 lg:block">Dhanraj</span>
            </div>
          </div>
        </div>

        <div className="mx-auto flex max-w-[1800px] gap-1 px-4 pb-2 md:hidden">
          <Link
            href="/"
            className={`flex-1 rounded-lg px-3 py-2 text-center text-xs font-semibold ${
              active === "workspace" ? "bg-signal/15 text-white" : "text-slate-400"
            }`}
          >
            Workspace
          </Link>
          <Link
            href="/analytics"
            className={`flex-1 rounded-lg px-3 py-2 text-center text-xs font-semibold ${
              active === "analytics" ? "bg-signal/15 text-white" : "text-slate-400"
            }`}
          >
            Insights
          </Link>
        </div>
      </header>

      <Modal open={searchOpen} onClose={() => setSearchOpen(false)} title="Knowledge base search">
        <form onSubmit={runSearch} className="flex gap-2">
          <input
            ref={inputRef}
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="e.g. performance benchmark, logo clear space, colour contrast"
            className="input"
          />
          <button type="submit" className="btn-primary shrink-0" disabled={searching}>
            {searching ? <Spinner /> : null}
            Search
          </button>
        </form>

        <div className="mt-4 space-y-2">
          {!searched && (
            <p className="px-1 text-xs leading-relaxed text-slate-500">
              Retrieval runs over {`the organisation's`} guideline clauses. Try “500% speedup”,
              “logo clear space”, “alt text” or “promo disclaimer”.
            </p>
          )}
          {searched && !searching && results.length === 0 && (
            <p className="rounded-lg border border-edge bg-white/[0.02] px-3 py-4 text-xs text-slate-500">
              No clauses matched that query.
            </p>
          )}
          {results.map((item) => (
            <div key={item.id} className="rounded-xl border border-edge bg-white/[0.02] p-3">
              <div className="flex flex-wrap items-center gap-2">
                <span className="rounded bg-signal/15 px-1.5 py-0.5 text-[10px] font-bold text-signal">
                  {item.code}
                </span>
                <span className="text-[11px] font-semibold text-slate-300">{item.section}</span>
                <span className="text-[10px] uppercase tracking-wider text-slate-600">
                  {item.category}
                </span>
              </div>
              <p className="mt-1 text-xs font-semibold text-white">{item.title}</p>
              <p className="mt-1 line-clamp-2 text-xs leading-relaxed text-slate-400">{item.content}</p>
            </div>
          ))}
        </div>
      </Modal>
    </>
  );
}

function ShieldIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden>
      <path
        d="M12 2.5 20 6v6.2c0 4.6-3.2 8-8 9.3-4.8-1.3-8-4.7-8-9.3V6l8-3.5Z"
        stroke="currentColor"
        strokeWidth="1.7"
        strokeLinejoin="round"
      />
      <path d="m8.5 12 2.4 2.4 4.6-4.8" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function SearchIcon() {
  return (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" aria-hidden>
      <circle cx="11" cy="11" r="7" stroke="currentColor" strokeWidth="1.8" />
      <path d="m20 20-3.2-3.2" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
    </svg>
  );
}

function BellIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" aria-hidden>
      <path
        d="M6 9a6 6 0 1 1 12 0c0 4 1.5 5.5 2 6H4c.5-.5 2-2 2-6Z"
        stroke="currentColor"
        strokeWidth="1.7"
        strokeLinejoin="round"
      />
      <path d="M9.5 18.5a2.5 2.5 0 0 0 5 0" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" />
    </svg>
  );
}
