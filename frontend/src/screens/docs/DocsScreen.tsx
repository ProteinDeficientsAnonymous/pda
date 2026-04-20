// Docs tree: nested folders and documents. Members with manage_documents can
// create folders and docs, delete, and drag-reorder within the tree.

import { useMemo, useState, type ElementType } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { toast } from 'sonner';
import { useAuthStore } from '@/auth/store';
import {
  useCreateDocFolder,
  useCreateDocument,
  useDeleteDocFolder,
  useDeleteDocument,
  useDocFolders,
  useReorderDocuments,
  type DocFolder,
} from '@/api/docs';
import { SortableList } from '@/components/SortableList';
import { Button } from '@/components/ui/Button';
import { TextField } from '@/components/ui/TextField';
import { hasPermission, Permission } from '@/models/permissions';
import { ContentContainer, ContentError, ContentLoading } from '@/screens/public/ContentContainer';

export default function DocsScreen() {
  const user = useAuthStore((s) => s.user);
  const canManage = hasPermission(user, Permission.ManageDocuments);
  const { data, isPending, isError } = useDocFolders();
  const navigate = useNavigate();
  const createFolder = useCreateDocFolder();
  const createDoc = useCreateDocument();
  const deleteFolder = useDeleteDocFolder();
  const deleteDoc = useDeleteDocument();
  const reorderDocs = useReorderDocuments();

  const [newFolderName, setNewFolderName] = useState('');
  const [newDocTitle, setNewDocTitle] = useState('');
  const [newDocFolderId, setNewDocFolderId] = useState('');

  const flatFolders = useMemo(() => (data ? flattenFolders(data) : []), [data]);
  const defaultDocFolderId = flatFolders[0]?.id ?? '';
  const effectiveDocFolderId = newDocFolderId || defaultDocFolderId;

  if (isPending) return <ContentLoading />;
  if (isError) return <ContentError message="couldn't load the docs — try refreshing" />;

  const empty = data.length === 0;

  return (
    <ContentContainer>
      <h1 className="mb-6 text-2xl font-medium tracking-tight">docs</h1>

      {canManage ? (
        <section className="border-border bg-surface mb-8 rounded-lg border p-4">
          <h2 className="text-muted mb-3 text-xs font-medium tracking-wide">library admin</h2>
          <div className="mb-4 flex flex-col gap-2 sm:flex-row sm:items-end">
            <TextField
              label="new folder name"
              value={newFolderName}
              maxLength={120}
              onChange={(e) => {
                setNewFolderName(e.target.value);
              }}
            />
            <Button
              type="button"
              variant="secondary"
              disabled={!newFolderName.trim() || createFolder.isPending}
              onClick={() => {
                void (async () => {
                  try {
                    await createFolder.mutateAsync({
                      name: newFolderName.trim(),
                      parentId: null,
                    });
                    toast.success('folder created 🌱');
                    setNewFolderName('');
                  } catch {
                    toast.error("couldn't create folder");
                  }
                })();
              }}
            >
              {createFolder.isPending ? 'creating…' : 'create folder'}
            </Button>
          </div>
          <div className="flex flex-col gap-2 sm:flex-row sm:items-end">
            <TextField
              label="new document title"
              value={newDocTitle}
              maxLength={120}
              onChange={(e) => {
                setNewDocTitle(e.target.value);
              }}
            />
            <label className="text-muted flex min-w-[10rem] flex-col gap-1 text-xs">
              folder
              <select
                className="border-border bg-background text-foreground rounded-md border px-2 py-2 text-sm"
                value={effectiveDocFolderId}
                onChange={(e) => {
                  setNewDocFolderId(e.target.value);
                }}
              >
                {flatFolders.map((f) => (
                  <option key={f.id} value={f.id}>
                    {f.label.toLowerCase()}
                  </option>
                ))}
              </select>
            </label>
            <Button
              type="button"
              variant="secondary"
              disabled={
                !newDocTitle.trim() ||
                !effectiveDocFolderId ||
                createDoc.isPending ||
                flatFolders.length === 0
              }
              onClick={() => {
                void (async () => {
                  try {
                    const doc = await createDoc.mutateAsync({
                      title: newDocTitle.trim(),
                      folderId: effectiveDocFolderId,
                    });
                    toast.success('document created 🌱');
                    setNewDocTitle('');
                    void navigate(`/docs/${doc.id}`);
                  } catch {
                    toast.error("couldn't create document");
                  }
                })();
              }}
            >
              {createDoc.isPending ? 'creating…' : 'create document'}
            </Button>
          </div>
        </section>
      ) : null}

      {empty ? (
        <p className="text-muted text-sm">nothing here yet 🌿</p>
      ) : (
        <div className="flex flex-col gap-4">
          {data.map((folder) => (
            <FolderView
              key={folder.id}
              folder={folder}
              depth={0}
              canManage={canManage}
              deleteFolder={deleteFolder}
              deleteDoc={deleteDoc}
              reorderDocs={reorderDocs}
            />
          ))}
        </div>
      )}
    </ContentContainer>
  );
}

