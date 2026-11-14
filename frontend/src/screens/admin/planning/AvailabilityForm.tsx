import { useState } from 'react';
import { toast } from 'sonner';

import { extractApiErrorOr } from '@/api/apiErrors';
import {
  type BiannualInterest,
  useMyAvailability,
  usePlanningSlots,
  useSaveAvailability,
} from '@/api/planning';
import { Button } from '@/components/ui/Button';
import { SegmentedControl } from '@/components/ui/SegmentedControl';
import { TextField } from '@/components/ui/TextField';
import { ContentError, ContentLoading } from '@/screens/public/ContentContainer';

const INTEREST_OPTIONS: { value: BiannualInterest; label: string }[] = [
  { value: 'yes', label: 'yes' },
  { value: 'maybe', label: 'maybe' },
  { value: 'no', label: 'no' },
];

function parseCount(raw: string): number | null {
  const n = Number(raw);
  return raw.trim() !== '' && Number.isInteger(n) && n >= 0 && n <= 12 ? n : null;
}

export function AvailabilityForm({ year }: { year: number }) {
  const slots = usePlanningSlots(year);
  const mine = useMyAvailability(year);

  if (slots.isPending || mine.isPending) return <ContentLoading />;
  if (slots.isError || mine.isError) {
    return <ContentError message="couldn't load availability — try refreshing" />;
  }
  return <FormFields key={year} year={year} slots={slots.data} initial={mine.data} />;
}

type Slots = NonNullable<ReturnType<typeof usePlanningSlots>['data']>;
type Initial = NonNullable<ReturnType<typeof useMyAvailability>['data']>;

function FormFields({ year, slots, initial }: { year: number; slots: Slots; initial: Initial }) {
  const save = useSaveAvailability(year);
  const [slotIds, setSlotIds] = useState(new Set(initial.slotIds));
  const [interest, setInterest] = useState<BiannualInterest | null>(initial.biannualInterest);
  const [count, setCount] = useState(String(initial.monthlyCount));

  const countValid = parseCount(count) !== null;

  function toggle(id: string) {
    setSlotIds((prev) => {
      const next = new Set(prev);
      if (!next.delete(id)) next.add(id);
      return next;
    });
  }

  async function onSubmit(e: React.SyntheticEvent) {
    e.preventDefault();
    const monthlyCount = parseCount(count);
    if (!interest || monthlyCount === null) return;
    try {
      await save.mutateAsync({
        slotIds: slots.filter((s) => slotIds.has(s.id)).map((s) => s.id),
        biannualInterest: interest,
        monthlyCount,
      });
      toast.success('availability saved 🌱');
    } catch (err) {
      toast.error(extractApiErrorOr(err, "couldn't save availability — try again"));
    }
  }

  return (
    <form onSubmit={(e) => void onSubmit(e)} className="flex flex-col gap-6">
      <fieldset className="flex flex-col gap-2">
        <legend className="text-foreground mb-1 text-sm font-medium">
          which slots can you plan?
        </legend>
        {slots.map((s) => (
          <label key={s.id} className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={slotIds.has(s.id)}
              onChange={() => {
                toggle(s.id);
              }}
            />
            {s.label}
          </label>
        ))}
      </fieldset>

      <div className="flex flex-col gap-2">
        <p className="text-foreground text-sm font-medium">want to plan a biannual?</p>
        <SegmentedControl
          name="biannual-interest"
          ariaLabel="want to plan a biannual?"
          options={INTEREST_OPTIONS}
          value={interest}
          onChange={setInterest}
        />
      </div>

      <div className="max-w-48">
        <TextField
          label="how many monthlies will you plan?"
          type="number"
          min={0}
          max={12}
          step={1}
          error={countValid ? undefined : 'enter a whole number from 0 to 12'}
          value={count}
          onChange={(e) => {
            setCount(e.target.value);
          }}
        />
      </div>

      <div>
        <Button type="submit" disabled={save.isPending || !interest || !countValid}>
          save availability
        </Button>
      </div>
    </form>
  );
}
