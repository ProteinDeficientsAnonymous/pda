import { useState } from 'react';
import { useSearchParams } from 'react-router-dom';

import { type PlanningYear, useCreateYear, useMySlots, usePlanningYears } from '@/api/planning';
import { useHasPermission } from '@/auth/useAuth';
import { Button } from '@/components/ui/Button';
import { SegmentedControl } from '@/components/ui/SegmentedControl';
import { Select } from '@/components/ui/Select';
import { Permission } from '@/models/permissions';
import { ContentContainer, ContentError, ContentLoading } from '@/screens/public/ContentContainer';

import { AvailabilityForm } from './AvailabilityForm';
import { MySlots } from './MySlots';
import { PlanningGrid } from './PlanningGrid';
import { type PlanningTab, resolveTab, TAB_OPTIONS } from './planningTab';
import { SlotEditor } from './SlotEditor';
import { toastOnError } from './toastOnError';

// the latest year is >= the current year whenever one exists, so one rule covers both cases
function defaultYear(years: PlanningYear[]): number {
  return Math.max(...years.map((y) => y.year));
}

function StartYearButton({ year, onStarted }: { year: number; onStarted: (y: number) => void }) {
  const create = useCreateYear();

  async function start() {
    if (await toastOnError(create.mutateAsync(year), "couldn't start that year — try again")) {
      onStarted(year);
    }
  }

  return (
    <Button variant="secondary" disabled={create.isPending} onClick={() => void start()}>
      {`start ${String(year)}`}
    </Button>
  );
}

function MineTab({ year }: { year: number }) {
  return (
    <>
      <MySlots />
      <AvailabilityForm year={year} />
    </>
  );
}

export default function PlanningScreen() {
  const { data: years, isPending, isError } = usePlanningYears();
  const mySlots = useMySlots();
  const [params, setParams] = useSearchParams();
  const [picked, setPicked] = useState<number | null>(null);
  const [nextYear] = useState(() => new Date().getFullYear() + 1);
  const canManage = useHasPermission(Permission.ManageEventPlanning);

  if (isPending) return <ContentLoading />;
  if (isError) return <ContentError message="couldn't load planning years — try refreshing" />;

  const canStartNext = canManage && !years.some((y) => y.year === nextYear);

  if (years.length === 0) {
    return (
      <ContentContainer>
        <h1 className="mb-6 text-2xl font-medium tracking-tight">event planning</h1>
        <p className="text-muted mb-4 text-sm">no planning year yet 🌿</p>
        {canStartNext ? <StartYearButton year={nextYear} onStarted={setPicked} /> : null}
      </ContentContainer>
    );
  }

  const year = picked ?? defaultYear(years);
  const rawTab = params.get('tab');
  const hasWaiting = mySlots.data?.some((r) => r.status === 'proposed') ?? false;
  const tab = resolveTab(rawTab, hasWaiting);
  const awaitingDefault = canManage && rawTab === null && mySlots.isPending;

  function pickTab(next: PlanningTab) {
    setParams(
      (prev) => {
        const p = new URLSearchParams(prev);
        p.set('tab', next);
        return p;
      },
      { replace: true },
    );
  }

  return (
    <ContentContainer>
      <h1 className="mb-6 text-2xl font-medium tracking-tight">event planning</h1>
      <div className="mb-6 flex items-end gap-3">
        <div className="w-40">
          <Select
            label="year"
            value={String(year)}
            onChange={(e) => {
              setPicked(Number(e.target.value));
            }}
            options={years.map((y) => ({ value: String(y.year), label: String(y.year) }))}
          />
        </div>
        {canManage && tab === 'slots' && canStartNext ? (
          <StartYearButton year={nextYear} onStarted={setPicked} />
        ) : null}
      </div>
      {canManage ? (
        <SegmentedControl
          name="planning-tab"
          ariaLabel="planning view"
          options={TAB_OPTIONS}
          value={tab}
          onChange={pickTab}
          className="mb-6"
        />
      ) : null}
      {!canManage ? <MineTab year={year} /> : null}
      {canManage && awaitingDefault ? <ContentLoading /> : null}
      {canManage && !awaitingDefault && tab === 'schedule' ? <PlanningGrid year={year} /> : null}
      {canManage && !awaitingDefault && tab === 'mine' ? <MineTab year={year} /> : null}
      {canManage && !awaitingDefault && tab === 'slots' ? <SlotEditor year={year} /> : null}
    </ContentContainer>
  );
}
