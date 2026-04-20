// Bottom-sheet menu opened by the header logo. The Flutter app uses
// showModalBottomSheet; this is a lightweight port — fixed overlay + panel
// sliding up from the bottom. Escape + backdrop close it, item-taps route
// and close, logout calls the auth store then closes.

import { useEffect } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { toast } from 'sonner';
import { useAuthStore } from '@/auth/store';
import { extractApiError } from '@/utils/errors';
import { cn } from '@/utils/cn';

interface Props {
  open: boolean;
  onClose: () => void;
}

interface MenuItem {
  to: string;
  label: string;
}

const ALWAYS_ITEMS: MenuItem[] = [
  { to: '/', label: 'home' },
  { to: '/faq', label: 'faq' },
  { to: '/install', label: 'install app' },
  { to: '/donate', label: 'donate' },
];

const AUTHED_ITEMS: MenuItem[] = [
  { to: '/guidelines', label: 'guidelines' },
  { to: '/volunteer', label: 'volunteer' },
  { to: '/settings', label: 'settings' },
];

export function PdaMenuSheet({ open, onClose }: Props) {
  const navigate = useNavigate();
  const location = useLocation();
  const isAuthed = useAuthStore((s) => s.status === 'authed');
  const logout = useAuthStore((s) => s.logout);

  useEffect(() => {
    if (!open) return;
    function onKey(e: KeyboardEvent) {
      if (e.key === 'Escape') onClose();
    }
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('keydown', onKey);
    };
  }, [open, onClose]);

  if (!open) return null;

  const items: MenuItem[] = [...ALWAYS_ITEMS, ...(isAuthed ? AUTHED_ITEMS : [])];

  function go(to: string) {
    onClose();
    if (location.pathname !== to) {
      void navigate(to);
    }
  }

  async function onLogout() {
    onClose();
    try {
      await logout();
      void navigate('/', { replace: true });
    } catch (err) {
      toast.error(extractApiError(err, "couldn't log out — try again"));
    }
  }

  return (
    <div className="fixed inset-0 z-30" role="presentation">
      <button
        type="button"
        aria-label="close menu"
        onClick={onClose}
        className="absolute inset-0 cursor-default bg-black/50"
      />
      <div
        role="dialog"
        aria-modal="true"
        aria-label="menu"
        className="bg-surface absolute inset-x-0 bottom-0 flex max-h-[80vh] flex-col rounded-t-xl pb-[env(safe-area-inset-bottom)] shadow-xl"
      >
        <div className="flex justify-center pt-2" aria-hidden="true">
          <span className="h-1 w-10 rounded-full bg-neutral-300" />
        </div>
        <ul className="overflow-y-auto py-2">
          {items.map((item) => {
            const active = location.pathname === item.to;
            return (
              <li key={item.to}>
                <button
                  type="button"
                  onClick={() => {
                    go(item.to);
                  }}
                  aria-current={active ? 'page' : undefined}
                  className={cn(
                    'text-foreground hover:bg-background flex w-full items-center px-5 py-3 text-start text-base',
                    active && 'bg-surface-dim font-medium',
                  )}
                >
                  {item.label}
                </button>
              </li>
            );
          })}
          {isAuthed ? (
            <li className="mt-1 border-t border-neutral-100">
              <button
                type="button"
                onClick={() => void onLogout()}
                className="text-foreground-secondary hover:bg-background flex w-full items-center px-5 py-3 text-start text-base"
              >
                log out
              </button>
            </li>
          ) : null}
        </ul>
      </div>
    </div>
  );
}
