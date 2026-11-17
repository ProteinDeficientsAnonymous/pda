import { useChecklist } from '@/api/planningChecklist';
import { useHasPermission } from '@/auth/useAuth';
import { Permission } from '@/models/permissions';
import { ContentError, ContentLoading } from '@/screens/public/ContentContainer';

import { ChecklistEditor } from './ChecklistEditor';
import { ChecklistList } from './ChecklistList';

export function ChecklistTab() {
  const { data, isPending, isError } = useChecklist();
  const canEdit = useHasPermission(Permission.ManageEventPlanning);
  if (isPending) return <ContentLoading />;
  if (isError) return <ContentError message="couldn't load the checklist — try refreshing" />;
  return (
    <section>
      <p className="text-foreground-secondary mb-4 text-sm">
        tick these off for each of your events under my events
      </p>
      {canEdit ? <ChecklistEditor items={data} /> : <ChecklistList items={data} />}
    </section>
  );
}
