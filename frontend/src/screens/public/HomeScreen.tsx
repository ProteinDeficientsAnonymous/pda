import { useHome, useUpdateHome } from '@/api/content';
import { useAuthStore } from '@/auth/store';
import { EditableHtmlBlock } from '@/components/EditableHtmlBlock';
import { hasPermission, Permission } from '@/models/permissions';

import { ContentContainer, ContentError, ContentLoading } from './ContentContainer';

export default function HomeScreen() {
  const { data, isPending, isError } = useHome();
  const user = useAuthStore((s) => s.user);
  const canEdit = hasPermission(user, Permission.EditHomepage);
  const update = useUpdateHome();

  if (isPending) return <ContentLoading />;
  if (isError) return <ContentError message="couldn't load the home page — try refreshing" />;

  return (
    <ContentContainer>
      <EditableHtmlBlock
        canEdit={canEdit}
        contentHtml={data.contentHtml}
        initialPm={data.contentPm}
        onSave={(contentPm) => update.mutateAsync({ contentPm }).then(() => undefined)}
        placeholder="home page content"
      />
    </ContentContainer>
  );
}
