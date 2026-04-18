// App chrome — mobile-first layout matching the Flutter AppScaffold:
// sticky header with logo-triggered menu tray, a bottom nav with three
// destinations, and a centered content outlet in between. No responsive
// branching — one code path from phone to 4K.

import { useState } from 'react';
import { Link, Outlet } from 'react-router-dom';
import { useAuthStore } from '@/auth/store';
import { BottomNav } from './BottomNav';
import { NotificationBell } from './NotificationBell';
import { PdaMenuSheet } from './PdaMenuSheet';

export function AppShell() {
  const isAuthed = useAuthStore((s) => s.status === 'authed');
  const [menuOpen, setMenuOpen] = useState(false);

  return (
    <div className="flex min-h-screen flex-col bg-neutral-50">
      <header className="sticky top-0 z-10 border-b border-neutral-200 bg-white">
        <div className="mx-auto flex h-14 max-w-6xl items-center justify-between gap-4 px-4">
          <button
            type="button"
            aria-label="open menu"
            aria-expanded={menuOpen}
            aria-controls="pda-menu-sheet"
            onClick={() => {
              setMenuOpen(true);
            }}
            className="text-brand-700 hover:text-brand-800 text-base font-medium tracking-tight"
          >
            pda
          </button>
          <div className="flex items-center gap-1">
            {isAuthed ? (
              <NotificationBell />
            ) : (
              <Link
                to="/login"
                className="bg-brand-600 hover:bg-brand-700 inline-flex h-9 items-center rounded-md px-3 text-sm font-medium text-white"
              >
                sign in
              </Link>
            )}
          </div>
        </div>
      </header>

      {/* Pad the bottom so the fixed BottomNav (h-14 + iOS safe area) doesn't
          cover the end of the scroll. Header already eats its own space. */}
      <div className="flex-1 pb-[calc(3.5rem+env(safe-area-inset-bottom))]">
        <Outlet />
      </div>

      <div id="pda-menu-sheet">
        <PdaMenuSheet
          open={menuOpen}
          onClose={() => {
            setMenuOpen(false);
          }}
        />
      </div>
      <BottomNav />
    </div>
  );
}
