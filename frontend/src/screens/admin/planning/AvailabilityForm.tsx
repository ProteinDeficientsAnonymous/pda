import { useState } from 'react';
import { toast } from 'sonner';

import {
  type BiannualInterest,
  useMyAvailability,
  usePlanningSlots,
  useSaveAvailability,
} from '@/api/planning';
import { Button } from '@/components/ui/Button';
import { SegmentedControl } from '@/components/ui/SegmentedControl';
import { TextField } from '@/components/ui/TextField';
import { Toggle } from '@/components/ui/Toggle';
import { ContentError, ContentLoading } from '@/screens/public/ContentContainer';

import { toastOnError } from './toastOnError';

const INTEREST_OPTIONS: { value: BiannualInterest; label: string }[] = [
  { value: 'yes', label: 'yes' },
  { value: 'maybe', label: 'maybe' },
  { value: 'no', label: 'no' },
];

const MAX_MONTHLIES = 12;

function parseCount(raw: string): number | null {
  const n = Number(raw);
  return raw.trim() !== '' && Number.isInteger(n) && n >= 0 && n <= MAX_MONTHLIES ? n : null;
}

interface StepButtonProps {
  label: string;
  disabled: boolean;
  onClick: () => void;
  children: string;
}

function StepButton({ label, disabled, onClick, children }: StepButtonProps) {
  return (
    <button
      type="button"
      aria-label={label}
      disabled={disabled}
      onClick={onClick}
      className="text-foreground hover:bg-surface-dim flex size-8 items-center justify-center rounded-full text-lg leading-none disabled:opacity-40"
    >
      {children}
    </button>
  );
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
  const currentCount = parseCount(count) ?? 0;

  function step(by: number) {
    setCount(String(Math.min(MAX_MONTHLIES, Math.max(0, currentCount + by))));
  }
  const monthlies = slots.filter((s) => s.kind === 'monthly');
  const extras = slots.filter((s) => s.kind !== 'monthly');

  const renderToggle = (s: Slots[number]) => (
    <Toggle
      key={s.id}
      label={s.label}
      checked={slotIds.has(s.id)}
      onChange={() => {
        toggle(s.id);
      }}
    />
  );

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
    const saving = save.mutateAsync({
      slotIds: slots.filter((s) => slotIds.has(s.id)).map((s) => s.id),
      biannualInterest: interest,
      monthlyCount,
    });
    if (await toastOnError(saving, "couldn't save availability — try again")) {
      toast.success('availability saved 🌱');
    }
  }

  return (
    <form onSubmit={(e) => void onSubmit(e)} className="flex flex-col gap-6">
      <fieldset className="flex flex-col gap-2">
        <legend className="text-foreground mb-1 text-sm font-medium">
          which slots can you plan?
        </legend>
        {monthlies.length > 0 && (
          <div
            data-testid="monthly-slots"
            className="grid grid-flow-col grid-cols-2 gap-x-6 gap-y-2"
            style={{ gridTemplateRows: `repeat(${String(Math.ceil(monthlies.length / 2))}, auto)` }}
          >
            {monthlies.map(renderToggle)}
          </div>
        )}
        {extras.length > 0 && (
          <div data-testid="extra-slots" className="grid grid-cols-2 gap-x-6 gap-y-2">
            {extras.map((s) => (
              <div key={s.id} className="col-start-1">
                {renderToggle(s)}
              </div>
            ))}
          </div>
        )}
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
          max={MAX_MONTHLIES}
          step={1}
          inputMode="numeric"
          className="[appearance:textfield] pr-20 [&::-webkit-inner-spin-button]:appearance-none [&::-webkit-outer-spin-button]:appearance-none"
          error={countValid ? undefined : 'enter a whole number from 0 to 12'}
          value={count}
          onChange={(e) => {
            setCount(e.target.value);
          }}
          rightAdornment={
            <div className="flex gap-1">
              <StepButton
                label="one fewer monthly"
                disabled={currentCount <= 0}
                onClick={() => {
                  step(-1);
                }}
              >
                −
              </StepButton>
              <StepButton
                label="one more monthly"
                disabled={currentCount >= MAX_MONTHLIES}
                onClick={() => {
                  step(1);
                }}
              >
                +
              </StepButton>
            </div>
          }
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
