import { useState } from 'react';

import { type PlanningYear, useCreateYear, usePlanningYears } from '@/api/planning';
import { useAuthStore } from '@/auth/store';
import { Button } from '@/components/ui/Button';
import { Select } from '@/components/ui/Select';
import { hasPermission, Permission } from '@/models/permissions';
import { ContentContainer, ContentError, ContentLoading } from '@/screens/public/ContentContainer';

import { AvailabilityForm } from './AvailabilityForm';
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
  const [picked, setPicked] = useState<number | null>(null);
  const [nextYear] = useState(() => new Date().getFullYear() + 1);
  const canManage = useAuthStore((s) => hasPermission(s.user, Permission.ManageEventPlanning));

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
        {canStartNext ? <StartYearButton year={nextYear} onStarted={setPicked} /> : null}
      </div>
      <AvailabilityForm year={year} />
    </ContentContainer>
  );
}
