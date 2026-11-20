import { Link } from 'react-router-dom';

import { useEditablePage, useUpdateEditablePage } from '@/api/content';
import { PLANNING_GUIDELINES_SLUG } from '@/api/planningChecklist';
import { useHasPermission } from '@/auth/useAuth';
import { EditableHtmlBlock } from '@/components/EditableHtmlBlock';
import { Permission } from '@/models/permissions';
import { ContentError, ContentLoading } from '@/screens/public/ContentContainer';

export function GuidelinesTab() {
  const page = useEditablePage(PLANNING_GUIDELINES_SLUG);
  const update = useUpdateEditablePage(PLANNING_GUIDELINES_SLUG);
  const canEdit = useHasPermission(Permission.ManageEventPlanning);

  if (page.data) {
    return (
      <>
        <p className="text-foreground-secondary mb-4 text-sm">
          for the event itself, see the{' '}
          <Link to="/day-of" className="underline">
            day-of guide
          </Link>
        </p>
        <EditableHtmlBlock
          canEdit={canEdit}
          contentHtml={page.data.contentHtml}
          initialPm={page.data.contentPm}
          onSave={(contentPm) => update.mutateAsync({ contentPm }).then(() => undefined)}
          placeholder="planning guidelines"
        />
      </>
    );
  }
  if (page.isPending) return <ContentLoading />;
  return <ContentError message="couldn't load the guidelines — try refreshing" />;
}
