import { useFaq, useUpdateFaq } from '@/api/content';
import { useAuthStore } from '@/auth/store';
import { EditableHtmlBlock } from '@/components/EditableHtmlBlock';
import { Permission, hasPermission } from '@/models/permissions';
import { ContentContainer, ContentError, ContentLoading } from './ContentContainer';

export default function FaqScreen() {
  const { data, isPending, isError } = useFaq();
  const user = useAuthStore((s) => s.user);
  const canEdit = hasPermission(user, Permission.EditFaq);
  const update = useUpdateFaq();

  if (isPending) return <ContentLoading />;
  if (isError) return <ContentError message="couldn't load the faq — try refreshing" />;

  return (
    <ContentContainer>
      <h1 className="mb-4 text-2xl font-medium tracking-tight">faq</h1>
      <EditableHtmlBlock
        canEdit={canEdit}
        contentHtml={data.contentHtml}
        initialPm={data.contentPm}
        onSave={(contentPm) => update.mutateAsync(contentPm).then(() => undefined)}
        placeholder="faq content"
      />
    </ContentContainer>
  );
}
