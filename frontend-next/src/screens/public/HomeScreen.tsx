import { Link } from 'react-router-dom';
import { useHome, useUpdateHome } from '@/api/content';
import { useAuthStore } from '@/auth/store';
import { EditableHtmlBlock } from '@/components/EditableHtmlBlock';
import { Permission, hasPermission } from '@/models/permissions';
import { ContentContainer, ContentError, ContentLoading } from './ContentContainer';

export default function HomeScreen() {
  const { data, isPending, isError } = useHome();
  const isAuthed = useAuthStore((s) => s.status === 'authed');
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

      {!isAuthed && data.joinContentHtml ? (
        <section className="mt-10 rounded-lg border border-neutral-200 bg-white p-6">
          <EditableHtmlBlock
            canEdit={canEdit}
            contentHtml={data.joinContentHtml}
            initialPm={data.joinContentPm}
            onSave={(joinContentPm) => update.mutateAsync({ joinContentPm }).then(() => undefined)}
            placeholder="join cta content"
          />
          <Link
            to="/join"
            className="mt-4 inline-flex h-10 items-center rounded-md bg-neutral-900 px-4 text-sm font-medium text-white hover:bg-neutral-800"
          >
            request to join
          </Link>
        </section>
      ) : null}

      {data.donateUrl ? (
        <div className="mt-8 flex justify-center">
          <a
            href={data.donateUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex h-10 items-center rounded-md bg-neutral-900 px-4 text-sm font-medium text-white hover:bg-neutral-800"
          >
            donate
          </a>
        </div>
      ) : null}
    </ContentContainer>
  );
}
