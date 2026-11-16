import { useEditablePage, useUpdateEditablePage } from '@/api/content';
import { PLANNING_GUIDELINES_SLUG, useChecklist } from '@/api/planningChecklist';
import { useHasPermission } from '@/auth/useAuth';
import { EditableHtmlBlock } from '@/components/EditableHtmlBlock';
import { Permission } from '@/models/permissions';
import { ContentError, ContentLoading } from '@/screens/public/ContentContainer';

import { ChecklistList } from './ChecklistList';

function Checklist() {
  const { data, isPending, isError } = useChecklist();
  if (isPending) return <ContentLoading />;
  if (isError) return <ContentError message="couldn't load the checklist — try refreshing" />;
  return <ChecklistList items={data} />;
}

export function GuidelinesTab() {
  const page = useEditablePage(PLANNING_GUIDELINES_SLUG);
  const update = useUpdateEditablePage(PLANNING_GUIDELINES_SLUG);
  const canEdit = useHasPermission(Permission.ManageEventPlanning);

  return (
    <div className="flex flex-col gap-8">
      <section>
        <h2 className="mb-3 text-lg font-medium">checklist</h2>
        <p className="text-foreground-secondary mb-3 text-sm">
          tick these off for each of your events under my events
        </p>
        <Checklist />
      </section>
      <section>
        <h2 className="mb-3 text-lg font-medium">guidelines</h2>
        {page.isPending ? <ContentLoading /> : null}
        {page.isError ? (
          <ContentError message="couldn't load the guidelines — try refreshing" />
        ) : null}
        {page.data ? (
          <EditableHtmlBlock
            canEdit={canEdit}
            contentHtml={page.data.contentHtml}
            initialPm={page.data.contentPm}
            onSave={(contentPm) => update.mutateAsync({ contentPm }).then(() => undefined)}
            placeholder="planning guidelines"
          />
        ) : null}
      </section>
    </div>
  );
}
