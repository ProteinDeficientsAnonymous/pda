// Docs tree of contents. Folders nest; each folder lists its docs. Read-only
// in phase 3 — edit flow lands alongside TipTap in phase 4.

import { Link } from 'react-router-dom';
import { useDocFolders, type DocFolder } from '@/api/docs';
import { ContentContainer, ContentError, ContentLoading } from '@/screens/public/ContentContainer';

export default function DocsScreen() {
  const { data, isPending, isError } = useDocFolders();
  if (isPending) return <ContentLoading />;
  if (isError) return <ContentError message="couldn't load the docs — try refreshing" />;

  if (data.length === 0) {
    return (
      <ContentContainer>
        <h1 className="mb-4 text-2xl font-medium tracking-tight">docs</h1>
        <p className="text-sm text-neutral-500">nothing here yet 🌿</p>
      </ContentContainer>
    );
  }

  return (
    <ContentContainer>
      <h1 className="mb-6 text-2xl font-medium tracking-tight">docs</h1>
      <div className="flex flex-col gap-4">
        {data.map((folder) => (
          <FolderView key={folder.id} folder={folder} depth={0} />
        ))}
      </div>
    </ContentContainer>
  );
}

function FolderView({ folder, depth }: { folder: DocFolder; depth: number }) {
  const Heading: React.ElementType = depth === 0 ? 'h2' : 'h3';
  return (
    <section>
      <Heading
        className={
          depth === 0 ? 'text-lg font-medium' : 'mt-3 text-sm font-medium text-neutral-600'
        }
      >
        {folder.name}
      </Heading>
      {folder.documents.length > 0 ? (
        <ul className="mt-2 flex flex-col gap-1">
          {folder.documents.map((d) => (
            <li key={d.id}>
              <Link
                to={`/docs/${d.id}`}
                className="block rounded px-2 py-1 text-sm text-neutral-800 hover:bg-neutral-100"
              >
                {d.title}
              </Link>
            </li>
          ))}
        </ul>
      ) : null}
      {folder.children.length > 0 ? (
        <div className="ms-3 mt-2 border-s border-neutral-200 ps-3">
          {folder.children.map((c) => (
            <FolderView key={c.id} folder={c} depth={depth + 1} />
          ))}
        </div>
      ) : null}
    </section>
  );
}
