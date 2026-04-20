import { Link, useParams } from 'react-router-dom';
import { useDocument, useUpdateDocument } from '@/api/docs';
import { useAuthStore } from '@/auth/store';
import { EditableHtmlBlock } from '@/components/EditableHtmlBlock';
import { Permission, hasPermission } from '@/models/permissions';
import { ContentContainer, ContentError, ContentLoading } from '@/screens/public/ContentContainer';

export default function DocDetailScreen() {
  const { id } = useParams<{ id: string }>();
  const { data, isPending, isError } = useDocument(id);
  const user = useAuthStore((s) => s.user);
  const canEdit = hasPermission(user, Permission.ManageDocuments);
  const update = useUpdateDocument(id ?? '');

  if (isPending) return <ContentLoading />;
  if (isError) return <ContentError message="couldn't load this doc — try refreshing" />;

  return (
    <ContentContainer>
      <Link to="/docs" className="text-muted mb-4 inline-block text-sm hover:underline">
        ← back to docs
      </Link>
      <h1 className="mb-4 text-2xl font-medium tracking-tight">{data.title}</h1>
      <EditableHtmlBlock
        canEdit={canEdit}
        contentHtml={data.contentHtml}
        initialPm={data.contentPm}
        onSave={(contentPm) => update.mutateAsync({ contentPm }).then(() => undefined)}
        placeholder="doc content"
      />
    </ContentContainer>
  );
}
