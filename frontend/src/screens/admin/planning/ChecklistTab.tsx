import { useChecklist } from '@/api/planningChecklist';
import { ContentError, ContentLoading } from '@/screens/public/ContentContainer';

import { ChecklistList } from './ChecklistList';

export function ChecklistTab() {
  const { data, isPending, isError } = useChecklist();
  if (isPending) return <ContentLoading />;
  if (isError) return <ContentError message="couldn't load the checklist — try refreshing" />;
  return (
    <section>
      <p className="text-foreground-secondary mb-4 text-sm">
        tick these off for each of your events under my events
      </p>
      <ChecklistList items={data} />
    </section>
  );
}
