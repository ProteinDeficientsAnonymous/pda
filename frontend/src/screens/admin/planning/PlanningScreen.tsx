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
import { ChecklistTab } from './ChecklistTab';
import { GuidelinesTab } from './GuidelinesTab';
import { MySlots } from './MySlots';
import { explicitTab, type PlanningTab, resolveTab, tabOptions } from './planningTab';
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

export default function PlanningScreen() {
  const { data: years, isPending, isError } = usePlanningYears();
  const mySlots = useMySlots();
  const [params, setParams] = useSearchParams();
  const [picked, setPicked] = useState<number | null>(null);
  const [thisYear] = useState(() => new Date().getFullYear());
  const canManage = useHasPermission(Permission.ManageEventPlanning);

  const urlTab = explicitTab(params.get('tab'), canManage);
  const hasWaiting = mySlots.data?.some((r) => r.status === 'proposed') ?? false;
  const defaultSettled = !canManage || urlTab !== null || !mySlots.isPending;
  const tab: PlanningTab = resolveTab(urlTab, hasWaiting, canManage);

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
    if (urlTab === null && defaultSettled) pickTab(tab);
  }, [urlTab, defaultSettled, tab, pickTab]);

  if (isPending) return <ContentLoading />;
  if (isError) return <ContentError message="couldn't load planning years — try refreshing" />;

  const nextYear = years.length > 0 ? defaultYear(years) + 1 : thisYear + 1;

  if (years.length === 0) {
    return (
      <ContentContainer>
        <h1 className="mb-6 text-2xl font-medium tracking-tight">event planning</h1>
        <p className="text-muted mb-4 text-sm">no planning year yet 🌿</p>
        {canManage ? <StartYearButton year={nextYear} onStarted={setPicked} /> : null}
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
      <SegmentedControl
        name="planning-tab"
        ariaLabel="planning view"
        options={tabOptions(canManage)}
        value={defaultSettled ? tab : null}
        onChange={pickTab}
        className="mb-6 max-w-full overflow-x-auto [scrollbar-width:none]"
      />
      {!defaultSettled ? <ContentLoading /> : null}
      {defaultSettled && tab === 'schedule' ? <ScheduleTab key={year} year={year} /> : null}
      {defaultSettled && tab === 'events' ? <MySlots /> : null}
      {defaultSettled && tab === 'availability' ? <AvailabilityForm year={year} /> : null}
      {defaultSettled && tab === 'checklist' ? <ChecklistTab /> : null}
      {defaultSettled && tab === 'guidelines' ? <GuidelinesTab /> : null}
      {defaultSettled && tab === 'slots' ? (
        <>
          <SlotEditor year={year} />
          <div className="mt-6">
            <StartYearButton year={nextYear} onStarted={setPicked} />
          </div>
        </>
      ) : null}
    </ContentContainer>
  );
}
