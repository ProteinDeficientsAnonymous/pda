import { useState } from 'react';
import { Outlet } from 'react-router-dom';

import { useAuthStore } from '@/auth/store';
import { FeedbackButton } from '@/components/FeedbackButton';

import { BottomNav } from './BottomNav';
import { NotificationBell } from './NotificationBell';
import { PdaMenuSheet } from './PdaMenuSheet';

export function AppShell() {
  const isAuthed = useAuthStore((s) => s.status === 'authed');
  const [menuOpen, setMenuOpen] = useState(false);

  return (
    <div className="bg-background flex min-h-screen flex-col">
      <header className="sticky top-0 z-10">
        <div className="mx-auto flex h-10 max-w-6xl items-center justify-between gap-4 px-4">
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
          <div className="flex items-center gap-1">{isAuthed ? <NotificationBell /> : null}</div>
        </div>
      </header>

      {/* Pad the bottom so the fixed BottomNav (h-14 + iOS safe area) doesn't
          cover the end of the scroll. Header already eats its own space.
          No overflow-x-hidden here: it makes this div a scroll container,
          which hijacks position:sticky descendants (they anchor to this
          non-scrolling box instead of the window). Wide content clamps
          itself locally with overflow-x-auto instead (see #286). */}
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
      <FeedbackButton />
      <BottomNav />
    </div>
  );
}
