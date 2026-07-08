// Group-text picker (see #500). Hosts choose which rsvp groups to message,
// then open an sms: group draft (primary) or copy the numbers (fallback for
// platforms with no SMS app).

import { useState } from 'react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/Button';
import { Dialog } from '@/components/ui/Dialog';
import type { Event } from '@/models/event';
import {
  availableGroups,
  buildSmsUri,
  collectRecipients,
  countForGroup,
  RecipientGroup,
  type RecipientGroupValue,
} from '@/utils/groupText';

const DEFAULT_GROUPS: RecipientGroupValue[] = [RecipientGroup.Going, RecipientGroup.Maybe];

function skippedNote(count: number): string {
  const subject = count === 1 ? 'person has' : 'people have';
  return `${String(count)} ${subject} no number and weren't included`;
}

interface Props {
  event: Event;
  open: boolean;
  onClose: () => void;
}

export function GroupTextDialog({ event, open, onClose }: Props) {
  const options = availableGroups(event);
  const [selected, setSelected] = useState<Set<RecipientGroupValue>>(
    () => new Set(DEFAULT_GROUPS.filter((g) => countForGroup(event, g) > 0)),
  );

  const { phones, skippedCount } = collectRecipients(event, selected);
  const smsUri = buildSmsUri(phones);
  const disabled = phones.length === 0;

  function toggle(value: RecipientGroupValue) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(value)) next.delete(value);
      else next.add(value);
      return next;
    });
  }

  function handleCopy() {
    if (disabled) return;
    void navigator.clipboard
      .writeText(phones.join(', '))
      .then(() => {
        const note = skippedCount > 0 ? ` — ${skippedNote(skippedCount)}` : '';
        toast.success(`copied ${String(phones.length)} numbers${note}`);
        onClose();
      })
      .catch(() => {
        toast.error("couldn't copy — try again");
      });
  }

  function handleText() {
    if (skippedCount > 0) toast.info(skippedNote(skippedCount));
    onClose();
  }

  return (
    <Dialog open={open} onClose={onClose} title="group text">
      <p className="text-foreground-secondary text-sm">pick who to message</p>
      <div className="mt-3 flex flex-wrap gap-1.5">
        {options.map((o) => (
          <GroupChip
            key={o.value}
            label={o.label}
            count={o.count}
            active={selected.has(o.value)}
            onToggle={() => {
              toggle(o.value);
            }}
          />
        ))}
      </div>
      <p className="text-muted mt-3 text-xs">
        {disabled
          ? 'no one selected'
          : `${String(phones.length)} ${phones.length === 1 ? 'number' : 'numbers'} selected`}
      </p>
      <div className="mt-4 flex items-center justify-between gap-2">
        <button
          type="button"
          onClick={handleCopy}
          disabled={disabled}
          className="text-muted hover:text-foreground text-xs underline disabled:cursor-not-allowed disabled:opacity-50"
        >
          copy numbers instead
        </button>
        <div className="flex gap-2">
          <Button variant="secondary" onClick={onClose}>
            cancel
          </Button>
          {disabled || !smsUri ? (
            <span
              aria-disabled="true"
              className="bg-toggle-off text-brand-on inline-flex h-10 cursor-not-allowed items-center justify-center rounded-md px-4 text-sm font-medium"
            >
              text
            </span>
          ) : (
            <a
              href={smsUri}
              onClick={handleText}
              aria-label="text them"
              className="bg-brand-600 text-brand-on hover:bg-brand-700 inline-flex h-10 items-center justify-center rounded-md px-4 text-sm font-medium transition-colors"
            >
              text {String(phones.length)}
            </a>
          )}
        </div>
      </div>
    </Dialog>
  );
}

function GroupChip({
  label,
  count,
  active,
  onToggle,
}: {
  label: string;
  count: number;
  active: boolean;
  onToggle: () => void;
}) {
  const base =
    'inline-flex items-center gap-1 rounded-full border px-2.5 py-1 text-xs transition-colors';
  const activeCls = 'border-brand-300 bg-brand-100 text-brand-700';
  const idleCls =
    'border-border text-foreground-secondary hover:border-border-strong hover:text-foreground';
  return (
    <button
      type="button"
      onClick={onToggle}
      aria-pressed={active}
      className={`${base} ${active ? activeCls : idleCls}`}
    >
      {label}
      <span className="opacity-60">{String(count)}</span>
    </button>
  );
}
