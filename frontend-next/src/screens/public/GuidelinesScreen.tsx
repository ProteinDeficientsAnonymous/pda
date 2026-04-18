import { useGuidelines, useUpdateGuidelines } from '@/api/content';
import { useAuthStore } from '@/auth/store';
import { EditableHtmlBlock } from '@/components/EditableHtmlBlock';
import { Permission, hasPermission } from '@/models/permissions';
import { ContentContainer, ContentError, ContentLoading } from './ContentContainer';

export default function GuidelinesScreen() {
  const { data, isPending, isError } = useGuidelines();
  const user = useAuthStore((s) => s.user);
  const canEdit = hasPermission(user, Permission.EditGuidelines);
  const update = useUpdateGuidelines();

  if (isPending) return <ContentLoading />;
  if (isError) return <ContentError message="couldn't load the guidelines — try refreshing" />;

  return (
    <ContentContainer>
      <h1 className="mb-4 text-2xl font-medium tracking-tight">community guidelines</h1>
      <EditableHtmlBlock
        canEdit={canEdit}
        contentHtml={data.contentHtml}
        initialPm={data.contentPm}
        onSave={(contentPm) => update.mutateAsync(contentPm).then(() => undefined)}
        placeholder="guidelines content"
      />
    </ContentContainer>
  );
}
