import { useState } from 'react';

import { extractApiErrorOr } from '@/api/apiErrors';
import type { Club } from '@/api/clubs';
import { useClubs, useDeleteClub } from '@/api/clubs';
import { Button } from '@/components/ui/Button';
import { useConfirm } from '@/components/ui/useConfirm';
import { ContentContainer, ContentError, ContentLoading } from '@/screens/public/ContentContainer';

export default function ClubsAdminScreen() {
  const { data = [], isPending, isError } = useClubs();
  const del = useDeleteClub();
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const { confirm, element: confirmElement } = useConfirm();

  if (isPending) return <ContentLoading />;
  if (isError) return <ContentError message="couldn't load clubs — try refreshing" />;

  async function askDelete(c: Club) {
    const ok = await confirm({
      title: 'delete club',
      message: `delete "${c.name}"? its events keep their date and details but lose their club link.`,
      confirmLabel: 'delete',
      destructive: true,
    });
    if (!ok) return;
    setDeleteError(null);
    try {
      await del.mutateAsync(c.id);
    } catch (err) {
      setDeleteError(extractApiErrorOr(err, "couldn't delete — try again"));
    }
  }

  return (
    <ContentContainer>
      <h1 className="mb-6 text-2xl font-medium tracking-tight">clubs</h1>
      <p className="text-foreground-tertiary mb-6 text-sm">
        applicants pick the clubs they want to join on /join. requirements are shown next to each
        club.
      </p>
      {deleteError ? (
        <p role="alert" className="text-destructive mb-3 text-sm">
          {deleteError}
        </p>
      ) : null}

      {data.length === 0 ? (
        <p className="text-muted text-sm">no clubs yet</p>
      ) : (
        <ul aria-label="clubs" className="flex flex-col gap-2">
          {data.map((c) => (
            <li
              key={c.id}
              className="border-border bg-surface flex items-center justify-between gap-2 rounded-lg border p-3"
            >
              <div className="min-w-0 flex-1">
                <p className="text-sm font-medium break-words">{c.name}</p>
                {c.requirements ? (
                  <p className="text-muted text-xs break-words">{c.requirements}</p>
                ) : null}
              </div>
              <div className="flex shrink-0 gap-1">
                <Button
                  variant="ghost"
                  aria-label={`delete ${c.name}`}
                  onClick={() => {
                    void askDelete(c);
                  }}
                >
                  delete
                </Button>
              </div>
            </li>
          ))}
        </ul>
      )}

      {confirmElement}
    </ContentContainer>
  );
}
