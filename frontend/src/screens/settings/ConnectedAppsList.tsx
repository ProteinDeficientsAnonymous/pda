import { format, formatDistanceToNow } from 'date-fns';
import { useState } from 'react';
import { toast } from 'sonner';

import { extractApiErrorOr } from '@/api/apiErrors';
import type { ConnectedApp } from '@/api/connect';
import { Button } from '@/components/ui/Button';
import { useConfirm } from '@/components/ui/useConfirm';

interface Props {
  apps: ConnectedApp[] | undefined;
  isPending: boolean;
  isError: boolean;
  onRevoke: (grantId: string) => Promise<unknown>;
}

export function ConnectedAppsList({ apps, isPending, isError, onRevoke }: Props) {
  const { confirm, element: confirmElement } = useConfirm();
  const [revokingId, setRevokingId] = useState<string | null>(null);

  async function disconnect(app: ConnectedApp) {
    if (revokingId) return;
    const confirmed = await confirm({
      title: 'disconnect app',
      message: `disconnect ${app.clientName}? it will lose access right away.`,
      confirmLabel: 'disconnect',
      destructive: true,
    });
    if (!confirmed) return;
    setRevokingId(app.id);
    try {
      await onRevoke(app.id);
      toast.success('app disconnected ✓');
    } catch (err) {
      toast.error(extractApiErrorOr(err, "couldn't disconnect — try again"));
    } finally {
      setRevokingId(null);
    }
  }

  if (isPending) return <p className="text-muted text-sm">loading connected apps…</p>;
  if (isError || !apps) return <p className="text-muted text-sm">couldn't load connected apps</p>;
  if (apps.length === 0) {
    return (
      <p className="text-muted text-sm">
        no apps connected. add pda as a connector in your ai app to connect one.
      </p>
    );
  }

  return (
    <>
      <ul className="flex flex-col gap-3">
        {apps.map((app) => (
          <li key={app.id} className="flex items-center justify-between gap-3">
            <div>
              <div className="text-foreground text-sm">{app.clientName}</div>
              <div className="text-muted text-xs">
                connected {format(app.createdAt, 'MMM d, yyyy').toLowerCase()}
              </div>
              <div className="text-muted text-xs">
                last used{' '}
                {app.lastUsedAt
                  ? formatDistanceToNow(app.lastUsedAt, { addSuffix: true }).toLowerCase()
                  : 'never'}
              </div>
            </div>
            <Button
              variant="secondary"
              disabled={revokingId !== null}
              onClick={() => void disconnect(app)}
            >
              {revokingId === app.id ? 'disconnecting…' : 'disconnect'}
            </Button>
          </li>
        ))}
      </ul>
      {confirmElement}
    </>
  );
}
