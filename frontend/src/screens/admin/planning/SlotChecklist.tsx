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
  onToggle,
}: {
  item: ChecklistItem;
  label: string;
  done: boolean;
  onToggle: (done: boolean) => void;
}) {
  return (
    <li>
      <label className="flex items-start gap-2 text-sm">
        <input
          type="checkbox"
          aria-label={`${item.text} for ${label}`}
          checked={done}
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
  const [open, setOpen] = useState(false);
  const [pending, setPending] = useState<Record<string, boolean>>({});
  const panelId = useId();

  if (!items || items.length === 0) return null;

  const isDone = (id: string) => pending[id] ?? doneIds.includes(id);
  const doneCount = items.filter((i) => isDone(i.id)).length;
  const ordered = [...items.filter((i) => !isDone(i.id)), ...items.filter((i) => isDone(i.id))];

  async function toggle(itemId: string, done: boolean) {
    setPending((p) => ({ ...p, [itemId]: done }));
    await toastOnError(tick.mutateAsync({ itemId, done }), "couldn't save that — try again");
    setPending(({ [itemId]: _, ...rest }) => rest);
  }

  return (
    <div className="basis-full">
      <button
        type="button"
        aria-expanded={open}
        aria-controls={panelId}
        className="text-foreground-secondary flex items-center gap-1 text-xs"
        onClick={() => {
          setOpen((o) => !o);
        }}
      >
        {`checklist · ${String(doneCount)}/${String(items.length)} done`}
        <Chevron open={open} />
      </button>
      {open ? (
        <ul id={panelId} className="mt-2 flex flex-col gap-2">
          {ordered.map((item) => (
            <TickRow
              key={item.id}
              item={item}
              label={label}
              done={isDone(item.id)}
              onToggle={(done) => void toggle(item.id, done)}
            />
          ))}
        </ul>
      ) : null}
    </div>
  );
}
