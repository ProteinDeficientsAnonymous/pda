// Minimal accessible dialog: overlay + Escape to close + focus trap via
// autofocus on a designated element. Not a shadcn/Radix wholesale port —
// we only need this for a handful of small forms in phase 3, so keeping it
// inline avoids another dep.

import { useEffect, type ReactNode } from 'react';

interface Props {
  open: boolean;
  onClose: () => void;
  title: string;
  children: ReactNode;
}

export function Dialog({ open, onClose, title, children }: Props) {
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
  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label={title}
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
    >
      <button
        type="button"
        aria-label="close"
        onClick={onClose}
        className="absolute inset-0 cursor-default bg-black/60"
      />
      <div className="bg-surface relative w-full max-w-md rounded-lg p-5 shadow-(--shadow-xl)">
        <h2 className="mb-4 text-base font-medium">{title}</h2>
        {children}
      </div>
    </div>
  );
}