function flattenFolders(folders: DocFolder[], prefix = ''): { id: string; label: string }[] {
  const out: { id: string; label: string }[] = [];
  for (const f of folders) {
    const label = prefix ? `${prefix} / ${f.name}` : f.name;
    out.push({ id: f.id, label });
    out.push(...flattenFolders(f.children, label));
  }
  return out;
}

type DeleteFolder = ReturnType<typeof useDeleteDocFolder>;
type DeleteDoc = ReturnType<typeof useDeleteDocument>;
type ReorderDocs = ReturnType<typeof useReorderDocuments>;

function FolderView({
  folder,
  depth,
  canManage,
  deleteFolder,
  deleteDoc,
  reorderDocs,
}: {
  folder: DocFolder;
  depth: number;
  canManage: boolean;
  deleteFolder: DeleteFolder;
  deleteDoc: DeleteDoc;
  reorderDocs: ReorderDocs;
}) {
  const Heading: ElementType = depth === 0 ? 'h2' : 'h3';
  return (
    <section>
      <div className="flex flex-wrap items-center gap-2">
        <Heading
          className={
            depth === 0
              ? 'text-lg font-medium'
              : 'text-foreground-tertiary mt-3 text-sm font-medium'
          }
        >
          {folder.name.toLowerCase()}
        </Heading>
        {canManage ? (
          <Button
            type="button"
            variant="ghost"
            className="text-muted text-xs"
            onClick={() => {
              const ok = window.confirm(`delete folder "${folder.name}" and everything inside?`);
              if (!ok) return;
              void deleteFolder.mutateAsync(folder.id).then(
                () => toast.success('folder deleted'),
                () => toast.error("couldn't delete folder"),
              );
            }}
          >
            delete folder
          </Button>
        ) : null}
      </div>
      {folder.documents.length > 0 ? (
        canManage && folder.documents.length > 1 ? (
          <SortableList
            ariaLabel={`documents in ${folder.name}`}
            items={folder.documents}
            onReorder={(ids) => {
              void reorderDocs.mutateAsync(ids).catch(() => {
                toast.error("couldn't reorder documents");
              });
            }}
            renderItem={(d) => (
              <DocRow
                key={d.id}
                doc={d}
                canManage
                onDelete={() => {
                  const ok = window.confirm(`delete "${d.title}"?`);
                  if (!ok) return;
                  void deleteDoc.mutateAsync(d.id).then(
                    () => toast.success('document deleted'),
                    () => toast.error("couldn't delete"),
                  );
                }}
              />
            )}
          />
        ) : (
          <ul className="mt-2 flex flex-col gap-1">
            {folder.documents.map((d) => (
              <li key={d.id}>
                {canManage ? (
                  <DocRow
                    doc={d}
                    canManage
                    onDelete={() => {
                      const ok = window.confirm(`delete "${d.title}"?`);
                      if (!ok) return;
                      void deleteDoc.mutateAsync(d.id).then(
                        () => toast.success('document deleted'),
                        () => toast.error("couldn't delete"),
                      );
                    }}
                  />
                ) : (
                  <DocRow doc={d} canManage={false} />
                )}
              </li>
            ))}
          </ul>
        )
      ) : null}
      {folder.children.length > 0 ? (
        <div className="border-border ms-3 mt-2 border-s ps-3">
          {folder.children.map((c) => (
            <FolderView
              key={c.id}
              folder={c}
              depth={depth + 1}
              canManage={canManage}
              deleteFolder={deleteFolder}
              deleteDoc={deleteDoc}
              reorderDocs={reorderDocs}
            />
          ))}
        </div>
      ) : null}
    </section>
  );
}

function DocRow({
  doc,
  canManage,
  onDelete,
}: {
  doc: { id: string; title: string };
  canManage: boolean;
  onDelete?: () => void;
}) {
  return (
    <div className="hover:bg-surface-dim flex flex-wrap items-center gap-2 rounded px-2 py-1">
      <Link to={`/docs/${doc.id}`} className="text-foreground text-sm">
        {doc.title.toLowerCase()}
      </Link>
      {canManage && onDelete ? (
        <Button type="button" variant="ghost" className="h-7 px-2 text-xs" onClick={onDelete}>
          delete
        </Button>
      ) : null}
    </div>
  );
}
