import { useCallback, useRef, useState } from 'react';
import { ConfirmDialog } from '@/components/ui/ConfirmDialog';

interface ConfirmOptions {
  title?: string;
  message: string;
  confirmLabel?: string;
  cancelLabel?: string;
  destructive?: boolean;
}

interface ConfirmState extends ConfirmOptions {
  resolve: (ok: boolean) => void;
}

export function useConfirm() {
  const [state, setState] = useState<ConfirmState | null>(null);
  const pendingRef = useRef<ConfirmState | null>(null);

  const confirm = useCallback((options: ConfirmOptions) => {
    return new Promise<boolean>((resolve) => {
      const next: ConfirmState = { ...options, resolve };
      pendingRef.current = next;
      setState(next);
    });
  }, []);

  const close = useCallback((ok: boolean) => {
    const current = pendingRef.current;
    pendingRef.current = null;
    setState(null);
    current?.resolve(ok);
  }, []);

  const element = state ? (
    <ConfirmDialog
      open
      title={state.title ?? 'are you sure?'}
      message={state.message}
      confirmLabel={state.confirmLabel ?? 'confirm'}
      cancelLabel={state.cancelLabel ?? 'cancel'}
      destructive={state.destructive ?? false}
      onCancel={() => {
        close(false);
      }}
      onConfirm={() => {
        close(true);
      }}
    />
  ) : null;

  return { confirm, element };
}
