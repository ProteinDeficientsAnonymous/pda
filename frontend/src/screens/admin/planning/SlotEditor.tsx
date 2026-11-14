import { useState } from 'react';

import {
  type PlanningSlot,
  type SlotKind,
  useCreateSlot,
  useDeleteSlot,
  usePlanningSlots,
  useUpdateSlot,
} from '@/api/planning';
import { Button } from '@/components/ui/Button';
import { Select } from '@/components/ui/Select';
import { TextField } from '@/components/ui/TextField';
import { useConfirm } from '@/components/ui/useConfirm';
import { MONTH_OPTIONS } from '@/utils/datetime';

import { toastOnError } from './toastOnError';

const KIND_OPTIONS: { value: SlotKind; label: string }[] = [
  { value: 'monthly', label: 'monthly' },
  { value: 'biannual', label: 'biannual' },
];

const SAVE_FAILED = "couldn't save slot — try again";

function SlotRow({ slot, year }: { slot: PlanningSlot; year: number }) {
  const update = useUpdateSlot(year);
  const remove = useDeleteSlot(year);
  const { confirm, element } = useConfirm();
  const [label, setLabel] = useState(slot.label);

  function patch(change: { label?: string; month?: number; kind?: SlotKind }) {
    return toastOnError(update.mutateAsync({ id: slot.id, patch: change }), SAVE_FAILED);
  }

  async function saveLabel() {
    const trimmed = label.trim();
    const changed = trimmed !== '' && trimmed !== slot.label;
    const saved = changed ? await patch({ label: trimmed }) : trimmed !== '';
    setLabel(saved ? trimmed : slot.label);
  }

  async function onDelete() {
    const ok = await confirm({
      message: 'delete this slot? anyone proposed or committed to it is dropped',
      confirmLabel: 'delete',
      destructive: true,
    });
    if (ok) await toastOnError(remove.mutateAsync(slot.id), "couldn't delete slot — try again");
  }

  return (
    <li className="flex flex-wrap items-end gap-2">
      <div className="min-w-40 flex-1">
        <TextField
          id={`slot-${slot.id}-label`}
          label={`label for ${slot.label}`}
          hideLabel
          value={label}
          onChange={(e) => {
            setLabel(e.target.value);
          }}
          onBlur={() => void saveLabel()}
        />
      </div>
      <Select
        id={`slot-${slot.id}-month`}
        label={`month for ${slot.label}`}
        hideLabel
        value={String(slot.month)}
        options={MONTH_OPTIONS}
        onChange={(e) => void patch({ month: Number(e.target.value) })}
      />
      <Select
        id={`slot-${slot.id}-kind`}
        label={`kind for ${slot.label}`}
        hideLabel
        value={slot.kind}
        options={KIND_OPTIONS}
        onChange={(e) => void patch({ kind: e.target.value as SlotKind })}
      />
      <Button
        variant="destructive"
        aria-label={`delete ${slot.label}`}
        disabled={remove.isPending || update.isPending}
        onClick={() => void onDelete()}
      >
        delete
      </Button>
      {element}
    </li>
  );
}

function AddSlotRow({ year }: { year: number }) {
  const create = useCreateSlot(year);
  const [label, setLabel] = useState('');
  const [month, setMonth] = useState('1');
  const [kind, setKind] = useState<SlotKind>('monthly');

  async function onAdd() {
    const input = { label: label.trim(), month: Number(month), kind };
    if (await toastOnError(create.mutateAsync(input), "couldn't add slot — try again")) {
      setLabel('');
    }
  }

  return (
    <div className="flex flex-wrap items-end gap-2">
      <div className="min-w-40 flex-1">
        <TextField
          label="new slot label"
          hideLabel
          placeholder="new slot"
          value={label}
          onChange={(e) => {
            setLabel(e.target.value);
          }}
        />
      </div>
      <Select
        label="new slot month"
        hideLabel
        value={month}
        options={MONTH_OPTIONS}
        onChange={(e) => {
          setMonth(e.target.value);
        }}
      />
      <Select
        label="new slot kind"
        hideLabel
        value={kind}
        options={KIND_OPTIONS}
        onChange={(e) => {
          setKind(e.target.value as SlotKind);
        }}
      />
      <Button disabled={create.isPending || !label.trim()} onClick={() => void onAdd()}>
        add slot
      </Button>
    </div>
  );
}

export function SlotEditor({ year }: { year: number }) {
  const slots = usePlanningSlots(year);
  if (slots.isPending) return null;
  if (slots.isError) return <p className="text-destructive text-sm">couldn't load slots</p>;

  return (
    <section className="mt-10 flex flex-col gap-4">
      <h2 className="text-lg font-medium">manage slots</h2>
      <ul className="flex flex-col gap-3">
        {slots.data.map((s) => (
          <SlotRow key={s.id} slot={s} year={year} />
        ))}
      </ul>
      <AddSlotRow year={year} />
    </section>
  );
}
