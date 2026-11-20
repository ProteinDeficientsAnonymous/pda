import { getApiStatus } from '@/api/apiErrors';
import { useEditablePage, useUpdateEditablePage } from '@/api/content';
import { useHasPermission } from '@/auth/useAuth';
import { EditableHtmlBlock } from '@/components/EditableHtmlBlock';
import { Permission } from '@/models/permissions';
import { ContentContainer, ContentError, ContentLoading } from '@/screens/public/ContentContainer';

const SLUG = 'day-of-guide';

export default function DayOfGuideScreen() {
  const { data, isPending, error } = useEditablePage(SLUG);
  const update = useUpdateEditablePage(SLUG);
  const canEdit = useHasPermission(Permission.ManageEventPlanning);

  if (isPending) return <ContentLoading />;
  if (error) {
    if (getApiStatus(error) === 403) {
      return <ContentError message="this page is for members only" />;
    }
    return <ContentError message="couldn't load the day-of guide — try refreshing" />;
  }
  return (
    <ContentContainer>
      <h1 className="mb-1 text-2xl font-medium tracking-tight">day-of guide</h1>
      <p className="text-foreground-secondary mb-6 text-sm">
        what needs to happen on the day of an official event
      </p>
      <EditableHtmlBlock
        canEdit={canEdit}
        contentHtml={data.contentHtml}
        initialPm={data.contentPm}
        onSave={(contentPm) => update.mutateAsync({ contentPm }).then(() => undefined)}
        placeholder="day-of guide"
      />
    </ContentContainer>
  );
}
