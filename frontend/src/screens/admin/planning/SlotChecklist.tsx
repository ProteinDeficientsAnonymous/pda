import { useId, useState } from 'react';

import { type ChecklistItem, useChecklist, useTickChecklistItem } from '@/api/planningChecklist';
import { Chevron } from '@/components/ui/Chevron';
import { cn } from '@/utils/cn';

import { ChecklistItemText } from './ChecklistList';
import { toastOnError } from './toastOnError';

function TickRow({
  item,
  label,
  done,
  saving,
  onToggle,
}: {
  item: ChecklistItem;
  label: string;
  done: boolean;
  saving: boolean;
  onToggle: (done: boolean) => void;
}) {
  return (
    <li>
      <label className="flex items-start gap-2 text-sm">
        <input
          type="checkbox"
          aria-label={`${item.text} for ${label}`}
          checked={done}
          disabled={saving}
          onChange={(e) => {
            onToggle(e.target.checked);
          }}
          className="mt-1"
        />
        <span className={cn('min-w-0 break-words', done && 'text-muted line-through')}>
          <ChecklistItemText item={item} />
        </span>
      </label>
    </li>
  );
}

export function SlotChecklist({
  slotId,
  label,
  doneIds,
}: {
  slotId: string;
  label: string;
  doneIds: string[];
}) {
  const { data: items } = useChecklist();
  const tick = useTickChecklistItem(slotId);
  // set when the panel opens so ticking doesn't move rows under the cursor or drop focus
  const [order, setOrder] = useState<string[] | null>(null);
  const [pending, setPending] = useState<Record<string, boolean>>({});
  const panelId = useId();

  if (!items || items.length === 0) return null;

  const isDone = (id: string) => pending[id] ?? doneIds.includes(id);
  const doneCount = items.filter((i) => isDone(i.id)).length;
  const rank = (id: string) => {
    const at = order?.indexOf(id) ?? -1;
    return at === -1 ? items.length : at;
  };
  const ordered = [...items].sort((a, b) => rank(a.id) - rank(b.id));

  async function toggle(itemId: string, done: boolean) {
    setPending((p) => ({ ...p, [itemId]: done }));
    await toastOnError(tick.mutateAsync({ itemId, done }), "couldn't save that — try again");
    setPending(({ [itemId]: _, ...rest }) => rest);
  }

  return (
    <div className="basis-full">
      <button
        type="button"
        aria-expanded={order !== null}
        aria-controls={panelId}
        className="text-foreground-secondary flex items-center gap-1 text-xs"
        onClick={() => {
          setOrder((o) =>
            o
              ? null
              : [...items.filter((i) => !isDone(i.id)), ...items.filter((i) => isDone(i.id))].map(
                  (i) => i.id,
                ),
          );
        }}
      >
        {`checklist · ${String(doneCount)}/${String(items.length)} done`}
        <Chevron open={order !== null} />
      </button>
      {order ? (
        <ul id={panelId} className="mt-2 flex flex-col gap-2">
          {ordered.map((item) => (
            <TickRow
              key={item.id}
              item={item}
              label={label}
              done={isDone(item.id)}
              saving={item.id in pending}
              onToggle={(done) => void toggle(item.id, done)}
            />
          ))}
        </ul>
      ) : null}
    </div>
  );
}
