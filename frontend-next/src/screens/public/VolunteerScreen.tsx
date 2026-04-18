import { isAxiosError } from 'axios';
import { useEditablePage, useUpdateEditablePage } from '@/api/content';
import { useAuthStore } from '@/auth/store';
import { EditableHtmlBlock } from '@/components/EditableHtmlBlock';
import { Permission, hasPermission } from '@/models/permissions';
import { ContentContainer, ContentError, ContentLoading } from './ContentContainer';

export default function VolunteerScreen() {
  const { data, isPending, error } = useEditablePage('volunteer');
  const user = useAuthStore((s) => s.user);
  const canEdit = hasPermission(user, Permission.EditGuidelines);
  const update = useUpdateEditablePage('volunteer');

  if (isPending) return <ContentLoading />;
  if (error) {
    if (isAxiosError(error) && error.response?.status === 403) {
      return <ContentError message="this page is for members only" />;
    }
    return <ContentError message="couldn't load the volunteer page — try refreshing" />;
  }
  return (
    <ContentContainer>
      <h1 className="mb-4 text-2xl font-medium tracking-tight">volunteer</h1>
      <EditableHtmlBlock
        canEdit={canEdit}
        contentHtml={data.contentHtml}
        initialPm={data.contentPm}
        onSave={(contentPm) => update.mutateAsync({ contentPm }).then(() => undefined)}
        placeholder="volunteer content"
      />
    </ContentContainer>
  );
}
