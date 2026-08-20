'use client';

import React, { useEffect, useRef } from 'react';
import Link from 'next/link';

export interface FilterPillOption<T extends string = string> {
  id: T;
  label: string;
}

export interface NavLinkItem {
  href: string;
  label: string;
  active?: boolean;
}

export interface TopBarProps<T extends string = string> {
  query?: string;
  setQuery?: (q: string) => void;
  activeFilter?: T;
  setActiveFilter?: (f: T) => void;
  filterPills?: readonly FilterPillOption<T>[];
  onOpenTimer?: () => void;
  onOpenChat?: () => void;
  placeholder?: string;
  showSearch?: boolean;
  navLinks?: NavLinkItem[];
  children?: React.ReactNode;
  activeRoute?: string;
}

export function TopBar<T extends string = string>({
  query = '',
  setQuery,
  activeFilter,
  setActiveFilter,
  filterPills = [],
  onOpenTimer,
  onOpenChat,
  placeholder = 'Search every Q&A, defense, term…',
  showSearch = true,
  navLinks,
  children,
  activeRoute,
}: TopBarProps<T>) {
  const inputRef = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    if (!showSearch || !setQuery) return;
    const handler = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        inputRef.current?.focus();
        inputRef.current?.select();
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [showSearch, setQuery]);

  const defaultNavLinks: NavLinkItem[] = [
    { href: '/', label: 'Overview' },
    { href: '/dashboard', label: 'Pit Map' },
    { href: '/alerts', label: 'Alerts' },
    { href: '/trends', label: 'Trends' },
    { href: '/pitch', label: 'Pitch Hub' },
  ];

  const linksToRender = navLinks || (showSearch && filterPills.length > 0 ? null : defaultNavLinks);

  return (
    <header className="sticky top-0 z-30 backdrop-blur-xl bg-white/80 border-b border-[#E6E8EE]">
      <div className="max-w-5xl mx-auto px-5 sm:px-6 md:px-10 py-4 md:py-5">
        <div className="flex items-center gap-2 sm:gap-3">
          {showSearch && setQuery ? (
            <div className="relative flex-1">
              <svg
                aria-hidden
                className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-[#5B6472]"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <circle cx="11" cy="11" r="7" />
                <path d="m20 20-3.5-3.5" />
              </svg>
              <input
                ref={inputRef}
                type="search"
                inputMode="search"
                autoComplete="off"
                autoCorrect="off"
                spellCheck="false"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder={placeholder}
                className="w-full pl-10 pr-20 py-2.5 text-[14px] rounded-full bg-white border border-[#E6E8EE] text-[#0B1220] placeholder:text-[#8A93A1] focus:border-[#2563EB] focus:ring-2 focus:ring-[#2563EB]/15 outline-none transition"
              />
              {query ? (
                <button
                  type="button"
                  onClick={() => setQuery('')}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-[#5B6472] hover:text-[#0B1220] text-[11px] px-2 py-0.5"
                >
                  clear
                </button>
              ) : (
                <kbd className="hidden sm:flex absolute right-3 top-1/2 -translate-y-1/2 items-center gap-1 text-[10px] font-mono text-[#8A93A1] border border-[#E6E8EE] rounded px-1.5 py-0.5 bg-white">
                  Ctrl K
                </kbd>
              )}
            </div>
          ) : (
            <div className="flex items-center gap-3 flex-1">
              <Link href="/" className="flex items-center gap-2 group">
                <span className="w-2.5 h-2.5 rounded-full bg-[#2563EB]" />
                <span className="font-mono text-[12px] font-semibold tracking-wider text-[#0B1220] uppercase">
                  SIH 2026 • Rockfall Warning
                </span>
              </Link>
            </div>
          )}

          {linksToRender && (
            <nav className="hidden md:flex items-center gap-1.5">
              {linksToRender.map((link) => {
                const isActive =
                  link.active !== undefined
                    ? link.active
                    : activeRoute === link.href;
                return (
                  <Link
                    key={link.href}
                    href={link.href}
                    className={`px-3 py-1.5 text-[12px] font-medium rounded-full border transition ${
                      isActive
                        ? 'bg-[#0B1220] text-white border-[#0B1220]'
                        : 'bg-white text-[#0B1220] border-[#E6E8EE] hover:border-[#0B1220]'
                    }`}
                  >
                    {link.label}
                  </Link>
                );
              })}
            </nav>
          )}

          {onOpenTimer && (
            <button
              onClick={onOpenTimer}
              title="Rehearsal Timer"
              aria-label="Open Rehearsal Timer"
              className="flex-shrink-0 w-10 h-10 rounded-full bg-[#0B1220] hover:bg-[#1a2235] text-white flex items-center justify-center shadow-sm shadow-slate-900/10 transition"
            >
              <svg
                className="w-4 h-4"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
                aria-hidden
              >
                <circle cx="12" cy="13" r="8" />
                <path d="M12 9v4l2 2M9 2h6" />
              </svg>
            </button>
          )}

          {onOpenChat && (
            <button
              onClick={onOpenChat}
              title="Open AI Helper"
              aria-label="Open AI Helper chat"
              className="flex-shrink-0 w-10 h-10 rounded-full bg-white border border-[#E6E8EE] hover:border-[#2563EB] hover:text-[#2563EB] text-[#0B1220] flex items-center justify-center transition relative"
            >
              <svg
                className="w-4 h-4"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
                aria-hidden
              >
                <path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z" />
              </svg>
              <span className="absolute -top-0.5 -right-0.5 w-2 h-2 rounded-full bg-[#2563EB] ring-2 ring-white" />
            </button>
          )}
        </div>

        {filterPills && filterPills.length > 0 && setActiveFilter && (
          <div className="mt-3 flex flex-wrap gap-1.5">
            {filterPills.map((p) => {
              const active = activeFilter === p.id;
              return (
                <button
                  key={p.id}
                  onClick={() => setActiveFilter(p.id)}
                  className={`px-3.5 py-1.5 text-[12px] font-medium rounded-full border transition ${
                    active
                      ? 'bg-[#0B1220] text-white border-[#0B1220]'
                      : 'bg-white text-[#0B1220] border-[#E6E8EE] hover:border-[#0B1220]'
                  }`}
                >
                  {p.label}
                </button>
              );
            })}
          </div>
        )}

        {children}
      </div>
    </header>
  );
}

export default TopBar;
