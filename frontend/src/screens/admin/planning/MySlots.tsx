import { type MySlot, useCommit, useDecline, useMySlots } from '@/api/planning';
import { Button } from '@/components/ui/Button';
import { ContentError, ContentLoading } from '@/screens/public/ContentContainer';

import { toastOnError } from './toastOnError';

const RESPOND_FAILED = "couldn't save your response — try again";

function SlotRow({
  row,
  showYear,
  children,
}: {
  row: MySlot;
  showYear: boolean;
  children: React.ReactNode;
}) {
  return (
    <li className="border-border flex flex-wrap items-center justify-between gap-2 border-t py-2 first:border-t-0">
      <p className="text-sm font-medium">
        {showYear ? `${String(row.year)} · ${row.slot.label}` : row.slot.label}
      </p>
      <div className="flex gap-2">{children}</div>
    </li>
  );
}

export function MySlots() {
  const { data, isPending, isError } = useMySlots();
  const commit = useCommit();
  const decline = useDecline();

  if (isPending) return <ContentLoading />;
  if (isError) return <ContentError message="couldn't load your slots — try refreshing" />;

  const busy = commit.isPending || decline.isPending;
  const showYear = new Set(data.map((r) => r.year)).size > 1;
  const waiting = data.filter((r) => r.status === 'proposed');

  function respond(action: typeof commit, row: MySlot) {
    void toastOnError(action.mutateAsync(row.assignmentId), RESPOND_FAILED);
  }

  return (
    <div className="mb-8">
      {data.length === 0 ? <p className="text-muted text-sm">nothing assigned yet 🌿</p> : null}
      {waiting.length > 0 ? (
        <section aria-labelledby="waiting-on-you" className="mb-4">
          <h2 id="waiting-on-you" className="mb-2 text-lg font-medium">
            waiting on you
          </h2>
          <ul>
            {waiting.map((row) => (
              <SlotRow key={row.assignmentId} row={row} showYear={showYear}>
                <Button
                  disabled={busy}
                  onClick={() => {
                    respond(commit, row);
                  }}
                >
                  i&apos;m in
                </Button>
                <Button
                  variant="secondary"
                  disabled={busy}
                  onClick={() => {
                    respond(decline, row);
                  }}
                >
                  can&apos;t do it
                </Button>
              </SlotRow>
            ))}
          </ul>
        </section>
      ) : null}
    </div>
  );
}
