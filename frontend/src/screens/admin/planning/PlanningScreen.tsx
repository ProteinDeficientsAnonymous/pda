import { useCallback, useEffect, useState } from 'react';
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
import { type PlanningTab, resolveTab, TAB_OPTIONS } from './planningTab';
import { ScheduleTab } from './ScheduleTab';
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

  const rawTab = params.get('tab');
  const urlTab = TAB_OPTIONS.some((o) => o.value === rawTab) ? rawTab : null;
  const hasWaiting = mySlots.data?.some((r) => r.status === 'proposed') ?? false;
  const defaultSettled = !canManage || urlTab !== null || !mySlots.isPending;
  const resolved = resolveTab(urlTab, hasWaiting);
  const tab: PlanningTab = canManage ? resolved : 'mine';

  const pickTab = useCallback(
    (next: PlanningTab) => {
      setParams(
        (prev) => {
          const p = new URLSearchParams(prev);
          p.set('tab', next);
          return p;
        },
        { replace: true },
      );
    },
    [setParams],
  );

  // persist the resolved default so answering a proposal doesn't flip the tab
  useEffect(() => {
    if (canManage && urlTab === null && defaultSettled) pickTab(resolved);
  }, [canManage, urlTab, defaultSettled, resolved, pickTab]);

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
      </div>
      {canManage ? (
        <SegmentedControl
          name="planning-tab"
          ariaLabel="planning view"
          options={TAB_OPTIONS}
          value={defaultSettled ? tab : null}
          onChange={pickTab}
          className="mb-6"
        />
      ) : null}
      {!defaultSettled ? <ContentLoading /> : null}
      {defaultSettled && tab === 'schedule' ? <ScheduleTab year={year} /> : null}
      {defaultSettled && tab === 'mine' ? <MineTab year={year} /> : null}
      {defaultSettled && tab === 'slots' ? (
        <>
          {canStartNext ? (
            <div className="mb-4">
              <StartYearButton year={nextYear} onStarted={setPicked} />
            </div>
          ) : null}
          <SlotEditor year={year} />
        </>
      ) : null}
    </ContentContainer>
  );
}
