import { useState } from 'react';

import { type PlanningYear, usePlanningYears } from '@/api/planning';
import { Select } from '@/components/ui/Select';
import { ContentContainer, ContentError, ContentLoading } from '@/screens/public/ContentContainer';

// the latest year is >= the current year whenever one exists, so one rule covers both cases
function defaultYear(years: PlanningYear[]): number {
  return Math.max(...years.map((y) => y.year));
}

export default function PlanningScreen() {
  const { data: years, isPending, isError } = usePlanningYears();
  const [picked, setPicked] = useState<number | null>(null);

  if (isPending) return <ContentLoading />;
  if (isError) return <ContentError message="couldn't load planning years — try refreshing" />;

  if (years.length === 0) {
    return (
      <ContentContainer>
        <h1 className="mb-6 text-2xl font-medium tracking-tight">event planning</h1>
        <p className="text-muted text-sm">no planning year yet 🌿</p>
      </ContentContainer>
    );
  }

  const year = picked ?? defaultYear(years);

  return (
    <ContentContainer>
      <h1 className="mb-6 text-2xl font-medium tracking-tight">event planning</h1>
      <div className="mb-6 max-w-40">
        <Select
          label="year"
          value={String(year)}
          onChange={(e) => {
            setPicked(Number(e.target.value));
          }}
          options={years.map((y) => ({ value: String(y.year), label: String(y.year) }))}
        />
      </div>
    </ContentContainer>
  );
}
