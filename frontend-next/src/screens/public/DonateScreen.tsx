import { isAxiosError } from 'axios';
import { useEditablePage, useUpdateEditablePage } from '@/api/content';
import { useAuthStore } from '@/auth/store';
import { EditableHtmlBlock } from '@/components/EditableHtmlBlock';
// Editing EditablePage (including donate/volunteer) is gated by the same
// permission as guidelines per _pages.py.
import { Permission, hasPermission } from '@/models/permissions';
import { ContentContainer, ContentError, ContentLoading } from './ContentContainer';

export default function DonateScreen() {
  const { data, isPending, error } = useEditablePage('donate');
  const user = useAuthStore((s) => s.user);
  const canEdit = hasPermission(user, Permission.EditGuidelines);
  const update = useUpdateEditablePage('donate');

  if (isPending) return <ContentLoading />;
  if (error) {
    if (isAxiosError(error) && error.response?.status === 403) {
      return <ContentError message="this page is for members only" />;
    }
    return <ContentError message="couldn't load the donate page — try refreshing" />;
  }

  return (
    <ContentContainer>
      <h1 className="mb-4 text-2xl font-medium tracking-tight">donate</h1>
      <EditableHtmlBlock
        canEdit={canEdit}
        contentHtml={data.contentHtml}
        initialPm={data.contentPm}
        onSave={(contentPm) => update.mutateAsync({ contentPm }).then(() => undefined)}
        placeholder="donate content"
      />
    </ContentContainer>
  );
}
