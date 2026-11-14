import { Link } from 'react-router-dom';

import { type MySlot, useCommit, useDecline, useMySlots } from '@/api/planning';
import { Button } from '@/components/ui/Button';
import { useConfirm } from '@/components/ui/useConfirm';
import { eventPath } from '@/models/event';
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
  const { slot, teammates } = row;
  return (
    <li className="border-border flex flex-wrap items-center justify-between gap-2 border-t py-2 first:border-t-0">
      <div>
        <p className="text-sm font-medium">
          {showYear ? `${String(row.year)} · ${slot.label}` : slot.label}
        </p>
        {teammates.length > 0 ? (
          <p className="text-muted text-xs">
            with {teammates.map((t) => `${t.name} (${t.status})`).join(', ')}
          </p>
        ) : null}
        {slot.eventId ? (
          <Link
            className="text-xs underline"
            to={eventPath({ id: slot.eventId, slug: slot.eventSlug ?? '' })}
          >
            view event
          </Link>
        ) : null}
      </div>
      <div className="flex gap-2">{children}</div>
    </li>
  );
}

export function MySlots() {
  const { data, isPending, isError } = useMySlots();
  const commit = useCommit();
  const decline = useDecline();
  const { confirm, element } = useConfirm();

  if (isPending) return <ContentLoading />;
  if (isError) return <ContentError message="couldn't load your slots — try refreshing" />;

  const busy = commit.isPending || decline.isPending;
  const showYear = new Set(data.map((r) => r.year)).size > 1;
  const waiting = data.filter((r) => r.status === 'proposed');

  const committed = data.filter((r) => r.status === 'committed');

  async function backOut(row: MySlot) {
    const ok = await confirm({
      message: `back out of ${row.slot.label}? the coordinator will be told`,
      confirmLabel: 'yes, back out',
      destructive: true,
    });
    if (ok) respond(decline, row);
  }

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
      {committed.length > 0 ? (
        <section aria-labelledby="your-slots">
          <h2 id="your-slots" className="mb-2 text-lg font-medium">
            your slots
          </h2>
          <ul>
            {committed.map((row) => (
              <SlotRow key={row.assignmentId} row={row} showYear={showYear}>
                <Button variant="destructive" disabled={busy} onClick={() => void backOut(row)}>
                  back out
                </Button>
              </SlotRow>
            ))}
          </ul>
        </section>
      ) : null}
      {element}
    </div>
  );
}
