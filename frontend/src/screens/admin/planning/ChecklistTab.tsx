import { useChecklist } from '@/api/planningChecklist';
import { ContentError, ContentLoading } from '@/screens/public/ContentContainer';

import { ChecklistEditor } from './ChecklistEditor';

export function ChecklistTab() {
  const { data, isPending, isError } = useChecklist();
  if (isPending) return <ContentLoading />;
  if (isError) return <ContentError message="couldn't load the checklist — try refreshing" />;
  return (
    <section>
      <p className="text-foreground-secondary mb-4 text-sm">
        planners tick these off under each of their events in my events
      </p>
      {data.length === 0 ? (
        <p className="text-muted mb-4 text-sm">no checklist items yet 🌿</p>
      ) : null}
      <ChecklistEditor items={data} />
    </section>
  );
}
