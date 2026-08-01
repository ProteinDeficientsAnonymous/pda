import { type ReactNode, useEffect } from 'react';
import { createPortal } from 'react-dom';

interface Props {
  open: boolean;
  onClose: () => void;
  title: string;
  children: ReactNode;
  /** Wider panel for tables / multi-column content. */
  wide?: boolean;
}

export function Dialog({ open, onClose, title, children, wide = false }: Props) {
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

  // Portal to body so dialog content (including nested <form>s) is not inside
  // a parent page form — HTML forbids nested forms and browsers submit the outer one.
  return createPortal(
    <div
      role="dialog"
      aria-modal="true"
      aria-label={title}
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
    >
      <button
        type="button"
        aria-label="dismiss"
        onClick={onClose}
        className="absolute inset-0 cursor-default bg-black/60"
      />
      <div
        className={
          wide
            ? 'bg-surface relative max-h-[min(90vh,40rem)] w-full max-w-2xl overflow-y-auto rounded-lg p-5 shadow-(--shadow-xl)'
            : 'bg-surface relative max-h-[min(90vh,40rem)] w-full max-w-md overflow-hidden rounded-lg p-5 shadow-(--shadow-xl)'
        }
      >
        <div className="mb-4 flex items-start justify-between gap-3">
          <h2 className="text-base font-medium">{title}</h2>
          <button
            type="button"
            aria-label="close"
            onClick={onClose}
            className="text-foreground-secondary hover:bg-surface-dim hover:text-foreground -me-1 -mt-1 inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-md transition-colors"
          >
            <CloseIcon />
          </button>
        </div>
        {children}
      </div>
    </div>,
    document.body,
  );
}

function CloseIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
      <path d="M4 4l8 8M12 4l-8 8" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" />
    </svg>
  );
}
